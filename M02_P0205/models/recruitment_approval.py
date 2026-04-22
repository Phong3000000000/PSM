# -*- coding: utf-8 -*-
from odoo import models, fields, api, _


class ApprovalRequest(models.Model):
    _inherit = "approval.request"

    x_psm_0205_recruitment_request_id = fields.Many2one(
        "x_psm_recruitment_request",
        string="Yêu cầu tuyển dụng",
        copy=False,
        index=True,
        ondelete="set null",
    )

    def action_open_psm_recruitment_request(self):
        self.ensure_one()
        if not self.x_psm_0205_recruitment_request_id:
            return False
        action = {
            "type": "ir.actions.act_window",
            "name": _("Yêu Cầu Tuyển Dụng"),
            "res_model": "x_psm_recruitment_request",
            "view_mode": "form",
            "res_id": self.x_psm_0205_recruitment_request_id.id,
            "target": "current",
        }

        is_rgm_readonly = (
            self.env.user.has_group('M02_P0200.GDH_OPS_STORE_RGM_M')
            and not self.env.user.has_group('M02_P0200.GDH_RST_HR_RECRUITMENT_M')
            and not self.env.user.has_group('M02_P0200.GDH_RST_HR_RECRUITMENT_S')
        )
        if is_rgm_readonly:
            action["context"] = {
                "create": False,
                "edit": False,
                "delete": False,
                "x_psm_0205_rgm_readonly": True,
            }

        return action

    @api.depends("approver_ids.status", "approver_ids.required")
    def _compute_request_status(self):
        super()._compute_request_status()
        linked_requests = self.mapped("x_psm_0205_recruitment_request_id")
        if not linked_requests:
            return

        store_requests = linked_requests.filtered(lambda rec: rec.recruitment_block == 'store')
        office_requests = linked_requests - store_requests

        if store_requests:
            store_requests.sudo()._sync_state_from_approval_requests()
        if office_requests:
            office_requests._sync_state_from_approval_requests()
