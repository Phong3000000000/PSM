# -*- coding: utf-8 -*-
"""
Referral Submission Model
Nhân viên submit ứng viên + tracking trạng thái
"""

from odoo import models, fields, api, _
from odoo.exceptions import UserError
import random
import string
import logging

_logger = logging.getLogger(__name__)


class ReferralSubmission(models.Model):
    _name = 'employee.referral.submission'
    _description = 'Giới thiệu ứng viên'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

    # Program link
    program_id = fields.Many2one(
        'employee.referral.program',
        string='Chương trình',
        required=True,
        ondelete='cascade'
    )
    
    # Selected by user, must be in program_id.line_ids
    job_id = fields.Many2one('hr.job', string='Vị trí', required=True)
    store_id = fields.Many2one('hr.department', related='program_id.store_id', store=True, string='Cửa hàng / Phòng ban')
    recruitment_session_id = fields.Many2one(
        'mcd.recruitment.session',
        related='program_id.recruitment_session_id',
        store=True,
        string='Đợt tuyển dụng'
    )
    
    # Referrer (employee who makes the referral)
    referrer_id = fields.Many2one(
        'hr.employee',
        string='Người giới thiệu',
        required=True,
        tracking=True
    )
    
    referrer_user_id = fields.Many2one(
        related='referrer_id.user_id',
        string='User giới thiệu'
    )
    
    # Auto-generated referral code
    referral_code = fields.Char(
        string='Mã giới thiệu',
        readonly=True,
        copy=False,
        tracking=True
    )
    
    # Candidate info (before registration)
    candidate_name = fields.Char(string='Tên ứng viên', required=True, tracking=True)
    candidate_email = fields.Char(string='Email ứng viên', required=True)
    candidate_phone = fields.Char(string='Số điện thoại')
    
    cv_attachment = fields.Binary(string='CV/Hồ sơ')
    cv_filename = fields.Char(string='Tên file CV')
    
    notes = fields.Text(string='Ghi chú')
    
    # After candidate registers → link to hr.applicant
    applicant_id = fields.Many2one(
        'hr.applicant',
        string='Ứng viên',
        readonly=True,
        tracking=True
    )
    
    # State tracking
    state = fields.Selection([
        ('submitted', 'Đã gửi'),
        ('email_sent', 'Đã gửi email'),
        ('registered', 'Ứng viên đã đăng ký'),
        ('interviewing', 'Đang phỏng vấn'),
        ('probation', 'Đang thử việc'),
        ('completed', 'Hoàn thành thử việc'),
        ('done', 'Hoàn tất'),
        ('failed', 'Không đạt'),
    ], string='Trạng thái', default='submitted', tracking=True, copy=False)
    
    # Probation tracking
    probation_start_date = fields.Date(string='Ngày bắt đầu thử việc')
    probation_end_date = fields.Date(string='Ngày kết thúc thử việc')
    
    # Bonus tracking
    bonus_amount = fields.Float(
        string='Tiền thưởng',
        compute='_compute_bonus_amount',
        store=True
    )
    
    bonus_eligible = fields.Boolean(
        string='Đủ điều kiện thưởng',
        compute='_compute_bonus_eligible',
        store=True
    )
    
    bonus_paid = fields.Boolean(string='Đã chi thưởng', default=False, tracking=True)
    bonus_paid_date = fields.Date(string='Ngày chi thưởng')
    
    # Link to payslip input
    payslip_input_id = fields.Many2one(
        'hr.payslip.input',
        string='Payslip Input',
        readonly=True
    )
    
    @api.depends('program_id.line_ids.bonus_amount', 'job_id')
    def _compute_bonus_amount(self):
        for rec in self:
            if rec.program_id and rec.job_id:
                line = rec.program_id.line_ids.filtered(lambda l: l.job_id.id == rec.job_id.id)
                rec.bonus_amount = line[0].bonus_amount if line else 0
            else:
                rec.bonus_amount = 0

    @api.depends('state')
    def _compute_bonus_eligible(self):
        for rec in self:
            rec.bonus_eligible = rec.state in ['completed', 'done']
    
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('referral_code'):
                vals['referral_code'] = self._generate_referral_code()
        return super().create(vals_list)
    
    def write(self, vals):
        old_states = {rec.id: rec.state for rec in self}
        res = super().write(vals)
        if 'state' in vals:
            new_state = vals['state']
            for rec in self:
                old_state = old_states.get(rec.id)
                # Slot -1 when candidate enters probation from interviewing (passed OJE)
                if new_state == 'probation' and old_state == 'interviewing':
                    rec._decrease_slot()
                # Slot +1 if candidate fails after having consumed a slot
                elif new_state == 'failed' and old_state in ['probation', 'completed']:
                    rec._restore_slot()
                # Auto-close check
                if new_state in ['probation', 'completed']:
                    rec.program_id._check_auto_close()
        return res

    def _decrease_slot(self):
        """Decrease slot (-1) when candidate enters probation (passed interview + OJE)"""
        self.ensure_one()
        line = self.program_id.line_ids.filtered(
            lambda l: l.job_id.id == self.job_id.id
        )[:1] if self.job_id and self.program_id else None
        if line and line.positions_needed > 0:
            line.sudo().write({'positions_needed': line.positions_needed - 1})
            self.message_post(
                body='-1 slot tuyển dụng vị trí <b>%s</b> (ứng viên chuyển sang thử việc)' % (self.job_id.name or ''),
                message_type='notification'
            )

    def _restore_slot(self):
        """Restore slot (+1) when candidate fails probation"""
        self.ensure_one()
        line = self.program_id.line_ids.filtered(
            lambda l: l.job_id.id == self.job_id.id
        )[:1] if self.job_id and self.program_id else None
        if line:
            line.sudo().write({'positions_needed': line.positions_needed + 1})
            self.message_post(
                body='+1 slot tuyển dụng vị trí <b>%s</b> (ứng viên rớt thử việc)' % (self.job_id.name or ''),
                message_type='notification'
            )

    def _generate_referral_code(self):
        """Generate unique referral code: REF-XXXXXX"""
        while True:
            code = 'REF-' + ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
            if not self.search([('referral_code', '=', code)], limit=1):
                return code
    
    # ==================== ACTIONS ====================
    
    def action_send_candidate_email(self):
        """Send email to candidate with registration link"""
        self.ensure_one()
        
        if not self.candidate_email:
            raise UserError(_('Ứng viên chưa có email!'))
        
        template = self.env.ref('M02_P0202_03.email_referral_candidate_invite_v2', raise_if_not_found=False)
        if template:
            template.send_mail(self.id, force_send=False)
            self.message_post(
                body=_('📧 Đã gửi email mời đăng ký đến %s') % self.candidate_email,
                message_type='notification'
            )
            _logger.info(f"Sent referral invitation to {self.candidate_email}, code: {self.referral_code}")
        else:
            # Template not found - log warning but continue
            _logger.warning(f"Email template 'email_referral_candidate_invite_v2' not found. Skipping email.")
            self.message_post(
                body=_('Email template không tìm thấy - bỏ qua gửi email. Link đăng ký: /referral/register/%s') % self.referral_code,
                message_type='notification'
            )
        
        # Update state regardless
        self.write({'state': 'email_sent'})
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Đã xử lý!'),
                'message': _('Link đăng ký cho %s: /referral/register/%s') % (self.candidate_email, self.referral_code),
                'type': 'success',
            }
        }
    
    def action_mark_registered(self):
        """Mark candidate as registered (manual or via controller)"""
        self.write({'state': 'registered'})
    
    def action_start_interview(self):
        """Candidate starts interview process"""
        self.write({'state': 'interviewing'})
        self.message_post(body=_('Ứng viên bắt đầu quy trình phỏng vấn'))

    def action_start_probation(self):
        """Start probation period"""
        config = self.env['employee.referral.config'].sudo().get_config()
        probation_days = config.probation_days if config else 60
        
        start_date = fields.Date.today()
        end_date = fields.Date.add(start_date, days=probation_days)
        
        self.write({
            'state': 'probation',
            'probation_start_date': start_date,
            'probation_end_date': end_date,
        })
        
        self.message_post(
            body=_('Bắt đầu thử việc từ %s đến %s (%d ngày)') % (start_date, end_date, probation_days)
        )
    
    def action_pass_probation(self):
        """Candidate passed probation → eligible for bonus"""
        self.write({'state': 'completed'})
        
        # Create payslip input for referrer
        self._create_bonus_payslip_input()
        
        # Send notification to referrer
        self._send_bonus_eligible_notification()
        
        self.message_post(
            body=_('Ứng viên đã hoàn thành thử việc! Người giới thiệu %s đủ điều kiện nhận thưởng %s VND') 
                 % (self.referrer_id.name, '{:,.0f}'.format(self.bonus_amount))
        )
    
    def action_fail_probation(self):
        """Candidate failed probation"""
        self.write({'state': 'failed'})
        self.message_post(body=_('Ứng viên không đạt thử việc'))
        
        # Trigger offboarding if applicant exists
        if self.applicant_id and self.applicant_id.employee_id:
            pass
    
    def action_open_applicant(self):
        """Open linked hr.applicant record"""
        self.ensure_one()
        if not self.applicant_id:
            return False
        return {
            'type': 'ir.actions.act_window',
            'name': 'Ứng viên',
            'res_model': 'hr.applicant',
            'res_id': self.applicant_id.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_mark_bonus_paid(self):
        """HR marks bonus as paid"""
        self.write({
            'bonus_paid': True,
            'bonus_paid_date': fields.Date.today(),
            'state': 'done'
        })
        self.message_post(
            body=_('Thưởng giới thiệu đã được chi cho %s') % self.referrer_id.name
        )
    
    # ==================== PAYROLL INTEGRATION ====================
    
    def _create_bonus_payslip_input(self):
        """Create payslip input for referral bonus"""
        self.ensure_one()
        
        config = self.env['employee.referral.config'].sudo().get_config()
        if not config or not config.auto_create_payslip_input:
            return
        
        if not self.referrer_id:
            return
        
        # Find active payslip for referrer
        payslip = self.env['hr.payslip'].search([
            ('employee_id', '=', self.referrer_id.id),
            ('state', 'in', ['draft', 'verify']),
        ], limit=1, order='date_from desc')
        
        if payslip:
            # Find or create input type for referral bonus
            input_type = config.payslip_input_type_id
            if not input_type:
                input_type = self.env['hr.payslip.input.type'].search([
                    ('code', '=', 'REFERRAL_BONUS')
                ], limit=1)
                
                if not input_type:
                    input_type = self.env['hr.payslip.input.type'].create({
                        'name': 'Thưởng giới thiệu nhân sự',
                        'code': 'REFERRAL_BONUS',
                    })
            
            # Create input
            input_rec = self.env['hr.payslip.input.type'].create({
                'payslip_id': payslip.id,
                'input_type_id': input_type.id,
                'amount': self.bonus_amount,
            })
            
            self.payslip_input_id = input_rec
            
            _logger.info(f"Created payslip input for referral bonus: {self.referrer_id.name}, amount: {self.bonus_amount}")
        else:
            _logger.warning(f"No active payslip found for {self.referrer_id.name} to add referral bonus")
    
    # ==================== EMAIL ====================
    
    def _send_bonus_eligible_notification(self):
        """Send notification to referrer about bonus eligibility"""
        template = self.env.ref('M02_P0202_03.email_referral_bonus_eligible_v2', raise_if_not_found=False)
        if template:
            template.send_mail(self.id, force_send=False)
    def action_open_applicant(self):
        """Open linked applicant record"""
        self.ensure_one()
        if self.applicant_id:
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'hr.applicant',
                'res_id': self.applicant_id.id,
                'view_mode': 'form',
                'target': 'current',
            }
        return False
