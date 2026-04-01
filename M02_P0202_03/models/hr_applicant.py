"""
Extend HR Applicant for Referral Integration
"""

from odoo import models, fields, api

class HrApplicant(models.Model):
    _inherit = 'hr.applicant'

    # Link to referral submission
    referral_submission_id = fields.Many2one(
        'employee.referral.submission',
        string='Từ giới thiệu',
        tracking=True,
        help='Link đến record giới thiệu nhân sự'
    )
    
    is_referral = fields.Boolean(
        string='Từ chương trình giới thiệu',
        compute='_compute_is_referral',
        store=True
    )
    
    referrer_name = fields.Char(
        string='Người giới thiệu',
        compute='_compute_referrer_info',
        store=True
    )
    
    referral_code = fields.Char(
        string='Mã giới thiệu',
        related='referral_submission_id.referral_code'
    )
    
    @api.depends('referral_submission_id')
    def _compute_is_referral(self):
        for rec in self:
            rec.is_referral = bool(rec.referral_submission_id)
    
    @api.depends('referral_submission_id', 'referral_submission_id.referrer_id')
    def _compute_referrer_info(self):
        for rec in self:
            if rec.referral_submission_id and rec.referral_submission_id.referrer_id:
                rec.referrer_name = rec.referral_submission_id.referrer_id.name
            else:
                rec.referrer_name = False
    
    def write(self, vals):
        """Override to sync state changes with referral submission"""
        result = super().write(vals)
        
        # Sync stage changes to referral submission
        if 'stage_id' in vals:
            for rec in self:
                if rec.referral_submission_id:
                    self._sync_referral_state(rec)
        
        return result
    
    def _sync_referral_state(self, applicant):
        """Sync applicant stage to referral submission state
        
        P0204 Store Stages → P0202 Submission States:
        - New → (no change)
        - Review Tiêu chí → interviewing
        - Interview → interviewing
        - OJE → interviewing (still in interview process)
        - Thử việc → probation
        - Đề xuất chính thức → probation
        - Chính thức → completed (Pass - eligible for bonus)
        - Refused/Từ chối → failed (Fail)
        """
        if not applicant.referral_submission_id:
            return
        
        submission = applicant.referral_submission_id
        stage_name = applicant.stage_id.name.lower() if applicant.stage_id else ''
        
        # Check if applicant is refused (Fail case)
        if 'refused' in stage_name or 'từ chối' in stage_name or 'reject' in stage_name or 'rớt' in stage_name:
            if submission.state not in ['completed', 'done', 'failed']:
                submission.write({'state': 'failed'})
                submission.message_post(
                    body='Ứng viên KHÔNG ĐẠT phỏng vấn/thử việc',
                    message_type='notification'
                )
            return
        
        # Map stage to submission state
        if 'interview' in stage_name or 'phỏng vấn' in stage_name or 'oje' in stage_name or 'review' in stage_name:
            if submission.state in ['registered', 'email_sent', 'submitted']:
                submission.write({'state': 'interviewing'})
        
        elif 'thử việc' in stage_name or 'probation' in stage_name or 'đề xuất' in stage_name:
            if submission.state == 'interviewing':
                submission.action_start_probation()
        
        elif 'chính thức' in stage_name or 'hired' in stage_name or 'contract' in stage_name:
            # This is PASS - candidate completed probation
            if submission.state in ['probation']:
                submission.action_pass_probation()
                submission.message_post(
                    body='Ứng viên ĐẠT - Đã hoàn thành thử việc và trở thành nhân viên chính thức!',
                    message_type='notification'
                )
    
    def action_create_employee(self):
        """Override to trigger probation start on referral if still at interviewing"""
        result = super().action_create_employee()

        if self.referral_submission_id and self.referral_submission_id.state == 'interviewing':
            self.referral_submission_id.action_start_probation()

        return result

    def action_open_referral_submission(self):
        """Open related referral submission"""
        self.ensure_one()
        if self.referral_submission_id:
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'employee.referral.submission',
                'res_id': self.referral_submission_id.id,
                'view_mode': 'form',
                'target': 'current',
            }
        return False

    def action_open_onboarding(self):
        """Open Onboarding (Employee Profile)"""
        self.ensure_one()
        if self.employee_id:
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'hr.employee',
                'res_id': self.employee_id.id,
                'view_mode': 'form',
                'target': 'current',
            }
        return False

    def action_open_offboarding(self):
        """Open Offboarding (Resignation Request)"""
        self.ensure_one()
        
        # Find resignation request for this employee
        employee = self.employee_id
        if not employee:
            return False
            
        resignation = self.env['approval.request'].search([
            ('employee_id', '=', employee.id),
            ('category_id.name', '=', 'Yêu cầu nghỉ việc ') # Note the space if strictly matching P0213 code
        ], limit=1)
        
        # Fallback search by category ref if name is unreliable
        if not resignation:
             resignation_cat = self.env.ref('M02_P0213_00.approval_category_resignation', raise_if_not_found=False)
             if resignation_cat:
                 resignation = self.env['approval.request'].search([
                    ('employee_id', '=', employee.id),
                    ('category_id', '=', resignation_cat.id)
                ], limit=1)
        
        if resignation:
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'approval.request',
                'res_id': resignation.id,
                'view_mode': 'form',
                'target': 'current',
            }
        return False

    @api.model
    def retrieve_referral_welcome_screen(self):
        """Override: replace native referral counts with employee.referral.submission counts."""
        result = super().retrieve_referral_welcome_screen()
        if 'referral' not in result:
            return result

        user = self.env.user
        employee = self.env['hr.employee'].sudo().search([
            '|',
            ('user_id', '=', user.id),
            ('work_contact_id', '=', user.partner_id.id),
        ], limit=1)

        if not employee:
            result['referral'] = {'all': 0, 'progress': 0, 'hired': 0}
            return result

        subs = self.env['employee.referral.submission'].sudo().search([
            ('referrer_id', '=', employee.id),
        ])
        result['referral'] = {
            'all': len(subs),
            'progress': len(subs.filtered(lambda s: s.state == 'probation')),
            'hired': len(subs.filtered(lambda s: s.state in ['completed', 'done'])),
        }
        return result
