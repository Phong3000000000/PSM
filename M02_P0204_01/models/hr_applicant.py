# -*- coding: utf-8 -*-
"""
Extend HR Applicant
Thêm các trường liên quan đến lịch phỏng vấn và khảo sát
"""

from odoo import models, fields, api, exceptions
from datetime import timedelta
import logging

_logger = logging.getLogger(__name__)

class HrApplicant(models.Model):
    _inherit = 'hr.applicant'
    
    # ====================BRAND & SCHEDULE ====================
    
    company_id = fields.Many2one(
        'res.company',
        string="Brand",
        tracking=True,
        help="Brand mà ứng viên ứng tuyển"
    )
    
    recruitment_type = fields.Selection(
        related='job_id.recruitment_type',
        string="Loại Tuyển Dụng",
        store=True,  # Store for filtering and searching
        readonly=True,  # Cannot be changed manually
        tracking=True,
        help="Loại tuyển dụng được kế thừa từ Job Position"
    )

    
    interview_schedule_id = fields.Many2one(
        'interview.schedule',
        string="Lịch Phỏng Vấn",
        help="Lịch PV đã được duyệt của brand",
        tracking=True
    )
    
    # ==================== SURVEY ====================
    
    survey_id = fields.Many2one(
        'survey.survey',
        string="Khảo Sát",
        domain=[('is_pre_interview', '=', True)],
        help="Khảo sát trước phỏng vấn gửi cho ứng viên"
    )
    
    survey_url = fields.Char(
        string="Link Khảo Sát",
        compute='_compute_survey_url',
        help="Link công khai cho ứng viên điền khảo sát"
    )
    
    # ==================== TRACKING ====================
    
    interview_invitation_sent = fields.Boolean(
        string="Đã Gửi Thư Mời PV",
        default=False,
        tracking=True
    )
    
    invitation_sent_date = fields.Datetime(
        string="Ngày Gửi Thư Mời",
        readonly=True
    )
    
    # ==================== COMPUTED FIELDS ====================
    
    @api.depends('survey_id')
    def _compute_survey_url(self):
        """Tạo link công khai của survey"""
        for rec in self:
            if rec.survey_id:
                base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
                rec.survey_url = f"{base_url}/survey/start/{rec.survey_id.access_token}"
            else:
                rec.survey_url = False
    
    # ==================== ONCHANGE ====================
    
    @api.onchange('job_id')
    def _onchange_job_id(self):
        """
        Khi chọn job → tự động set recruitment_type (via related field)
        và set stage phù hợp với loại tuyển dụng
        """
        if self.job_id and self.job_id.recruitment_type:
            # Find first stage of this recruitment type
            default_stage = self.env['hr.recruitment.stage'].search([
                ('recruitment_type', 'in', [self.job_id.recruitment_type, 'both'])
            ], order='sequence asc', limit=1)
            
            if default_stage:
                self.stage_id = default_stage
    
    @api.onchange('company_id')
    def _onchange_company_id(self):
        """Khi chọn brand → tự động load lịch PV đã xác nhận của tuần này"""
        if self.company_id:
            # Tìm lịch PV đã xác nhận của brand trong tuần hiện tại
            today = fields.Date.today()
            schedule = self.env['interview.schedule'].search([
                ('company_id', '=', self.company_id.id),
                ('state', '=', 'confirmed'),
                ('week_start_date', '<=', today),
                ('week_start_date', '>=', today - timedelta(days=7))
            ], limit=1)
            
            if schedule:
                self.interview_schedule_id = schedule
                _logger.info(f"Auto-load schedule: {schedule.display_name}")
            else:
                self.interview_schedule_id = False
                _logger.warning(f"Brand {self.company_id.name} chưa có lịch PV đã xác nhận cho tuần này")

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            # Set default stage based on job's recruitment_type
            # recruitment_type will auto-populate from job via related field
            if vals.get('job_id') and not vals.get('stage_id'):
                job = self.env['hr.job'].browse(vals['job_id'])
                if job.recruitment_type:
                    stage = self.env['hr.recruitment.stage'].search([
                        ('recruitment_type', 'in', [job.recruitment_type, 'both'])
                    ], order='sequence asc', limit=1)
                    if stage:
                        vals['stage_id'] = stage.id
        
        applicants = super().create(vals_list)
        
        return applicants
    
    def write(self, vals):
        # 1. Store old stage to detect change
        old_stages = {rec.id: rec.stage_id for rec in self}
        
        res = super(HrApplicant, self).write(vals)
        
        # 2. Check for stage changes
        if 'stage_id' in vals:
            new_stage = self.env['hr.recruitment.stage'].browse(vals['stage_id'])
            
            for rec in self:
                # === Case 1: PASS -> P0211 Onboarding ===
                if new_stage.hired_stage:
                    _logger.info(f"Applicant {rec.partner_name or rec.id} moved to HIRED stage. Ready for P0211 Onboarding.")
        
        # 3. Check for FAIL (Refused/Archived) -> P0213 Resignation
        if 'active' in vals and not vals['active']:
            for rec in self:
                # Use employee_id instead of emp_id
                if rec.employee_id: 
                    _logger.info(f"Applicant {rec.partner_name or rec.id} (Employee {rec.employee_id.name}) Refused. Triggering P0213 Resignation.")
                    
                    # Create Resignation Request
                    category = self.env.ref('M02_P0213_00.approval_category_resignation', raise_if_not_found=False)
                    if category:
                        # Check if request already exists
                        existing_req = self.env['approval.request'].search([
                            ('category_id', '=', category.id),
                            ('request_owner_id', '=', rec.employee_id.user_id.id),
                            ('request_status', 'not in', ['done', 'cancel'])
                        ], limit=1)
                        
                        if not existing_req:
                            self.env['approval.request'].create({
                                'name': f"Thôi việc: {rec.employee_id.name}",
                                'category_id': category.id,
                                'request_owner_id': rec.employee_id.user_id.id or self.env.user.id,
                                'resignation_reason': "Không đạt thử việc (Refused from Recruitment)",
                                'date_start': fields.Datetime.now(),
                            })
                    else:
                        _logger.warning("P0213 Resignation Category not found!")

        return res

    def archive_applicant(self):
        """Override to catch Refuse action if that's how they 'Fail'"""
        # Note: Standard Odoo calls toggle_active or write({'active': False})
        return super(HrApplicant, self).archive_applicant()
    
    # ==================== KANBAN STAGE FILTERING ====================
    
    @api.model
    def _read_group_stage_ids(self, stages, domain, order=None):
        """
        Override để chỉ hiển thị stages phù hợp với recruitment_type trong kanban view
        Check cả context VÀ domain để đảm bảo filter đúng
        """
        _logger.info(f"[STAGE FILTER] ========== START ==========")
        _logger.info(f"[STAGE FILTER] Domain received: {domain}")
        _logger.info(f"[STAGE FILTER] Context: {dict(self.env.context)}")
        _logger.info(f"[STAGE FILTER] Stages input count: {len(stages)}")
        _logger.info(f"[STAGE FILTER] Stages input names: {stages.mapped('name')}")
        
        search_domain = []
        target_type = False
        
        # 1. Ưu tiên check trong Domain (chính xác nhất)
        if domain:
            for leaf in domain:
                # Tìm điều kiện: ['recruitment_type', '=', 'store']
                if isinstance(leaf, (list, tuple)) and len(leaf) == 3:
                    if leaf[0] == 'recruitment_type' and leaf[1] == '=':
                        target_type = leaf[2]
                        _logger.info(f"[STAGE FILTER] ✓ Found type in domain: {target_type}")
                        break
        
        # 2. Nếu không có trong domain, check Context
        if not target_type:
            target_type = self.env.context.get('default_recruitment_type')
            if target_type:
                _logger.info(f"[STAGE FILTER] ✓ Found type in context: {target_type}")
            
        # 3. Apply Filter
        if target_type:
            # Chỉ lấy stages của loại này HOẶC 'both'
            # Điều này TỰ ĐỘNG loại bỏ các stages cũ (vì chúng có recruitment_type = False)
            search_domain = [('recruitment_type', 'in', [target_type, 'both'])]
            
            _logger.info(f"[STAGE FILTER] Applying search domain: {search_domain}")
            filtered_stages = stages.search(search_domain, order=order)
            _logger.info(f"[STAGE FILTER] ✓ Filtered stages count: {len(filtered_stages)}")
            _logger.info(f"[STAGE FILTER] ✓ Filtered stages names: {filtered_stages.mapped('name')}")
            _logger.info(f"[STAGE FILTER] ========== END ==========")
            return filtered_stages
        else:
            # Nếu không xác định loại, chỉ hiện stages mặc định (không có type)
            # hoặc stages chung. Tránh hiện stages custom của loại khác.
            _logger.warning(f"[STAGE FILTER] ⚠ No target type found, returning ALL stages")
            _logger.info(f"[STAGE FILTER] ========== END ==========")
            pass
            
        return stages
    
    # ==================== ACTIONS ====================
    
    def action_send_interview_invitation(self):
        """Gửi email mời phỏng vấn kèm link khảo sát"""
        self.ensure_one()
        
        # Validation
        if not self.company_id:
            raise exceptions.ValidationError("Vui lòng chọn Brand!")
        
        if not self.interview_schedule_id:
            raise exceptions.ValidationError("Vui lòng chọn Lịch Phỏng Vấn!")
        
        if self.interview_schedule_id.state != 'confirmed':
            raise exceptions.ValidationError("Lịch PV chưa được xác nhận bởi Store Manager!")
        
        if not self.survey_id:
            raise exceptions.ValidationError("Vui lòng chọn Khảo Sát!")
        
        if not self.email_from:
            raise exceptions.UserError("Ứng viên chưa có email!")
        
        # Tìm email template
        template = self.env.ref('M02_P0204_01.email_interview_invitation_v10', raise_if_not_found=False)
        
        if not template:
             # Fallback: Search by name
            template = self.env['mail.template'].search([('name', '=', 'Thư Mời Phỏng Vấn Cửa Hàng (Mới)')], limit=1)
            
        if not template:
            # Fallback 2: Search by old name
            template = self.env['mail.template'].search([('name', '=', 'Thư Mời Phỏng Vấn Cửa Hàng')], limit=1)

        if not template:
            _logger.error("Could not find email template 'M02_P0204_01.email_interview_invitation_v10' or by name")
            raise exceptions.ValidationError("Không tìm thấy email template! Vui lòng kiểm tra lại cấu hình Email Template.")
        
        # Gửi email
        template.send_mail(self.id, force_send=True)
        
        # Cập nhật trạng thái
        self.write({
            'interview_invitation_sent': True,
            'invitation_sent_date': fields.Datetime.now()
        })
        
        _logger.info(f"📧 Đã gửi thư mời PV cho {self.partner_name}")
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Đã gửi!',
                'message': f'Đã gửi thư mời phỏng vấn cho {self.partner_name}',
                'type': 'success',
            }
        }
