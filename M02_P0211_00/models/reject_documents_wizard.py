# -*- coding: utf-8 -*-
from odoo import models, fields
from odoo.exceptions import ValidationError


class RejectDocumentsWizard(models.TransientModel):
    _name = 'reject.documents.wizard'
    _description = 'Wizard Từ chối Hồ sơ Ứng viên'

    applicant_id = fields.Many2one('hr.applicant', string='Ứng viên', required=True)
    reason = fields.Text(string='Lý do từ chối', required=True)

    def action_confirm_reject(self):
        self.ensure_one()
        if not self.reason or not self.reason.strip():
            raise ValidationError("Vui lòng nhập lý do từ chối!")

        applicant = self.applicant_id
        clean_reason = self.reason.strip()

        stage = self.env['hr.recruitment.stage'].search([('name', 'ilike', 'Reject')], limit=1)
        # Try to find a pipeline-specific reject stage first
        stage_type = applicant.position_level or applicant.recruitment_type
        if stage_type:
            pipeline_stage = self.env['hr.recruitment.stage'].search([
                ('name', 'ilike', 'Reject'),
                ('recruitment_type', 'in', [stage_type, 'both'])
            ], limit=1)
            if pipeline_stage:
                stage = pipeline_stage

        vals = {
            'document_approval_status': 'refused',
            'reject_reason': clean_reason,
        }
        if stage:
            vals['stage_id'] = stage.id

        applicant.write(vals)
        applicant.message_post(body=f"❌ Từ chối hồ sơ. Lý do: {clean_reason}")
        return {'type': 'ir.actions.act_window_close'}
