# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError, AccessError


class ApprovalRequest(models.Model):
    _name = "approval.engine.request"
    _description = "Approval Request"
    _order = "id desc"
    _inherit = ["mail.thread", "mail.activity.mixin"]

    name = fields.Char(default=lambda self: _("New"), readonly=True, copy=False)
    company_id = fields.Many2one("res.company", required=True, index=True)

    workflow_id = fields.Many2one("approval.workflow", required=True, ondelete="restrict")

    res_model = fields.Char(required=True, index=True)
    res_id = fields.Integer(required=True, index=True)

    requester_id = fields.Many2one("res.users", required=True, default=lambda self: self.env.user, index=True)

    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("waiting", "Waiting"),
            ("approved", "Approved"),
            ("rejected", "Rejected"),
            ("cancelled", "Cancelled"),
        ],
        default="draft",
        tracking=True,
        index=True,
    )

    current_step_id = fields.Many2one("approval.step", tracking=True)
    pending_action = fields.Char(help="Technical action name being blocked, e.g. button_confirm / action_post.")

    step_run_ids = fields.One2many("approval.engine.request.step.run", "request_id", string="Step Runs", copy=False)
    next_approver_ids = fields.Many2many("res.users", compute="_compute_next_approvers", string="Next Approvers", store=False)

    reject_reason = fields.Text()

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", _("New")) == _("New"):
                vals["name"] = self.env["ir.sequence"].next_by_code("approval.engine.request") or _("New")
        return super().create(vals_list)

    def _get_target_record(self):
        self.ensure_one()
        return self.env[self.res_model].browse(self.res_id).exists()

    @api.depends("step_run_ids.state", "step_run_ids.approver_run_ids.state", "current_step_id", "state")
    def _compute_next_approvers(self):
        for req in self:
            users = self.env["res.users"]
            if req.state == "waiting" and req.current_step_id:
                current_run = req.step_run_ids.filtered(lambda r: r.step_id == req.current_step_id and r.state == "waiting")[:1]
                if current_run:
                    pending = current_run.approver_run_ids.filtered(lambda a: a.state == "pending")
                    users = pending.mapped("user_id")
            req.next_approver_ids = users

    def _ensure_can_approve(self):
        self.ensure_one()
        if self.env.user in self.next_approver_ids:
            return True
        raise AccessError(_("You are not an approver for the current step."))

    def _open_first_step(self):
        self.ensure_one()
        record = self._get_target_record()
        if not record:
            raise UserError(_("Target record not found."))

        steps = self.workflow_id.step_ids.sorted("sequence")
        applicable_steps = [s for s in steps if s.is_applicable(record)]
        if not applicable_steps:
            # No steps => auto-approved
            self.write({"state": "approved", "current_step_id": False})
            return

        first = applicable_steps[0]
        self._create_step_run(first, record)
        self.write({"state": "waiting", "current_step_id": first.id})

    def _create_step_run(self, step, record):
        self.ensure_one()
        approvers = step.get_approver_users(record).filtered(lambda u: not u.share)
        if not approvers:
            raise UserError(_("No approvers resolved for step '%s'.") % (step.name,))

        run = self.env["approval.engine.request.step.run"].create({
            "request_id": self.id,
            "step_id": step.id,
            "sequence": step.sequence,
            "state": "waiting",
            "parallel": step.parallel,
        })

        self.env["approval.engine.request.approver.run"].create([
            {"step_run_id": run.id, "user_id": u.id, "state": "pending"}
            for u in approvers
        ])

        self.message_post(body=_("Approval step opened: <b>%s</b>. Approvers: %s") % (
            step.name,
            ", ".join(approvers.mapped("name")),
        ))

    def _advance_to_next_step_or_finish(self):
        self.ensure_one()
        record = self._get_target_record()
        if not record:
            raise UserError(_("Target record not found."))

        steps = self.workflow_id.step_ids.sorted("sequence")
        applicable_steps = [s for s in steps if s.is_applicable(record)]
        if not applicable_steps:
            self.write({"state": "approved", "current_step_id": False})
            return

        current = self.current_step_id
        next_step = None
        if current:
            for st in applicable_steps:
                if st.sequence > current.sequence:
                    next_step = st
                    break
        else:
            next_step = applicable_steps[0]

        if not next_step:
            self.write({"state": "approved", "current_step_id": False})
            return

        self._create_step_run(next_step, record)
        self.write({"current_step_id": next_step.id, "state": "waiting"})

    def action_approve(self, comment=None):
        for req in self:
            req._ensure_can_approve()
            if req.state != "waiting" or not req.current_step_id:
                raise UserError(_("No active approval step to approve."))

            current_run = req.step_run_ids.filtered(lambda r: r.step_id == req.current_step_id and r.state == "waiting")[:1]
            if not current_run:
                raise UserError(_("Current step run not found."))

            my_line = current_run.approver_run_ids.filtered(lambda a: a.user_id == req.env.user and a.state == "pending")[:1]
            if not my_line:
                raise UserError(_("You have no pending approval on this step."))

            my_line.write({
                "state": "approved",
                "decided_on": fields.Datetime.now(),
                "comment": comment or "",
                "acted_by_user_id": req.env.user.id,
            })

            if not current_run.parallel:
                current_run.approver_run_ids.filtered(lambda a: a.state == "pending").write({"state": "cancelled"})

            req.message_post(body=_("Approved by <b>%s</b>%s") % (
                req.env.user.name,
                (": %s" % comment) if comment else "",
            ))

            if current_run._is_completed():
                current_run.write({"state": "approved", "closed_on": fields.Datetime.now()})
                req._advance_to_next_step_or_finish()

            if req.state == "approved":
                record = req._get_target_record()
                if record and hasattr(record, "_on_approval_request_finalized"):
                    record._on_approval_request_finalized(req)

        return True

    def action_reject(self, reason=None):
        reason = (reason or "").strip()
        if not reason:
            raise UserError(_("Rejection reason is required."))

        for req in self:
            req._ensure_can_approve()
            if req.state != "waiting" or not req.current_step_id:
                raise UserError(_("No active approval step to reject."))

            current_run = req.step_run_ids.filtered(lambda r: r.step_id == req.current_step_id and r.state == "waiting")[:1]
            if not current_run:
                raise UserError(_("Current step run not found."))

            my_line = current_run.approver_run_ids.filtered(lambda a: a.user_id == req.env.user and a.state == "pending")[:1]
            if not my_line:
                raise UserError(_("You have no pending approval on this step."))

            my_line.write({
                "state": "rejected",
                "decided_on": fields.Datetime.now(),
                "comment": reason,
                "acted_by_user_id": req.env.user.id,
            })

            current_run.write({"state": "rejected", "closed_on": fields.Datetime.now()})
            req.write({"state": "rejected", "reject_reason": reason})

            req.message_post(body=_("Rejected by <b>%s</b>: %s") % (req.env.user.name, reason))

            record = req._get_target_record()
            if record and hasattr(record, "_on_approval_request_rejected"):
                record._on_approval_request_rejected(req, reason)

        return True


