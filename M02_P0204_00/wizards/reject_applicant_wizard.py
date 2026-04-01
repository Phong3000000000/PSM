# -*- coding: utf-8 -*-
from odoo import models, fields, api

class RejectApplicantWizard(models.TransientModel):
    _name = 'reject.applicant.wizard'
    _description = 'Wizard Từ chối Ứng viên'

    applicant_id = fields.Many2one('hr.applicant', string='Ứng viên', required=True)
    reason = fields.Text(string='Lý do từ chối', required=True)
    source_action = fields.Selection([
        ('reject_stage', 'Reject Stage'),
        ('reject_survey', 'Reject Survey'),
        ('reject_documents', 'Reject Documents'),
    ], string='Hành động gốc')

    def action_confirm_reject(self):
        self.ensure_one()
        if self.source_action == 'reject_survey':
            self.applicant_id._action_reject_survey_review_confirmed(self.reason)
        elif self.source_action == 'reject_documents':
            self.applicant_id._action_reject_documents_confirmed(self.reason)
        else:
            self.applicant_id._action_reject_stage_confirmed(self.reason)
        return {'type': 'ir.actions.act_window_close'}
