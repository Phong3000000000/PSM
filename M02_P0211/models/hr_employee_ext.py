# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import UserError
from markupsafe import Markup as markup
from datetime import timedelta
import logging

_logger = logging.getLogger(__name__)


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    # Odoo 19 - Lower group restriction for these fields to allow all internal users to see them
    x_psm_0211_contract_date_start = fields.Date(string="Contract Start Date", groups="base.group_user")
    
    # Phân loại nhân viên
    x_psm_0211_staff_type = fields.Selection([
        ('ops', 'Frontline (Ops)'),
        ('office', 'Office Staff')
    ], string='Staff Category', default='ops', compute='_compute_x_psm_0211_staff_type', store=True, readonly=True, groups="base.group_user")

    @api.depends('department_id', 'department_id.block_id', 'department_id.block_id.code')
    def _compute_x_psm_0211_staff_type(self):
        # Tìm nhanh mã loại hợp đồng Full-time
        full_time_type = self.env['hr.contract.type'].sudo().search([('name', 'ilike', 'Full')], limit=1)
        
        for rec in self:
            if rec.department_id and rec.department_id.block_id:
                block_code = (rec.department_id.block_id.code or '').upper()
                if block_code == 'OPS':
                    rec.x_psm_0211_staff_type = 'ops'
                elif block_code in ('RST', 'SV'):
                    rec.x_psm_0211_staff_type = 'office'
                    # Tự động chỉnh contract type là full time khi map ra office/rst
                    if full_time_type:
                        rec.contract_type_id = full_time_type.id
                else:
                    rec.x_psm_0211_staff_type = rec.x_psm_0211_staff_type or 'ops'
            else:
                rec.x_psm_0211_staff_type = rec.x_psm_0211_staff_type or 'ops'
    
    x_psm_0211_is_rst_employee_onb = fields.Boolean(string="Is RST Employee", compute="x_psm_0211_compute_is_rst_employee", store=True, groups="base.group_user")
    
    x_psm_0211_can_evaluate_probation = fields.Boolean(string="Can Evaluate Probation", compute="x_psm_0211_compute_can_evaluate_probation", groups="base.group_user")

    @api.depends('x_psm_0211_staff_type')
    def x_psm_0211_compute_is_rst_employee(self):
        for rec in self:
            rec.x_psm_0211_is_rst_employee_onb = (rec.x_psm_0211_staff_type == 'office')

    @api.depends('x_psm_0211_training_started', 'x_psm_0211_onboarding_ops_rst_training_process', 'x_psm_0211_onboarding_state', 'parent_id', 'x_psm_0211_staff_type')
    @api.depends_context('uid')
    def x_psm_0211_compute_can_evaluate_probation(self):
        self.x_psm_0211_compute_can_evaluate_logic()

    def x_psm_0211_compute_can_evaluate_logic(self):
        # Gọi helper lấy cấu hình 80% từ model gốc
        threshold = self.env['hr.employee'].x_psm_0211_get_evaluation_threshold()
        current_user = self.env.user
        is_hr_manager = current_user.has_group('hr.group_hr_manager') or current_user.has_group('base.group_system')
        is_public = (self._name == 'hr.employee.public')
        
        for rec in self:
            is_line_manager = False
            if rec.parent_id:
                # Sudo để chắc chắn đọc được user_id của sếp
                manager_user = rec.parent_id.sudo().user_id
                if manager_user and manager_user.id == current_user.id:
                    is_line_manager = True

            # Logic phân quyền đánh giá
            is_rst = (rec.x_psm_0211_staff_type == 'office')
            # Điều kiện đạt ngưỡng: Probation + Training >= thres (Training started)
            is_ready = (
                rec.x_psm_0211_onboarding_state == 'probation' and 
                rec.x_psm_0211_training_started and 
                rec.x_psm_0211_onboarding_ops_rst_training_process >= threshold
            )
            
            if is_public:
                # Ở Public (Danh bạ): Chỉ hiện nút cho RST (Văn phòng) cho cả Manager và HR
                rec.x_psm_0211_can_evaluate_probation = is_ready and is_rst and (is_line_manager or is_hr_manager)
            else:
                # Ở Private (Module Employee):
                if is_rst:
                    # RST (Văn phòng): Manager hoặc HR đều thấy
                    rec.x_psm_0211_can_evaluate_probation = is_ready and (is_line_manager or is_hr_manager)
                else:
                    # OPS (Frontline): Chỉ HR/Admin mới được đánh giá (như yêu cầu)
                    rec.x_psm_0211_can_evaluate_probation = is_ready and is_hr_manager

    # ========== ONBOARDING STATE ==========
    x_psm_0211_onboarding_state = fields.Selection([
        ('pending',   'Pending Documents'),
        ('submitted', 'Submitted'),
        ('approved',  'Approved'),
        ('probation', 'Under Probation'),
        ('done',      'Passed'),
        ('signed',    'Signed'),
        ('refused',   'Refused'),
    ], string='Onboarding Status',
       default='pending',
       tracking=True,
       required=True,
       copy=False)

    x_psm_0211_contract_sign_request_id = fields.Many2one('sign.request', string='Contract Signature Request', copy=False)
    x_psm_0211_contract_signed = fields.Boolean(
        string='Contract Signed',
        compute='_compute_x_psm_0211_contract_signed',
        help='True if the employee has at least one signed sign.request.'
    )

    @api.depends('x_psm_0211_contract_sign_request_id.state')
    def _compute_x_psm_0211_contract_signed(self):
        for rec in self:
            # Ưu tiên check theo id liên kết
            if rec.x_psm_0211_contract_sign_request_id and rec.x_psm_0211_contract_sign_request_id.state == 'signed':
                rec.x_psm_0211_contract_signed = True
            else:
                # Nếu không có id hoặc id chưa ký, search fallback theo partner để chính xác tuyệt đối
                partner = rec.user_partner_id or rec.work_contact_id
                if partner:
                    signed_request = self.env['sign.request.item'].sudo().search_count([
                        ('partner_id', '=', partner.id),
                        ('sign_request_id.state', '=', 'signed')
                    ])
                    rec.x_psm_0211_contract_signed = signed_request > 0
                else:
                    rec.x_psm_0211_contract_signed = False

    x_psm_0211_management_state = fields.Selection([
        ('adecco', 'Managed by Adecco'),
        ('good_day', 'Managed by McD (Good Day)'),
    ], string='Management Entity', default='adecco', tracking=True)
    x_psm_0211_welcome_email_sent = fields.Boolean(string='Email Sent', default=False, copy=False)
    contract_type_id_name = fields.Char(related='contract_type_id.name', string='Contract Type Name')
    x_psm_0211_is_full_time = fields.Boolean(compute='_compute_x_psm_0211_is_full_time', string='Is Full-time')
    x_psm_0211_show_adecco_banner = fields.Boolean(compute='_compute_x_psm_0211_management_display')
    x_psm_0211_show_goodday_banner = fields.Boolean(compute='_compute_x_psm_0211_management_display')
    x_psm_0211_show_transfer_button = fields.Boolean(compute='_compute_x_psm_0211_management_display')

    x_psm_0211_onboarding_refusal_reason = fields.Char(string='Onboarding Refusal Reason')

    @api.depends('contract_type_id')
    def _compute_x_psm_0211_is_full_time(self):
        for rec in self:
            # Check standard contract_type_id name
            name = (rec.contract_type_id.name or '').lower()
            # Logic mới: Đã là Part-time hoặc Thời vụ thì KHÔNG được coi là Full-time
            if 'part' in name or 'thời vụ' in name:
                rec.x_psm_0211_is_full_time = False
            else:
                rec.x_psm_0211_is_full_time = 'full' in name or 'chính thức' in name

    @api.depends('x_psm_0211_onboarding_state', 'x_psm_0211_management_state', 'x_psm_0211_staff_type', 'x_psm_0211_is_full_time')
    def _compute_x_psm_0211_management_display(self):
        for rec in self:
            rec.x_psm_0211_show_adecco_banner = (
                rec.x_psm_0211_onboarding_state == 'signed' and
                rec.x_psm_0211_staff_type == 'ops'
            )
            rec.x_psm_0211_show_goodday_banner = (
                rec.x_psm_0211_onboarding_state == 'signed' and
                (rec.x_psm_0211_staff_type == 'office' or rec.x_psm_0211_management_state == 'good_day')
            )
            rec.x_psm_0211_show_transfer_button = (
                rec.x_psm_0211_onboarding_state == 'signed' and
                rec.x_psm_0211_staff_type == 'ops' and
                rec.x_psm_0211_is_full_time and
                rec.x_psm_0211_management_state == 'adecco'
            )


    def action_psm_notify_probation_passed(self):
        """Hệ thống tự động xác nhận đậu thử việc và gửi thông báo cho Agency.
        Đã cập nhật để dùng trường contract_type_id mặc định của Odoo.
        """
        self.ensure_one()
        # Chuyển trạng thái sang Done
        self.write({'x_psm_0211_onboarding_state': 'done'})

        # Gửi email chúc mừng nội bộ cho nhân viên
        congrats_template = self.env.ref('M02_P0211.email_template_probation_congrats', raise_if_not_found=False)
        recipient = self.work_email or self.private_email
        if congrats_template and recipient:
            try:
                congrats_template.with_context(lang=self.env.user.lang).send_mail(self.id, force_send=True, email_values={
                    'email_to': recipient,
                    'recipient_ids': [],
                    'partner_ids': [],
                })
            except Exception as e:
                _logger.warning("Failed to send probation congrats email to %s: %s", self.name, e)
        else:
            _logger.warning("Skip probation congrats email for %s due to missing template or recipient", self.name)

        # Gửi email thông báo cho Agency (Adecco hoặc Good Day)
        agency_email = self.env['x_psm.hr.adecco.config'].sudo().get_x_psm_agency_email(x_psm_0211_staff_type=self.x_psm_0211_staff_type or 'ops')

        # Xác định template dựa trên loại hợp đồng ('Full-time' hoặc 'Part-time')
        # Dựa vào tên loại hợp đồng trong hr.contract.type
        ctype_name = (self.contract_type_id.name or '').lower()
        if 'part' in ctype_name or 'thời vụ' in ctype_name:
            is_ft = False
        else:
            is_ft = 'full' in ctype_name or 'chính thức' in ctype_name

        template_id = (self.env.ref('M02_P0211.email_template_probation_passed_ft_v2').id
                       if is_ft else
                       self.env.ref('M02_P0211.email_template_probation_passed_pt_v2').id)

        template = self.env['mail.template'].browse(template_id)
        template.with_context(agency_email=agency_email).send_mail(self.id, force_send=True, email_values={
            'email_to': agency_email,
            'recipient_ids': [],
            'partner_ids': [],
        })

        agency_label = "Good Day" if self.x_psm_0211_staff_type == 'office' else "Adecco"
        self.message_post(body=f"Probation completion confirmed. "
                               f"Notification email has been sent to {agency_label} ({agency_email}).")

    def action_psm_transfer_to_good_day(self):
        """Chuyển đổi quản lý từ Adecco sang Good Day (McD) cho NV Full-time."""
        self.ensure_one()
        if self.x_psm_0211_management_state == 'good_day':
            raise UserError("This employee is already managed by Good Day.")
        
        self.write({'x_psm_0211_management_state': 'good_day'})
        self.message_post(body=markup("🔄 Management entity transferred to Good Day (McD)."))

    # ========== PROBATION (Thử việc) ==========
    # Số ngày thử việc: đọc từ System Parameter, HR sửa qua Settings → Technical → System Parameters
    # Key: M02_P0211.probation_duration_days, mặc định 30

    x_psm_0211_probation_start_date = fields.Date(
        string='Probation Start Date',
        tracking=True,
        groups='hr.group_hr_user',
    )
    x_psm_0211_probation_end_date = fields.Date(
        string='Probation End Date',
        compute='_compute_psm_0211_probation_end_date',
        store=True,
        groups='hr.group_hr_user',
    )
    x_psm_0211_probation_days_remaining = fields.Integer(
        string='Probation Days Remaining',
        compute='_compute_psm_probation_0211_days_remaining',
        groups='hr.group_hr_user',
    )
    def x_psm_0211_get_probation_duration_days(self):
        """Đọc số ngày thử việc từ System Parameter, mặc định 30."""
        return int(self.env['ir.config_parameter'].sudo().get_param(
            'M02_P0211.probation_duration_days', '30'
        ))

    @api.depends('x_psm_0211_probation_start_date')
    def _compute_psm_0211_probation_end_date(self):
        for rec in self:
            if rec.x_psm_0211_probation_start_date:
                duration = rec.x_psm_0211_get_probation_duration_days()
                rec.x_psm_0211_probation_end_date = rec.x_psm_0211_probation_start_date + timedelta(days=duration)
            else:
                rec.x_psm_0211_probation_end_date = False

    @api.depends('x_psm_0211_probation_start_date', 'x_psm_0211_probation_end_date', 'x_psm_0211_onboarding_state')
    def _compute_psm_probation_0211_days_remaining(self):
        today = fields.Date.today()
        for rec in self:
            if rec.x_psm_0211_probation_end_date and rec.x_psm_0211_onboarding_state in ('approved', 'probation', 'done'):
                if rec.x_psm_0211_probation_start_date and today < rec.x_psm_0211_probation_start_date:
                    # Chưa đến ngày bắt đầu thử việc → hiện tổng số ngày thử việc (max)
                    rec.x_psm_0211_probation_days_remaining = rec.x_psm_0211_get_probation_duration_days()
                else:
                    # Đã vào giai đoạn thử việc → tính ngày còn lại
                    delta = (rec.x_psm_0211_probation_end_date - today).days
                    rec.x_psm_0211_probation_days_remaining = max(delta, 0)
            else:
                rec.x_psm_0211_probation_days_remaining = 0


    # Removed compute count cũ

    def action_psm_open_probation_wizard(self):
        """Mở Wizard đánh giá thử việc."""
        self.ensure_one()
        return {
            'name': 'Probation Performance Evaluation',
            'type': 'ir.actions.act_window',
            'res_model': 'hr.probation.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_employee_id': self.id}
        }

    def _send_psm_0211_probation_fail_email(self, reason):
        """Gửi email cảm ơn + thông báo không đạt thử việc."""
        template = self.env.ref('M02_P0211.email_template_probation_failed', raise_if_not_found=False)
        if template:
            template.with_context(refusal_reason=reason).send_mail(self.id, force_send=True)

    @api.model
    def x_psm_0211_get_evaluation_threshold(self):
        """Lấy tỉ lệ % tối thiểu để bắt đầu đánh giá (mặc định 80%)."""
        return float(self.env['ir.config_parameter'].sudo().get_param('M02_P0211.evaluation_threshold', '80.0'))



    # ========== DOCUMENT FIELDS (lưu trực tiếp trên hr.employee) ==========
    # Odoo 19: Tài liệu portal được lưu thẳng tại đây và controller bộ sync vào res.partner

    # 1. Profile Photo
    x_psm_0211_passport_photo = fields.Binary(
        string="Passport Photo (3x4)", attachment=True, groups='hr.group_hr_user')
    x_psm_0211_passport_photo_filename = fields.Char(
        string="Photo Filename", groups='hr.group_hr_user')

    # 2. Identity Card (Bắt buộc)
    x_psm_0211_id_card = fields.Binary(
        string="Identity Card", attachment=True, groups='hr.group_hr_user')
    x_psm_0211_id_card_filename = fields.Char(
        string="Identity Card Filename", groups='hr.group_hr_user')
    
    x_psm_0211_id_card_front = fields.Binary(
        string="ID Card (Front)", attachment=True, groups='hr.group_hr_user')
    x_psm_0211_id_card_front_filename = fields.Char(
        string="ID Card Front Filename", groups='hr.group_hr_user')

    x_psm_0211_id_card_back = fields.Binary(
        string="ID Card (Back)", attachment=True, groups='hr.group_hr_user')
    x_psm_0211_id_card_back_filename = fields.Char(
        string="ID Card Back Filename", groups='hr.group_hr_user')

    # 3. Personal History Group (Bắt buộc 1 trong 4)
    x_psm_0211_curriculum_vitae = fields.Binary(
        string="Personal History", attachment=True, groups='hr.group_hr_user')
    x_psm_0211_curriculum_vitae_filename = fields.Char(
        string="Personal History Filename", groups='hr.group_hr_user')

    x_psm_0211_household_registration = fields.Binary(
        string="Household Registration", attachment=True, groups='hr.group_hr_user')
    x_psm_0211_household_registration_filename = fields.Char(
        string="Household Registration Filename", groups='hr.group_hr_user')

    # 4. Health & Insurance
    x_psm_0211_health_certificate = fields.Binary(
        string="Health Certificate (TT32)", attachment=True, groups='hr.group_hr_user')
    x_psm_0211_health_certificate_filename = fields.Char(
        string="Health Certificate Filename", groups='hr.group_hr_user')

    x_psm_0211_social_insurance = fields.Binary(
        string="Social Insurance (BHXH)", attachment=True, groups='hr.group_hr_user')
    x_psm_0211_social_insurance_filename = fields.Char(
        string="Social Insurance Filename", groups='hr.group_hr_user')

    # 5. Professional & Driving
    x_psm_0211_driving_license = fields.Binary(
        string="Driving License", attachment=True, groups='hr.group_hr_user')
    x_psm_0211_driving_license_filename = fields.Char(
        string="Driving License Filename", groups='hr.group_hr_user')

    x_psm_0211_judicial_record = fields.Binary(
        string="Judicial Record", attachment=True, groups='hr.group_hr_user')
    x_psm_0211_judicial_record_filename = fields.Char(
        string="Judicial Record Filename", groups='hr.group_hr_user')

    x_psm_0211_professional_certificate = fields.Binary(
        string="Professional Degree", attachment=True, groups='hr.group_hr_user')
    x_psm_0211_professional_certificate_filename = fields.Char(
        string="Degree Filename", groups='hr.group_hr_user')

    x_psm_0211_additional_certificates = fields.Binary(
        string="Other Certificates", attachment=True, groups='hr.group_hr_user')
    x_psm_0211_additional_certificates_filename = fields.Char(
        string="Other Certificates Filename", groups='hr.group_hr_user')

    # Tracking portal submissions
    x_psm_0211_portal_last_update = fields.Datetime(
        string="Last Portal Update", groups='hr.group_hr_user')
    x_psm_0211_portal_updates_count = fields.Integer(
        string="Field Update Count", default=0, groups='hr.group_hr_user')
    x_psm_portal_revision_count = fields.Integer(
        string="Submission Count", default=0, groups='hr.group_hr_user')
        
    # ========== FOOD SAFETY (VSATTP) ==========
    x_psm_0211_vsattp_survey_id = fields.Many2one('survey.survey', string="Food Safety Survey (VSATTP)", help="Food Safety assessment for staff", groups='hr.group_hr_user')
    x_psm_0211_vsattp_user_input_id = fields.Many2one('survey.user_input', compute='_compute_x_psm_0211_vsattp_user_input', string="Latest Assessment", groups='hr.group_hr_user')
    x_psm_0211_vsattp_survey_state = fields.Selection(
        [('new', 'Not Started'), ('in_progress', 'In Progress'), ('done', 'Completed')],
        compute='_compute_x_psm_0211_vsattp_survey_details', string="Assessment Status", groups='hr.group_hr_user')
    x_psm_0211_vsattp_survey_score = fields.Float(compute='_compute_x_psm_0211_vsattp_survey_details', string="Assessment Score (%)", groups='hr.group_hr_user')
    x_psm_0211_vsattp_survey_url = fields.Char(compute='_compute_x_psm_0211_vsattp_survey_details', string="Assessment Link", groups='hr.group_hr_user')
    x_psm_0211_vsattp_survey_done = fields.Boolean(string="Assessment Completed", tracking=True, groups='hr.group_hr_user')

    @api.depends('x_psm_0211_vsattp_user_input_id', 'x_psm_0211_vsattp_user_input_id.state')
    def _compute_x_psm_0211_vsattp_survey_details(self):
        for rec in self:
            if rec.x_psm_0211_vsattp_user_input_id:
                rec.x_psm_0211_vsattp_survey_state = rec.x_psm_0211_vsattp_user_input_id.state
                rec.x_psm_0211_vsattp_survey_score = rec.x_psm_0211_vsattp_user_input_id.scoring_percentage
                
                # Ghép thêm Base URL để có link đầy đủ
                base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url', '')
                relative_url = rec.x_psm_0211_vsattp_user_input_id.get_start_url()
                rec.x_psm_0211_vsattp_survey_url = f"{base_url.rstrip('/')}{relative_url}"
                # Note: x_psm_0211_vsattp_survey_done is updated in write/onchange, not here to avoid side-effects
                pass
            else:
                rec.x_psm_0211_vsattp_survey_state = False
                rec.x_psm_0211_vsattp_survey_score = 0.0
                rec.x_psm_0211_vsattp_survey_url = False
                
    @api.constrains('x_psm_0211_vsattp_survey_done')
    def x_psm_check_vsattp_survey_done(self):
        for rec in self:
            if not rec.x_psm_0211_vsattp_survey_done and rec._origin.x_psm_0211_vsattp_survey_done:
                raise UserError("You cannot uncheck the Assessment completion once it has been verified.")

    @api.depends('x_psm_0211_vsattp_survey_id', 'work_email', 'private_email', 'work_contact_id')
    def _compute_x_psm_0211_vsattp_user_input(self):
        for rec in self:
            if not rec.x_psm_0211_vsattp_survey_id:
                rec.x_psm_0211_vsattp_user_input_id = False
                continue
                
            email_to_check = rec.work_email or rec.private_email
            domain = [('survey_id', '=', rec.x_psm_0211_vsattp_survey_id.id)]
            if rec.work_contact_id:
                domain += ['|', ('partner_id', '=', rec.work_contact_id.id), ('email', '=', email_to_check)]
            elif email_to_check:
                domain += [('email', '=', email_to_check)]
            else:
                domain += [('id', '=', 0)]
                
            last_input = self.env['survey.user_input'].sudo().search(domain, order='create_date desc', limit=1)
            rec.x_psm_0211_vsattp_user_input_id = last_input.id if last_input else False

    def action_view_psm_0211_vsattp_results(self):
        self.ensure_one()
        if not self.x_psm_0211_vsattp_user_input_id:
            from odoo.exceptions import UserError
            raise UserError("Nhân viên này chưa có dữ liệu làm bài khảo sát.")
            
        return {
            'name': 'Food Safety Assessment Details',
            'type': 'ir.actions.act_window',
            'res_model': 'survey.user_input',
            'view_mode': 'form',
            'res_id': self.x_psm_0211_vsattp_user_input_id.id,
            'target': 'current',
        }

    x_psm_0211_onboarding_task_ids = fields.One2many('x_psm.hr.employee.onboarding.task', 'employee_id', string="Onboarding Checklist")
    x_psm_0211_onboarding_pending_count = fields.Integer(compute='_compute_x_psm_0211_onboarding_progress', store=True)
    x_psm_0211_onboarding_done_count = fields.Integer(compute='_compute_x_psm_0211_onboarding_progress', store=True)
    x_psm_0211_onboarding_total_count = fields.Integer(compute='_compute_x_psm_0211_onboarding_progress', store=True)
    x_psm_0211_onboarding_progress = fields.Float(string="Onboarding Progress", compute='_compute_x_psm_0211_onboarding_progress', store=True)

    @api.depends('x_psm_0211_onboarding_task_ids.x_psm_is_done', 'x_psm_0211_training_task_ids.x_psm_is_done')
    def _compute_x_psm_0211_onboarding_progress(self):
        for rec in self:
            # 1. Checklist Onboarding (Từ mail.activity.plan)
            onboarding_tasks = rec.x_psm_0211_onboarding_task_ids
            onboarding_done = len(onboarding_tasks.filtered(lambda t: t.x_psm_is_done))
            onboarding_total = len(onboarding_tasks)

            # 2. Checklist Đào tạo (Từ hr.training.config)
            training_tasks = rec.x_psm_0211_training_task_ids
            training_done = len(training_tasks.filtered(lambda t: t.x_psm_is_done))
            training_total = len(training_tasks)
            
            total = onboarding_total + training_total
            done = onboarding_done + training_done
            
            rec.x_psm_0211_onboarding_pending_count = total - done
            rec.x_psm_0211_onboarding_done_count = done
            rec.x_psm_0211_onboarding_total_count = total
            rec.x_psm_0211_onboarding_progress = (done / total * 100.0) if total > 0 else 0.0

    # ========== TRAINING & ORIENTATION ==========
    x_psm_0211_training_state = fields.Selection([
        ('not_started', 'Not Started'),
        ('in_progress', 'In Training'),
        ('completed',   'Completed'),
    ], string='Training Status', compute='_compute_x_psm_0211_training_state', store=True, tracking=True)


    x_psm_0211_training_started = fields.Boolean(string="Training Started", default=False)
    x_psm_0211_training_start_date = fields.Date(string="Training Start Date")
    
    # Danh sách đào tạo lưu trữ tiến độ được tạo tự động từ cấu hình
    x_psm_0211_training_task_ids = fields.One2many('x_psm.hr.employee.training.task', 'employee_id', string="Training Checklist")

    x_psm_0211_onboarding_ops_rst_training_process = fields.Float(string="Training Progress", compute='_compute_x_psm_0211_onboarding_ops_rst_training_process', store=True)

    @api.depends('x_psm_0211_training_task_ids.x_psm_is_done')
    def _compute_x_psm_0211_onboarding_ops_rst_training_process(self):
        for rec in self:
            tasks = rec.x_psm_0211_training_task_ids
            total_tasks = len(tasks)
            done_tasks = len(tasks.filtered(lambda t: t.x_psm_is_done))
            rec.x_psm_0211_onboarding_ops_rst_training_process = (done_tasks / total_tasks * 100.0) if total_tasks > 0 else 0.0
            
            # Kích hoạt thông báo cho Line Manager nếu đạt ngưỡng 80%
            threshold = rec.x_psm_0211_get_evaluation_threshold()
            if rec.x_psm_0211_onboarding_ops_rst_training_process >= threshold:
                rec.x_psm_0211_notify_evaluation_ready()
            
    @api.depends('x_psm_0211_onboarding_ops_rst_training_process')
    def _compute_x_psm_0211_training_state(self):
        for rec in self:
            if rec.x_psm_0211_onboarding_ops_rst_training_process == 100:
                rec.x_psm_0211_training_state = 'completed'
            elif rec.x_psm_0211_onboarding_ops_rst_training_process > 0:
                rec.x_psm_0211_training_state = 'in_progress'
            else:
                rec.x_psm_0211_training_state = 'not_started'

    def action_psm_start_training_journey(self):
        self.ensure_one()
        from datetime import timedelta
        from markupsafe import Markup as markup
        
        self.x_psm_0211_training_started = True
        self.x_psm_0211_training_start_date = fields.Date.today()
        
        # 1. Xử lý kịch bản đào tạo (Checklist)
        self.x_psm_0211_training_task_ids.sudo().unlink() # Chống trùng lặp: Xóa các task cũ trước khi tạo lại
        
        now_date = fields.Date.today()
        configs = self.env['x_psm.hr.training.config'].sudo().search([
            ('active', '=', True),
            ('x_psm_staff_type', '=', self.x_psm_0211_staff_type or 'ops')
        ])
        
        manager_user = self.parent_id.user_id or self.env.user
        
        for config in configs:
            target_date_only = now_date + timedelta(days=config.x_psm_days_after_start)
            
            # Tạo Checklist cho nhân viên
            task = self.env['x_psm.hr.employee.training.task'].sudo().create({
                'employee_id': self.id,
                'x_psm_origin_config_id': config.id,
                'name': config.name,
                'x_psm_doc_code': config.x_psm_code,
                'x_psm_description': config.x_psm_description,
                'sequence': config.sequence,
                'x_psm_date_planned': target_date_only,
                'x_psm_is_done': False,
            })

            # 2. Tạo activity cho Manager (Cả OPS lẫn RST)
            if manager_user:
                act = self.activity_schedule(
                    'mail.mail_activity_data_todo',
                    date_deadline=task.x_psm_date_planned,
                    summary=f"Đào tạo: {task.name} - {self.name}",
                    note=f"<b>Hướng dẫn:</b> {task.x_psm_description or 'Theo lộ trình đào tạo chuẩn'}",
                    user_id=manager_user.id
                )
                task.x_psm_activity_id = act.id
            
        self.env.cr.flush() # Đẩy dữ liệu xuống DB ngay lập tức
        self.invalidate_recordset(['x_psm_0211_training_task_ids']) # Xóa cache để Odoo lấy dữ liệu mới từ DB

        scheduled_msg = f"Training roadmap activated for {self.name}. System has created {len(configs)} activities for Manager ({manager_user.name})."
        self.message_post(body=markup(scheduled_msg))

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Activation Successful!',
                'message': scheduled_msg,
                'type': 'success',
                'sticky': False,
            }
        }
    # ========== ACTIONS ==========

    @api.model_create_multi
    def create(self, vals_list):
        """Standard create for HR Employee."""
        return super().create(vals_list)

    def write(self, vals):
        """
        1. Quản lý trạng thái onboarding và các hồ sơ liên quan (Manual sending).
        2. Tự động tạo Activity cho Line Manager khi chuyển sang trạng thái Thử việc.
        """
        res = super(HrEmployee, self).write(vals)
        
        # Logic 2: Tạo Activity Thử việc (Đã có từ trước)
        if 'x_psm_0211_onboarding_state' in vals and vals['x_psm_0211_onboarding_state'] == 'probation':
            for rec in self:
                if rec.parent_id and rec.parent_id.user_id:
                    existing = self.env['mail.activity'].sudo().search([
                        ('res_model', '=', 'hr.employee'),
                        ('res_id', '=', rec.id),
                        ('user_id', '=', rec.parent_id.user_id.id),
                        ('summary', 'like', 'Đánh giá thử việc')
                    ], limit=1)
                    if not existing:
                        rec.activity_schedule(
                            'mail.mail_activity_data_todo',
                            date_deadline=rec.x_psm_0211_probation_end_date or fields.Date.today(),
                            summary=f"Đánh giá thử việc: {rec.name}",
                            note=f"Nhân viên {rec.name} đã được chuyển sang trạng thái Thử việc. Vui lòng thực hiện đánh giá kết quả Onboarding.",
                            user_id=rec.parent_id.user_id.id
                        )
        return res

    def x_psm_0211_notify_evaluation_ready(self):
        """Thông báo cho Line Manager khi nhân viên đủ điều kiện đánh giá (>=80% đào tạo)."""
        for rec in self:
            if rec.x_psm_0211_onboarding_state != 'probation' or not rec.parent_id or not rec.parent_id.user_id:
                continue

            # 1. Kiểm tra xem đã có activity đánh giá chưa (tránh tạo trùng)
            existing_act = self.env['mail.activity'].sudo().search([
                ('res_model', '=', 'hr.employee'),
                ('res_id', '=', rec.id),
                ('user_id', '=', rec.parent_id.user_id.id),
                ('summary', 'like', 'Đánh giá thử việc')
            ], limit=1)

            if not existing_act:
                # 2. Tạo Activity
                rec.activity_schedule(
                    'mail.mail_activity_data_todo',
                    date_deadline=fields.Date.today(),
                    summary=f"🚀 Đã đủ điều kiện Đánh giá thử việc: {rec.name}",
                    note=f"Nhân viên {rec.name} đã hoàn thành {rec.x_psm_0211_onboarding_ops_rst_training_process}% lộ trình đào tạo.\n"
                         f"Hệ thống đã kích hoạt nút 'Evaluation Probation' để bạn có thể thực hiện đánh giá kết quả sớm.",
                    user_id=rec.parent_id.user_id.id
                )

                # 3. Gửi Popup thông báo (Bus Notification) cho Manager nếu online
                try:
                    title = f"📢 Đủ điều kiện đánh giá: {rec.name}"
                    message = f"Nhân viên {rec.name} đã hoàn thành khóa đào tạo ({rec.x_psm_0211_onboarding_ops_rst_training_process}%). Bạn có thể đánh giá thử việc ngay bây giờ!"
                    
                    # Odoo 17/19 Bus send notification to specific user
                    notification = [{'type': 'display_notification', 'payload': {
                        'title': title,
                        'message': message,
                        'type': 'success',
                        'sticky': True, # Manager nên thấy tin này lâu hơn
                        'links': [{
                            'label': 'Đi tới hồ sơ nhân viên',
                            'url': f'#id={rec.id}&model=hr.employee&view_type=form',
                        }]
                    }}]
                    self.env['bus.bus'].sudo()._sendone(rec.parent_id.user_id.partner_id, 'notification', notification)
                except Exception as e:
                    _logger.warning("Failed to send bus notification to manager: %s", e)

    @api.constrains('work_email')
    def x_psm_0211_check_work_email_required(self):
        for rec in self:
            if not rec.work_email:
                raise UserError("Please enter a Work Email for the employee before saving. Email is required for Onboarding notifications.")

    def action_psm_send_welcome_email(self):
        """
        Gửi Email Chào Mừng sử dụng template XML 'email_template_onboarding_welcome'.
        Được gọi tự động khi user được tạo (Create User) hoặc có thể gọi thủ công.
        """
        self.ensure_one()
        return self._action_psm_send_welcome_email_to_rec()

    def _action_psm_send_welcome_email_to_rec(self):
        """Logic cốt lõi để gửi email chào mừng, dùng chung cho cả gọi tay và tự động."""
        email_to = self.work_email or (self.work_contact_id.email if self.work_contact_id else None)
        if not email_to:
            raise UserError('Employee missing Work Email. Please provide an email before sending.')

        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url', '')
        partner = self.work_contact_id
        
        # Xác định loại hợp đồng để gắn vào link (slug)
        ctype_name = (self.contract_type_id.name or '').lower()
        contract_slug = 'fulltime' if 'full' in ctype_name else 'parttime'
        
        signup_url = f"{base_url}/my/onboard_info"

        # Tạo signup link cho user đã có
        if partner and partner.user_ids:
            partner.sudo().signup_prepare(signup_type='reset')
            urls = partner.sudo()._get_signup_url_for_action()
            raw_signup_url = urls.get(partner.id, f"{base_url}/my/onboard_info")
            
            # Nối param redirect vào URL signup native của Odoo
            import urllib.parse
            redirect_path = f"/my/onboard_info"
            encoded_redirect = urllib.parse.quote(redirect_path)
            
            connector = '&' if '?' in raw_signup_url else '?'
            signup_url = f"{raw_signup_url}{connector}redirect={encoded_redirect}"

        # Gửi email bằng template XML custom
        template = self.env.ref('M02_P0211.email_template_onboarding_welcome', raise_if_not_found=False)
        if template:
            try:
                template.with_context(
                    base_url=base_url,
                    signup_url=signup_url,
                    employee_login=email_to,
                ).send_mail(self.id, force_send=True)
            except Exception as e:
                _logger.error("Failed to send welcome email for %s: %s", self.name, str(e))
                raise UserError(f'Cannot send email: {str(e)}')
        else:
            raise UserError('Email template "email_template_onboarding_welcome" not found. Please upgrade the module.')

        self.message_post(body=markup(f'Welcome onboarding email sent to {email_to}.'))
        self.x_psm_0211_welcome_email_sent = True
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Email sent successfuly!',
                'message': f'Welcome email has been sent to {email_to}',
                'type': 'success',
                'sticky': False,
            }
        }

    def action_psm_automated_onboarding_setup(self):
        """
        Gửi Email Onboarding cho nhân viên đã có tài khoản User:
        - Kiểm tra Contract Type.
        - Đảm bảo nhân viên đã được liên kết với một User (hoặc tìm theo Email).
        - Thực hiện reset password và gửi link onboarding.
        """
        for rec in self:
            # 1. BẮT BUỘC: Phải có Loại hợp đồng mới được gửi mail
            if not rec.contract_type_id:
                raise UserError(f"Vui lòng chọn Loại hợp đồng cho nhân viên {rec.name} trước khi gửi Email Onboarding.")

            email_to = rec.work_email or (rec.work_contact_id.email if rec.work_contact_id else None)
            if not email_to:
                raise UserError(f"Nhân viên {rec.name} thiếu Email công việc. Vui lòng bổ sung trước khi gửi.")

            # 2. KIỂM TRA USER: Ưu tiên dùng user_id đã gán, hoặc tìm theo login
            user = rec.user_id
            if not user:
                user = self.env['res.users'].sudo().search([('login', '=', email_to)], limit=1)
                if user and not rec.user_id:
                    rec.user_id = user.id
            
            if not user:
                raise UserError(f"Không tìm thấy tài khoản User cho {rec.name} với email {email_to}. "
                                "Vui lòng tạo User cho nhân viên này trước hoặc gán vào tab 'Settings' trên hồ sơ nhân viên.")

            # 3. Tiến hành gửi mail (Hàm này đã có logic signup_prepare('reset'))
            rec._action_psm_send_welcome_email_to_rec()
            rec.x_psm_0211_welcome_email_sent = True

    def action_psm_show_onboarding_progress(self):
        self.ensure_one()
        return {
            'name': 'Onboarding Progress (Pending Tasks)',
            'type': 'ir.actions.act_window',
            'res_model': 'mail.activity',
            'view_mode': 'list,form',
            'domain': [('res_model', '=', 'hr.employee'), ('res_id', '=', self.id)],
            'context': {'default_res_model': 'hr.employee', 'default_res_id': self.id},
        }

    def action_psm_approve_onboarding(self):
        """Bước 4 Đạt: Duyệt hồ sơ → 'approved' + thiết lập loại công việc + bắt đầu thử việc."""
        for rec in self:
            if rec.x_psm_0211_onboarding_state not in ('pending', 'submitted'):
                raise UserError(
                    f'Cannot approve employee in status "{rec.x_psm_0211_onboarding_state}".'
                )
            
            # YÊU CẦU: Buộc HR phải chọn Loại hợp đồng (contract_type_id) trước khi duyệt
            if not rec.contract_type_id:
                raise UserError(
                    "Please select a Contract Type (e.g., Full-time/Part-time) for this employee before approving documents!"
                )

            rec.x_psm_0211_onboarding_state = 'approved'
            rec.message_post(
                body=markup(f'Documents approved.\\n'
                     f'Contract Type: {rec.contract_type_id.name}\\n'
                     f'Use the "Launch Plan" button to select start date and initialize the onboarding roadmap.')
            )

    def action_psm_reject_onboarding(self):
        """Bước 4 Không đạt: Từ chối hồ sơ ngay từ đầu (Chưa vào thử việc)."""
        for rec in self:
            if rec.x_psm_0211_onboarding_state == 'refused':
                raise UserError('This application has already been refused.')
            
            rec.x_psm_0211_onboarding_state = 'refused'
            
            # Gửi mail Từ chối hồ sơ (Giai đoạn đầu)
            template = self.env.ref('M02_P0211.email_template_onboarding_refused', raise_if_not_found=False)
            if template:
                template.send_mail(rec.id, force_send=True)
                
            rec.message_post(
                body=markup('Documents refused. Notification email sent to applicant.')
            )

    # ========== ONBOARDING PLAN (Activities checklist) ==========


    def action_psm_send_onboarding_plan_email(self, schedule_wizard):
        """ Gửi email thông báo nhận việc + kế hoạch Onboarding + link VSATTP (nếu có) """
        self.ensure_one()
        
        template = self.env.ref('M02_P0211.email_template_onboarding_plan', raise_if_not_found=False)
        if not template:
            _logger.warning("Không tìm thấy email template 'email_template_onboarding_plan'")
            return

        # Build checklist html từ wizard
        checklist_html = ""
        for template_activity in schedule_wizard.plan_id.template_ids:
            task_name = template_activity.summary or template_activity.activity_type_id.name
            
            # TÍNH TOÁN NGƯỜI PHỤ TRÁCH CHO EMAIL (SYNC VỚI ROLE)
            responsible = False
            role = template_activity.x_psm_0211_responsible_role if hasattr(template_activity, 'x_psm_0211_responsible_role') else 'manager'
            
            if template_activity.responsible_type == 'on_demand':
                # Nếu là nhân viên Office, phân biệt giữa Manager và IT
                if self.x_psm_0211_staff_type == 'office':
                    if role == 'manager':
                        responsible = schedule_wizard.x_psm_0211_bp_user_id
                    else:
                        responsible = schedule_wizard.plan_on_demand_user_id
                else:
                    responsible = schedule_wizard.plan_on_demand_user_id
            else:
                resp_info = template_activity._determine_responsible(schedule_wizard.plan_on_demand_user_id, self)
                responsible = resp_info.get('responsible')
            
            resp_name = responsible.name if responsible else 'Phụ trách'
            deadline = template_activity._get_date_deadline(schedule_wizard.plan_date)
            deadline_str = deadline.strftime('%d/%m/%Y') if deadline else 'Chưa rõ'

            checklist_html += f"""
                <tr style="border-bottom: 1px solid #f1f1f1;">
                    <td style="padding: 15px 10px; color: #333333; font-size: 14px; vertical-align: middle;">{task_name}</td>
                    <td style="padding: 15px 10px; color: #777777; font-size: 14px; vertical-align: middle; text-align: center;">{resp_name}</td>
                    <td style="padding: 15px 10px; color: #DA291C; font-weight: bold; font-size: 14px; vertical-align: middle; text-align: right;">{deadline_str}</td>
                </tr>
            """

        # === VSATTP: Tự tạo survey invite và lấy link ===
        survey_url = False
        if self.x_psm_0211_vsattp_survey_id:
            try:
                email_to = self.work_email or self.private_email or (self.work_contact_id.email if self.work_contact_id else '')
                # Tìm partner email
                partner = self.work_contact_id
                if not partner:
                    partner = self.env['res.partner'].sudo().search([('email', '=', email_to)], limit=1)
                
                # Tạo survey.user_input (invite) cho nhân viên
                survey_input = self.env['survey.user_input'].sudo().create({
                    'survey_id': self.x_psm_0211_vsattp_survey_id.id,
                    'partner_id': partner.id if partner else False,
                    'email': email_to,
                    'deadline': schedule_wizard.plan_date if schedule_wizard.plan_date else False,
                })
                survey_url = survey_input.get_start_url()
                
                # Tạo activity nhắc HR check kết quả
                self.activity_schedule(
                    'mail.mail_activity_data_todo',
                    summary='Theo dõi kết quả Khảo sát VSATTP',
                    note=f'Vui lòng theo dõi xem nhân viên đã hoàn thành Bài khảo sát "{self.x_psm_0211_vsattp_survey_id.display_name}" hay chưa, '
                         f'và đánh dấu "Ứng viên đã làm bài" ở Tab Hồ sơ nhân viên.'
                )
            except Exception as e:
                self.message_post(body=markup(f"Không thể tạo link VSATTP tự động: {str(e)}"))

        # Gửi email qua template
        template.with_context(
            plan_date=schedule_wizard.plan_date.strftime('%d/%m/%Y') if schedule_wizard.plan_date else 'Đang cập nhật',
            vsattp_url=survey_url,
            checklist_html=markup(checklist_html),
        ).send_mail(self.id, force_send=True)

        self.message_post(body=markup(f"Welcome email + Onboarding plan sent" + 
                          (f" + Food Safety link" if self.x_psm_0211_vsattp_survey_id else "") +
                          f" to applicant."))


    def x_psm_0211_send_3P_notification_email(self, schedule_wizard):
        """ Gửi email thông báo cho Adecco (Agency) """
        self.ensure_one()
        x_psm_0211_3P_email = schedule_wizard.x_psm_0211_3P_email
        if not x_psm_0211_3P_email:
            return

        template = self.env.ref('M02_P0211.email_template_adecco_notification', raise_if_not_found=False)
        if not template:
            _logger.warning("Không tìm thấy email template 'email_template_adecco_notification'")
            return
        
        # Gửi email qua template - Đảm bảo CHỈ gửi tới Adecco, không gửi cho nhân viên/followers
        template.with_context(
            x_psm_0211_3P_email=x_psm_0211_3P_email,
            plan_date=schedule_wizard.plan_date.strftime('%d/%m/%Y') if schedule_wizard.plan_date else 'N/A',
        ).send_mail(self.id, force_send=True, email_values={
            'email_to': x_psm_0211_3P_email,
            'email_cc': False,
            'auto_delete': True,
            'partner_ids': [], # Ngăn Odoo tự thêm partner của record
            'recipient_ids': [], # Xóa bỏ mọi người nhận khác để không gửi cho nhân viên
        })

        self.message_post(body=markup(f"Adecco notification email sent: {x_psm_0211_3P_email}"))

    def action_psm_request_contract_signature(self):
        """Initiate signature flow, pre-fill data, and send custom invitation email."""
        self.ensure_one()
        
        if self.x_psm_0211_contract_sign_request_id and self.x_psm_0211_contract_sign_request_id.state not in ('canceled', 'expired', 'signed'):
            raise UserError("A signature request is already active for this employee.")
            
        template = self.env.ref('M02_P0211.sign_template_contract', raise_if_not_found=False)
        if not template:
            raise UserError("Contract Sign Template not found. Please upgrade the module.")
            
        partner = self.user_partner_id or self.work_contact_id
        if not partner:
             raise UserError("Employee contact information (Partner) is missing. Cannot proceed.")

        # --- DYNAMIC PRE-FILLING --- 
        # Find Sign Items assigned to employee on the template
        name_item = self.env.ref('M02_P0211.sign_item_employee_name', raise_if_not_found=False)
        date_item = self.env.ref('M02_P0211.sign_item_employee_date', raise_if_not_found=False)
        # Use our local role for onboarding
        role_employee = self.env.ref('M02_P0211.sign_item_role_employee_onboarding', raise_if_not_found=False)
        if not role_employee:
             role_employee = self.env.ref('sign.sign_item_role_default')

        from odoo import Command
        sign_request = self.env['sign.request'].sudo().with_context(no_mail=True).create({
            'template_id': template.id,
            'request_item_ids': [Command.create({
                'partner_id': partner.id,
                'role_id': role_employee.id,
                'mail_sent_order': 1,
            })],
            'reference': f"Employment Contract - {self.name}",
            'subject': f"Employment Contract - {self.name}",
            'reference_doc': f"{self._name},{self.id}",
        })
        
        self.x_psm_0211_contract_sign_request_id = sign_request.id
        # --- DYNAMIC PRE-FILLING (IMPROVED) --- 
        # Find item types to ensure matching
        name_item = self.env.ref('M02_P0211.sign_item_employee_name_signature', raise_if_not_found=False)
        company_item = self.env.ref('M02_P0211.sign_item_company_name', raise_if_not_found=False)
        
        # Any items on this request? (Assuming 1 signer flow)
        for req_item in sign_request.request_item_ids:
            # Pre-fill ALL matched placeholders regardless of role (Safest for single-signer automation)
            if company_item:
                 self.env['sign.request.item.value'].sudo().create({
                     'sign_request_item_id': req_item.id,
                     'sign_item_id': company_item.id,
                     'value': self.company_id.name or "Company Name"
                 })
            if name_item:
                 self.env['sign.request.item.value'].sudo().create({
                     'sign_request_item_id': req_item.id,
                     'sign_item_id': name_item.id,
                     'value': self.name
                 })
        
        # --- SEND CUSTOM PORTAL NOTIFICATION ---
        mail_template = self.env.ref('M02_P0211.email_template_contract_invitation', raise_if_not_found=False)
        if mail_template:
            mail_template.send_mail(self.id, force_send=True)
            self.message_post(body=f"✉️ Contract signature invitation sent with pre-filled Company: {self.company_id.name} and Employee: {self.name}.")
        else:
            self.message_post(body=f"⚠️ Sign request created (ID: {sign_request.id}), but notification email failed.")

        return True

    def action_psm_portal_confirm_contract(self):
        """Finalize signature from Portal (Simple confirmation).
        Clean x_psm_0211_code: can be extended for Canvas signature later.
        """
        self.ensure_one()
        # Sync state with sign module if it's currently managed by it
        if self.x_psm_0211_contract_sign_request_id:
            self.x_psm_0211_contract_sign_request_id.sudo().write({'state': 'signed'})
        
        # Log to chatter
        self.message_post(body="🖋️ Contract has been officially confirmed and signed by the Employee via Portal.")
        return True



