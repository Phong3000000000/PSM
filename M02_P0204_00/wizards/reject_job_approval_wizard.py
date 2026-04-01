# -*- coding: utf-8 -*-
from odoo import models, fields, api

class RejectJobApprovalWizard(models.TransientModel):
    _name = 'reject.job.approval.wizard'
    _description = 'Wizard Từ chối Yêu cầu Tuyển dụng'

    request_id = fields.Many2one('job.approval.request', string='Yêu cầu', required=True)
    reason = fields.Text(string='Lý do từ chối', required=True)

    def action_confirm_reject(self):
        self.ensure_one()
        self.request_id.action_reject_with_reason(self.reason)
        return {'type': 'ir.actions.act_window_close'}
