# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class ApprovalLog(models.Model):
    _name = "approval.log"
    _description = "Approval Log (Audit Trail)"
    _order = "id desc"
    _rec_name = "action"

    company_id = fields.Many2one("res.company", required=True, index=True)
    request_id = fields.Many2one("approval.engine.request", ondelete="cascade", index=True)

    res_model = fields.Char(required=True, index=True)
    res_id = fields.Integer(required=True, index=True)

    user_id = fields.Many2one("res.users", required=True, default=lambda self: self.env.user, index=True)
    action = fields.Selection(
        [
            ("submit", "Submitted"),
            ("approve", "Approved"),
            ("reject", "Rejected"),
            ("advance", "Advanced Step"),
            ("final_approve", "Final Approved"),
            ("cancel", "Cancelled"),
        ],
        required=True,
        index=True,
    )
    step_id = fields.Many2one("approval.step", index=True)
    timestamp = fields.Datetime(default=fields.Datetime.now, required=True, index=True)
    comment = fields.Text()

    @api.model
    def log(self, *, company, request, record, action, comment="", step=None):
        vals = {
            "company_id": company.id,
            "request_id": request.id if request else False,
            "res_model": record._name,
            "res_id": record.id,
            "user_id": self.env.user.id,
            "action": action,
            "comment": comment or "",
            "step_id": step.id if step else False,
        }
        return self.create(vals)