class HrEmployeePublic(models.Model):
    _inherit = 'hr.employee.public'

    x_psm_0211_can_evaluate_probation = fields.Boolean(
        string='Can Evaluate Probation', 
        compute='x_psm_0211_compute_can_evaluate_probation',
        groups="base.group_user"
    )
    x_psm_0211_is_rst_employee_onb = fields.Boolean(related='employee_id.x_psm_0211_is_rst_employee_onb')
    x_psm_0211_onboarding_state = fields.Selection(related='employee_id.x_psm_0211_onboarding_state')
    x_psm_0211_training_started = fields.Boolean(related='employee_id.x_psm_0211_training_started')
    x_psm_0211_onboarding_ops_rst_training_process = fields.Float(related='employee_id.x_psm_0211_onboarding_ops_rst_training_process')
    x_psm_0211_staff_type = fields.Selection(related='employee_id.x_psm_0211_staff_type')

    @api.depends_context('uid')
    def x_psm_0211_compute_can_evaluate_probation(self):
        # Re-use logic from hr.employee
        HrEmployee.x_psm_0211_compute_can_evaluate_logic(self)

    def action_psm_open_probation_wizard(self):
        # Delegate to the main employee record
        self.ensure_one()
        return self.employee_id.action_psm_open_probation_wizard()
