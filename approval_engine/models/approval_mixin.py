# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class ApprovalMixin(models.AbstractModel):
    _name = "approval.mixin"
    _description = "Approval Mixin"

    # IMPORTANT (Odoo 19 EE):
    # Do NOT inherit mail.thread / mail.activity.mixin here.
    # Many business documents already include a long list of mixins.
    # If this mixin also inherits mail.thread, Odoo's dynamic model class
    # composition can hit an MRO conflict (TypeError: cannot create a consistent
    # method resolution order).
    #
    # Therefore, keep this as a *pure* mixin. Target models that want chatter
    # features should inherit mail.thread / mail.activity.mixin themselves
    # (most standard documents already do).

    # --------------------------
    # CHATTER SAFE POST
    # --------------------------
    def _approval_message_post(self, body: str):
        """Post a message to chatter if the target model supports it.

        This keeps the mixin reusable for models that don't inherit
        mail.thread.
        """
        for rec in self:
            if hasattr(rec, "message_post"):
                rec.message_post(body=body)

    approval_state = fields.Selection(
        [("draft", "Draft"), ("waiting", "Waiting"), ("approved", "Approved"), ("rejected", "Rejected")],
        default="draft",
        tracking=True,
        index=True,
        copy=False,
    )

    current_step_id = fields.Many2one("approval.step", copy=False, tracking=True)
    next_approver_ids = fields.Many2many("res.users", compute="_compute_next_approver_ids", store=False)

    approval_request_id = fields.Many2one("approval.engine.request", copy=False, readonly=True)

    approval_log_ids = fields.One2many(
        "approval.log",
        compute="_compute_approval_log_ids",
        string="Approval Logs",
        store=False,
    )

    approval_can_approve = fields.Boolean(compute="_compute_approval_can_approve", store=False)
    approval_can_submit = fields.Boolean(compute="_compute_approval_can_submit", store=False)

    # --------------------------
    # COMPUTES
    # --------------------------
    def _compute_approval_log_ids(self):
        Log = self.env["approval.log"]
        for rec in self:
            rec.approval_log_ids = Log.search([("res_model", "=", rec._name), ("res_id", "=", rec.id)])

    def _compute_next_approver_ids(self):
        for rec in self:
            users = self.env["res.users"]
            req = rec.approval_request_id
            if req and req.exists() and req.state == "waiting":
                users = req.next_approver_ids
            rec.next_approver_ids = users

    def _compute_approval_can_approve(self):
        for rec in self:
            rec.approval_can_approve = bool(rec.approval_request_id and (self.env.user in rec.next_approver_ids))

    def _compute_approval_can_submit(self):
        for rec in self:
            wf = rec._get_applicable_workflow(action_name=rec.env.context.get("approval_pending_action") or "")
            rec.approval_can_submit = bool(wf and rec.approval_state in ("draft", "rejected") and rec.id)

    # --------------------------
    # PUBLIC METHODS (Required)
    # --------------------------
    def action_submit_for_approval(self):
        for rec in self:
            if rec.approval_state == "waiting":
                raise UserError(_("Already waiting for approval."))

            pending_action = rec.env.context.get("approval_pending_action") or ""
            wf = rec._get_applicable_workflow(action_name=pending_action)
            if not wf:
                raise UserError(_("No applicable approval workflow found."))

            company = rec.company_id if hasattr(rec, "company_id") and rec.company_id else rec.env.company

            req = rec.env["approval.engine.request"].create({
                "company_id": company.id,
                "workflow_id": wf.id,
                "res_model": rec._name,
                "res_id": rec.id,
                "requester_id": rec.env.user.id,
                "state": "draft",
                "pending_action": pending_action,
            })

            req._open_first_step()

            rec.write({
                "approval_state": "waiting" if req.state == "waiting" else "approved",
                "approval_request_id": req.id,
                "current_step_id": req.current_step_id.id if req.current_step_id else False,
            })

            rec.env["approval.log"].log(
                company=req.company_id,
                request=req,
                record=rec,
                action="submit",
                comment=_("Submitted for approval."),
                step=req.current_step_id,
            )
            rec._approval_message_post(_("Submitted for approval. Workflow: <b>%s</b>") % wf.name)

            rec._approval_send_email_notifications(req, event="submit")

        return True

    def action_approve(self):
        for rec in self:
            req = rec._get_active_request()
            if not req:
                raise UserError(_("No active approval request."))

            req.action_approve(comment="")
            rec._sync_from_request(req)

            rec.env["approval.log"].log(
                company=req.company_id,
                request=req,
                record=rec,
                action="approve" if req.state != "approved" else "final_approve",
                comment=_("Approved."),
                step=req.current_step_id,
            )

            rec._approval_send_email_notifications(req, event="approve")

        return True

    def action_reject(self, reason=None):
        reason = (reason or "").strip()
        if not reason:
            raise UserError(_("Rejection reason is required."))

        for rec in self:
            req = rec._get_active_request()
            if not req:
                raise UserError(_("No active approval request."))

            req.action_reject(reason)
            rec._sync_from_request(req)

            rec.env["approval.log"].log(
                company=req.company_id,
                request=req,
                record=rec,
                action="reject",
                comment=reason,
                step=req.current_step_id,
            )

            rec._approval_send_email_notifications(req, event="reject")

        return True

    def _compute_next_approvers(self):
        # Compatibility method requested by spec.
        for rec in self:
            rec._compute_next_approver_ids()

    # --------------------------
    # WORKFLOW RESOLUTION
    # --------------------------
    def _get_applicable_workflow(self, action_name: str = ""):
        self.ensure_one()
        company = self.company_id if hasattr(self, "company_id") and self.company_id else self.env.company

        workflows = self.env["approval.workflow"].search([
            ("active", "=", True),
            ("company_id", "=", company.id),
            ("model", "=", self._name),
        ], order="sequence asc, id asc")

        for wf in workflows:
            if wf.is_applicable(self, action_name=action_name):
                return wf
        return False

    # --------------------------
    # ACTION BLOCKING (Integration helper)
    # --------------------------
    def _approval_check_before_action(self, action_name: str):
        for rec in self:
            if rec.env.context.get("approval_engine_bypass"):
                continue

            wf = rec._get_applicable_workflow(action_name=action_name)
            if not wf:
                continue  # no approval required

            if rec.approval_state == "approved":
                continue

            if rec.approval_state == "waiting":
                raise UserError(_("This document is waiting for approval. Approvers: %s") %
                                (", ".join(rec.next_approver_ids.mapped("name")) or _("(none)")))

            raise UserError(_("Approval is required before this action. Click 'Submit for Approval'."))

        return True

    # --------------------------
    # POST-FINAL HOOK
    # --------------------------
    def _apply_native_transition_after_final_approval(self, request):
        # Hook for model-specific implementation.
        return True

    # --------------------------
    # INTERNAL HELPERS
    # --------------------------
    def _get_active_request(self):
        self.ensure_one()
        req = self.approval_request_id
        if req and req.exists() and req.state in ("waiting", "approved", "rejected"):
            return req

        Req = self.env["approval.engine.request"]
        company = self.company_id if hasattr(self, "company_id") and self.company_id else self.env.company
        return Req.search([
            ("company_id", "=", company.id),
            ("res_model", "=", self._name),
            ("res_id", "=", self.id),
        ], order="id desc", limit=1)

    def _sync_from_request(self, req):
        self.ensure_one()
        if not req or not req.exists():
            return

        vals = {"approval_request_id": req.id}
        if req.state == "waiting":
            vals.update({"approval_state": "waiting", "current_step_id": req.current_step_id.id if req.current_step_id else False})
        elif req.state == "approved":
            vals.update({"approval_state": "approved", "current_step_id": False})
            self._apply_native_transition_after_final_approval(req)
        elif req.state == "rejected":
            vals.update({"approval_state": "rejected", "current_step_id": req.current_step_id.id if req.current_step_id else False})
        self.write(vals)

    def _on_approval_request_finalized(self, request):
        self.ensure_one()
        self._sync_from_request(request)
        self._approval_message_post(_("Final approval completed."))

    def _on_approval_request_rejected(self, request, reason):
        self.ensure_one()
        self._sync_from_request(request)
        self._approval_message_post(_("Approval rejected: %s") % reason)

    def _approval_send_email_notifications(self, request, event: str):
        # Placeholder hook: implement in derived module if needed.
        return True