class ApprovalRequestStepRun(models.Model):
    _name = "approval.engine.request.step.run"
    _description = "Approval Step Run"
    _order = "request_id, sequence, id"

    request_id = fields.Many2one("approval.engine.request", required=True, ondelete="cascade", index=True)
    step_id = fields.Many2one("approval.step", required=True, ondelete="restrict", index=True)
    sequence = fields.Integer(default=10)
    state = fields.Selection(
        [("waiting", "Waiting"), ("approved", "Approved"), ("rejected", "Rejected"), ("cancelled", "Cancelled")],
        default="waiting",
        index=True,
    )
    parallel = fields.Boolean(default=False)

    opened_on = fields.Datetime(default=fields.Datetime.now)
    closed_on = fields.Datetime()

    approver_run_ids = fields.One2many("approval.engine.request.approver.run", "step_run_id", copy=False)

    def _is_completed(self) -> bool:
        self.ensure_one()
        if self.state != "waiting":
            return True

        pending = self.approver_run_ids.filtered(lambda a: a.state == "pending")
        if self.parallel:
            rejected = self.approver_run_ids.filtered(lambda a: a.state == "rejected")
            return (not pending) and (not rejected)

        if self.approver_run_ids.filtered(lambda a: a.state == "approved"):
            return True
        if self.approver_run_ids.filtered(lambda a: a.state == "rejected"):
            return True
        return False


class ApprovalRequestApproverRun(models.Model):
    _name = "approval.engine.request.approver.run"
    _description = "Approval Approver Run"
    _order = "id"

    step_run_id = fields.Many2one("approval.engine.request.step.run", required=True, ondelete="cascade", index=True)
    user_id = fields.Many2one("res.users", required=True, index=True)

    state = fields.Selection(
        [("pending", "Pending"), ("approved", "Approved"), ("rejected", "Rejected"), ("cancelled", "Cancelled")],
        default="pending",
        index=True,
    )
    decided_on = fields.Datetime()
    comment = fields.Text()

    acted_by_user_id = fields.Many2one("res.users", string="Acted By", help="Actual user who performed the action.")

    _sql_constraints = [
        ("uniq_step_user", "unique(step_run_id, user_id)", "Approver must be unique per step run."),
    ]
