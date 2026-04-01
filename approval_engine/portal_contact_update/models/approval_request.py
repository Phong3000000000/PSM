from odoo import models, fields, api
from odoo.exceptions import UserError
class ApprovalRequest(models.Model):
    _inherit = 'approval.request'

    # Thông tin cá nhân mới
    new_name = fields.Char(string='Họ tên mới')
    new_phone = fields.Char(string='Số điện thoại mới')
    
    # Private Info
    sex = fields.Selection([
        ('male', 'Male'),
        ('female', 'Female'),
        ('other', 'Other')
    ], string='Giới tính')
    birthday = fields.Date(string='Ngày sinh')
    country_id = fields.Many2one('res.country', string='Quốc tịch')
    identification_id = fields.Char(string='Số CCCD')
    passport_id = fields.Char(string='Số Hộ chiếu')
    
    # Marital & Family
    marital = fields.Selection([
        ('single', 'Single'),
        ('married', 'Married'),
        ('cohabitant', 'Legal Cohabitant'),
        ('widower', 'Widower'),
        ('divorced', 'Divorced')
    ], string='Tình trạng hôn nhân')
    children = fields.Integer(string='Số con')
    
    # Emergency
    emergency_contact = fields.Char(string='Liên hệ khẩn cấp')
    emergency_phone = fields.Char(string='SĐT khẩn cấp')
    
    # Education
    certificate = fields.Selection([
        ('graduate', 'Graduate'),
        ('bachelor', 'Bachelor'),
        ('master', 'Master'),
        ('doctor', 'Doctor'),
        ('other', 'Other'),
    ], string='Bằng cấp cao nhất')
    study_field = fields.Char(string='Chuyên ngành')
    study_school = fields.Char(string='Trường')

    # Tài liệu đính kèm (Lưu dưới dạng Binary để dễ review trên form approval)
    passport_photo = fields.Binary(string='Ảnh Hộ chiếu', attachment=True)
    id_card_front = fields.Binary(string='Mặt trước CCCD', attachment=True)
    

    # --- Linked Employee for Comparison ---
    employee_id = fields.Many2one('hr.employee', string='Employee Linked', compute='_compute_employee_id', store=True)

    @api.depends('partner_id')
    def _compute_employee_id(self):
        for request in self:
            employee = self.env['hr.employee'].search([('work_contact_id', '=', request.partner_id.id)], limit=1)
            request.employee_id = employee.id if employee else False

    # --- Related Fields for "Original Content" Tab (Readonly) ---
    employee_private_email = fields.Char(related='employee_id.private_email', string="Current Private Email", readonly=True)
    employee_private_phone = fields.Char(related='employee_id.private_phone', string="Current Private Phone", readonly=True)
    employee_legal_name = fields.Char(related='employee_id.legal_name', string="Current Legal Name", readonly=True)
    
    employee_sex = fields.Selection(related='employee_id.sex', string="Current Gender", readonly=True)
    employee_birthday = fields.Date(related='employee_id.birthday', string="Current Birthday", readonly=True)
    employee_place_of_birth = fields.Char(related='employee_id.place_of_birth', string="Current Place of Birth", readonly=True)
    employee_country_of_birth = fields.Many2one(related='employee_id.country_of_birth', string="Current Country of Birth", readonly=True)
    
    employee_country_id = fields.Many2one(related='employee_id.country_id', string="Current Nationality", readonly=True)
    employee_identification_id = fields.Char(related='employee_id.identification_id', string="Current Identification No", readonly=True)
    employee_passport_id = fields.Char(related='employee_id.passport_id', string="Current Passport No", readonly=True)
    employee_ssnid = fields.Char(related='employee_id.ssnid', string="Current SSN", readonly=True)
    employee_passport_expiration_date = fields.Date(related='employee_id.passport_expiration_date', string="Current Passport Expiration", readonly=True)
    
    employee_visa_no = fields.Char(related='employee_id.visa_no', string="Current Visa No", readonly=True)
    employee_visa_expire = fields.Date(related='employee_id.visa_expire', string="Current Visa Expire", readonly=True)
    employee_permit_no = fields.Char(related='employee_id.permit_no', string="Current Work Permit No", readonly=True)
    employee_work_permit_expiration_date = fields.Date(related='employee_id.work_permit_expiration_date', string="Current Work Permit Expiration", readonly=True)
    
    employee_private_street = fields.Char(related='employee_id.private_street', string="Current Private Street", readonly=True)
    employee_private_street2 = fields.Char(related='employee_id.private_street2', string="Current Private Street 2", readonly=True)
    employee_private_city = fields.Char(related='employee_id.private_city', string="Current Private City", readonly=True)
    employee_private_state_id = fields.Many2one(related='employee_id.private_state_id', string="Current Private State", readonly=True)
    employee_private_zip = fields.Char(related='employee_id.private_zip', string="Current Private Zip", readonly=True)
    employee_private_country_id = fields.Many2one(related='employee_id.private_country_id', string="Current Private Country", readonly=True)
    employee_distance_home_work = fields.Integer(related='employee_id.distance_home_work', string="Current Distance", readonly=True)
    
    employee_marital = fields.Selection(related='employee_id.marital', string="Current Marital Status", readonly=True)
    employee_children = fields.Integer(related='employee_id.children', string="Current Children", readonly=True)
    employee_spouse_complete_name = fields.Char(related='employee_id.spouse_complete_name', string="Current Spouse Name", readonly=True)
    employee_spouse_birthdate = fields.Date(related='employee_id.spouse_birthdate', string="Current Spouse Birthday", readonly=True)
    
    employee_emergency_contact = fields.Char(related='employee_id.emergency_contact', string="Current Emergency Contact", readonly=True)
    employee_emergency_phone = fields.Char(related='employee_id.emergency_phone', string="Current Emergency Phone", readonly=True)
    
    employee_certificate = fields.Selection(related='employee_id.certificate', string="Current Certificate", readonly=True)
    employee_study_field = fields.Char(related='employee_id.study_field', string="Current Study Field", readonly=True)
    employee_study_school = fields.Char(related='employee_id.study_school', string="Current Study School", readonly=True)

    # --- Expanded Personal Info Fields ---
    # 1. Private Contact
    private_email = fields.Char(string='Private Email')
    private_phone = fields.Char(string='Private Phone')
    legal_name = fields.Char(string='Legal Name')

    # 2. Birth
    place_of_birth = fields.Char(string='Place of Birth')
    country_of_birth = fields.Many2one('res.country', string='Country of Birth')

    # 3. Visa & Work Permit
    visa_no = fields.Char(string='Visa No')
    visa_expire = fields.Date(string='Visa Expiration Date')
    permit_no = fields.Char(string='Work Permit No')
    work_permit_expiration_date = fields.Date(string='Work Permit Expiration Date')
    has_work_permit = fields.Binary(string='Work Permit Document', attachment=True)

    # 4. Citizenship
    ssnid = fields.Char(string='SSN No')
    passport_expiration_date = fields.Date(string='Passport Expiration Date')

    # 5. Address (Private)
    private_street = fields.Char(string='Private Street')
    private_street2 = fields.Char(string='Private Street2')
    private_city = fields.Char(string='Private City')
    private_state_id = fields.Many2one('res.country.state', string='Private State')
    private_zip = fields.Char(string='Private Zip')
    private_country_id = fields.Many2one('res.country', string='Private Country')
    distance_home_work = fields.Integer(string='Home-Work Distance')
    
    # 6. Family (Extras)
    spouse_complete_name = fields.Char(string='Spouse Complete Name')
    spouse_birthdate = fields.Date(string='Spouse Birthdate')
    is_government_updated = fields.Boolean(
        string='Đã cập nhật Web Dịch vụ công', 
        default=False, 
        tracking=True
    )
    # Helper field for view visibility
    category_name = fields.Char(related='category_id.name', string="Category Name", readonly=True, store=False)

    def action_approve(self):
        """
        Ghi đè hàm duyệt: Khi Admin bấm Approve, tự động cập nhật vào res.partner và hr.employee
        """
        res = super(ApprovalRequest, self).action_approve()
        category_id = self.env.ref('portal_contact_update.approval_category_contact_update', raise_if_not_found=False)
        for request in self:
            if category_id and request.category_id == category_id and request.partner_id:
                # 1. Update Partner
                partner_vals = {}
                if request.new_name: partner_vals['name'] = request.new_name
                if request.new_phone: partner_vals['phone'] = request.new_phone
                if partner_vals:
                    request.partner_id.sudo().write(partner_vals)
                # 2. Update Employee (if exists)
                employee = self.env['hr.employee'].sudo().search([('work_contact_id', '=', request.partner_id.id)], limit=1)
                if employee:
                    emp_vals = {}
                    # Basic & Private Contact
                    if request.sex: emp_vals['sex'] = request.sex
                    if request.birthday: emp_vals['birthday'] = request.birthday
                    if request.country_id: emp_vals['country_id'] = request.country_id.id
                    if request.identification_id: emp_vals['identification_id'] = request.identification_id
                    if request.passport_id: emp_vals['passport_id'] = request.passport_id
                    
                    if request.private_email: emp_vals['private_email'] = request.private_email
                    if request.private_phone: emp_vals['private_phone'] = request.private_phone
                    if request.legal_name: emp_vals['legal_name'] = request.legal_name
                    
                    # Birth
                    if request.place_of_birth: emp_vals['place_of_birth'] = request.place_of_birth
                    if request.country_of_birth: emp_vals['country_of_birth'] = request.country_of_birth.id

                    # Visa
                    if request.visa_no: emp_vals['visa_no'] = request.visa_no
                    if request.visa_expire: emp_vals['visa_expire'] = request.visa_expire
                    if request.permit_no: emp_vals['permit_no'] = request.permit_no
                    if request.work_permit_expiration_date: emp_vals['work_permit_expiration_date'] = request.work_permit_expiration_date
                    if request.has_work_permit: emp_vals['has_work_permit'] = request.has_work_permit

                    # Citizenship Extra
                    if request.ssnid: emp_vals['ssnid'] = request.ssnid
                    if request.passport_expiration_date: emp_vals['passport_expiration_date'] = request.passport_expiration_date

                    # Address
                    if request.private_street: emp_vals['private_street'] = request.private_street
                    if request.private_street2: emp_vals['private_street2'] = request.private_street2
                    if request.private_city: emp_vals['private_city'] = request.private_city
                    if request.private_state_id: emp_vals['private_state_id'] = request.private_state_id.id
                    if request.private_zip: emp_vals['private_zip'] = request.private_zip
                    if request.private_country_id: emp_vals['private_country_id'] = request.private_country_id.id
                    if request.distance_home_work: emp_vals['distance_home_work'] = request.distance_home_work

                    # Marital & Family
                    if request.marital: emp_vals['marital'] = request.marital
                    if request.children: emp_vals['children'] = request.children
                    if request.spouse_complete_name: emp_vals['spouse_complete_name'] = request.spouse_complete_name
                    if request.spouse_birthdate: emp_vals['spouse_birthdate'] = request.spouse_birthdate
                    
                    # Emergency
                    if request.emergency_contact: emp_vals['emergency_contact'] = request.emergency_contact
                    if request.emergency_phone: emp_vals['emergency_phone'] = request.emergency_phone
                    
                    # Education
                    if request.certificate: emp_vals['certificate'] = request.certificate
                    if request.study_field: emp_vals['study_field'] = request.study_field
                    if request.study_school: emp_vals['study_school'] = request.study_school
                    
                    if emp_vals:
                        employee.sudo().write(emp_vals)
                        
        return res





    # --- HR PROCESSING STATUS ---
    hr_processing_status = fields.Selection([
        ('pending', 'Chưa xử lý'),
        ('processing', 'Đang thực hiện cập nhật'),
        ('done', 'Đã hoàn thành')
    ], string='Trạng thái xử lý HR', default='pending', tracking=True)

    def write(self, vals):
        if 'is_government_updated' in vals and not vals['is_government_updated']:
            for request in self:
                # Mà giá trị hiện tại đang là True rồi
                if request.is_government_updated:
                    raise UserError("Không thể bỏ chọn trạng thái 'Đã cập nhật Web Dịch vụ công' khi đã xác nhận!")
        
        # 1. Logic cũ: Kiểm tra trạng thái xử lý HR (hr_processing_status)
        if 'hr_processing_status' in vals and vals['hr_processing_status'] == 'done':
            for request in self:
                if request.hr_processing_status != 'done':
                    request._send_completion_email()
        
        # 2. Logic MỚI: Kiểm tra trạng thái Dịch vụ công (is_government_updated)
        if 'is_government_updated' in vals and vals['is_government_updated']:
            for request in self:
                # Nếu trước đó chưa tick mà giờ tick thì mới gửi mail
                if not request.is_government_updated:
                    request._send_gov_update_email()
        return super(ApprovalRequest, self).write(vals)
    def _send_gov_update_email(self):
        """Gửi email thông báo cập nhật Dịch vụ công"""
        self.ensure_one()
        template = self.env.ref('portal_contact_update.email_template_gov_update_done', raise_if_not_found=False)
        if template:
            template.send_mail(self.id, force_send=True)

    def _send_completion_email(self):
        """Gửi email khi hoàn tất"""
        self.ensure_one()
        # Chú ý: ID của template phải khớp với file XML bên dưới
        template = self.env.ref('portal_contact_update.email_template_hr_update_done', raise_if_not_found=False)
        if template:
            template.send_mail(self.id, force_send=True)