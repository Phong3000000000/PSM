from odoo import models, fields, api
from odoo.exceptions import UserError
class ApprovalRequest(models.Model):
    _inherit = 'approval.request'

    # Thông tin cá nhân mới
    # new_name / new_phone -> Removed. Use legal_name / private_phone.
    
    # Private Info
    sex = fields.Selection([
        ('male', 'Male'),
        ('female', 'Female'),
        ('other', 'Other')
    ], string='Giới tính')
    birthday = fields.Date(string='Ngày sinh')
    country_id = fields.Many2one('res.country', string='Quốc tịch')
    # identification_id = fields.Char(string='Số CCCD') -> Computed
    identification_id = fields.Char(
        string='Số CCCD',
        compute="_compute_employee_info",
        store=True,
        readonly=False,
    )
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

    @api.depends('request_owner_id', 'partner_id')
    def _compute_employee_id(self):
        for request in self:
            employee = False
            # 1. Ưu tiên partner_id
            if request.partner_id:
                employee = self.env['hr.employee'].search([
                    ('work_contact_id', '=', request.partner_id.id),
                    ('company_id', '=', request.company_id.id),
                ], limit=1)
            
            # 2. Fallback request_owner_id
            if not employee and request.request_owner_id:
                employee = self.env['hr.employee'].search([
                    ('user_id', '=', request.request_owner_id.id),
                    ('company_id', '=', request.company_id.id),
                ], limit=1)
            
            request.employee_id = employee

    @api.depends('employee_id')
    def _compute_employee_info(self):
        for request in self:
            if request.employee_id:
                # Only set if empty to avoid overwriting user input?
                # Actually, standard Odoo compute with store=True and readonly=False:
                # The compute triggers when dependencies change. If employee_id changes (e.g. at creation), it sets the value.
                # If user writes to it manually, it stays (unless dependency changes again).
                # Since employee_id likely set once at create, this acts as pre-fill.
                request.legal_name = request.employee_id.legal_name or request.employee_id.name
                request.private_phone = request.employee_id.private_phone or request.employee_id.mobile_phone
                request.identification_id = request.employee_id.identification_id
            else:
                # If no employee, no auto-fill. Don't force False if user typed something?
                # But if logic is strict sync... 
                # For now, replicate 201 logic exactly.
                if not request.legal_name: request.legal_name = False
                if not request.private_phone: request.private_phone = False
                if not request.identification_id: request.identification_id = False

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
    employee_distance_home_work_unit = fields.Selection(related='employee_id.distance_home_work_unit', string="Current Distance Unit", readonly=True)
    employee_bank_account_ids = fields.Many2many(related='employee_id.bank_account_ids', string="Current Bank Accounts", readonly=True)
    


    # --- Expanded Personal Info Fields ---
    # 1. Private Contact
    private_email = fields.Char(string='Private Email')
    # private_phone = fields.Char(string='Private Phone') -> Computed
    private_phone = fields.Char(
        string='Private Phone',
        compute="_compute_employee_info",
        store=True,
        readonly=False,
    )
    # legal_name = fields.Char(string='Legal Name') -> Computed
    legal_name = fields.Char(
        string='Legal Name',
        compute="_compute_employee_info",
        store=True,
        readonly=False,
    )

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
    distance_home_work_unit = fields.Selection([
        ('kilometers', 'km'),
        ('miles', 'mi')
    ], string='Đơn vị khoảng cách', default='kilometers')
    
    # 6. Bank Account (Info only)
    acc_number = fields.Char(string='Số tài khoản')
    bank_id = fields.Many2one('res.bank', string='Ngân hàng')
    
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
    
    # Change history
    change_history_ids = fields.One2many(
        'hr.employee.change.history',
        'approval_request_id',
        string='Change History',
        readonly=True
    )

    # Computed HTML summary of changes (new vs current employee values)
    changes_summary_html = fields.Html(
        string='Tổng hợp thay đổi',
        compute='_compute_changes_summary_html',
        sanitize=False,
    )

    def _compute_changes_summary_html(self):
        for request in self:
            changes = request.get_changes_summary()
            if not changes:
                request.changes_summary_html = (
                    '<div class="alert alert-info" role="alert">'
                    '<i class="fa fa-info-circle me-1"/> Không có thông tin nào thay đổi so với hiện tại.'
                    '</div>'
                )
                continue

            rows = ''
            for change in changes:
                rows += (
                    '<tr>'
                    '<td><strong>{label}</strong></td>'
                    '<td class="text-muted">{old}</td>'
                    '<td class="text-success fw-bold">{new}</td>'
                    '</tr>'
                ).format(
                    label=change.get('label', ''),
                    old=change.get('old', '---'),
                    new=change.get('new', '---'),
                )

            request.changes_summary_html = (
                '<table class="table table-sm table-bordered table-hover">'
                '<thead class="table-light">'
                '<tr>'
                '<th>Trường thông tin</th>'
                '<th>Giá trị hiện tại</th>'
                '<th>Giá trị đăng ký mới</th>'
                '</tr>'
                '</thead>'
                '<tbody>{rows}</tbody>'
                '</table>'
            ).format(rows=rows)

    def action_approve(self, approver=None):
        """
        Ghi đè hàm duyệt: Khi Admin bấm Approve, tự động cập nhật vào res.partner và hr.employee
        """
        res = super(ApprovalRequest, self).action_approve(approver=approver)
        # --- Changed Reference to new module ---
        category_id = self.env.ref('M02_P0203_00.approval_category_contact_update', raise_if_not_found=False)
        for request in self:
            if category_id and request.category_id == category_id and request.partner_id:
                # 1. Update Partner
                partner_vals = {}
                if request.legal_name: partner_vals['name'] = request.legal_name
                if request.private_phone: partner_vals['phone'] = request.private_phone
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
                    if request.passport_expiration_date: emp_vals['passport_expiration_date'] = request.passport_expiration_date
                    
                    if request.private_email: emp_vals['private_email'] = request.private_email
                    if request.private_phone: emp_vals['private_phone'] = request.private_phone
                    if request.legal_name: emp_vals['legal_name'] = request.legal_name
                    
                    # Birth
                    if request.place_of_birth: emp_vals['place_of_birth'] = request.place_of_birth
                    if request.country_of_birth: emp_vals['country_of_birth'] = request.country_of_birth.id

                    # Visa
                    if request.visa_no: emp_vals['visa_no'] = request.visa_no
                    if request.permit_no: emp_vals['permit_no'] = request.permit_no
                    if request.has_work_permit: emp_vals['has_work_permit'] = request.has_work_permit
                    if request.visa_expire: emp_vals['visa_expire'] = request.visa_expire
                    if request.work_permit_expiration_date: emp_vals['work_permit_expiration_date'] = request.work_permit_expiration_date

                    # Citizenship Extra
                    if request.ssnid: emp_vals['ssnid'] = request.ssnid

                    # Address
                    if request.private_street: emp_vals['private_street'] = request.private_street
                    if request.private_street2: emp_vals['private_street2'] = request.private_street2
                    if request.private_city: emp_vals['private_city'] = request.private_city
                    if request.private_state_id: emp_vals['private_state_id'] = request.private_state_id.id
                    if request.private_zip: emp_vals['private_zip'] = request.private_zip
                    if request.private_country_id: emp_vals['private_country_id'] = request.private_country_id.id
                    if request.distance_home_work: emp_vals['distance_home_work'] = request.distance_home_work
                    if request.distance_home_work_unit: emp_vals['distance_home_work_unit'] = request.distance_home_work_unit
                    if request.acc_number and request.bank_id:
                        bank_acc = self.env['res.partner.bank'].sudo().search([
                            ('partner_id', '=', request.partner_id.id),
                            ('acc_number', '=', request.acc_number),
                            ('bank_id', '=', request.bank_id.id)
                        ], limit=1)
                        if not bank_acc:
                            bank_acc = self.env['res.partner.bank'].sudo().create({
                                'partner_id': request.partner_id.id,
                                'acc_number': request.acc_number,
                                'bank_id': request.bank_id.id,
                            })
                        emp_vals['bank_account_ids'] = [(6, 0, [bank_acc.id])]

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
                        # Tạo bản ghi lịch sử thay đổi (Lấy trước khi update để có old_value đúng)
                        changes = request.get_changes_summary()

                        employee.sudo().write(emp_vals)
                        
                        ChangeHistory = self.env['hr.employee.change.history'].sudo()
                        for change in changes:
                            ChangeHistory.create({
                                'employee_id': employee.id,
                                'approval_request_id': request.id,
                                'change_date': fields.Datetime.now(),
                                'changed_by_id': self.env.user.id,
                                'field_name': change['field'],
                                'field_label': change['label'],
                                'old_value': change['old'],
                                'new_value': change['new'],
                                'change_type': 'update',
                            })
                        
                        # Post message to employee chatter
                        if changes:
                            employee.message_post(
                                body=f"Thông tin được cập nhật từ yêu cầu phê duyệt: {request.name}",
                                subject="Cập nhật thông tin nhân viên"
                            )
                        

                        
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
        # --- Changed Reference to new module ---
        template = self.env.ref('M02_P0203_00.email_template_gov_update_done', raise_if_not_found=False)
        if template:
            template.send_mail(self.id, force_send=True)

    def _send_completion_email(self):
        """Gửi email khi hoàn tất"""
        self.ensure_one()
        # Chú ý: ID của template phải khớp với file XML bên dưới
        template = self.env.ref('M02_P0203_00.email_template_hr_update_done', raise_if_not_found=False)
        if template:
            template.send_mail(self.id, force_send=True)

    def get_changes_summary(self):
        """Trả về danh sách các thay đổi để hiển thị trên Portal"""
        self.ensure_one()
        changes = []
        # Mapping: (field_name, related_field_name, string_label)
        field_map = [
            ('legal_name', 'employee_legal_name', 'Tên hợp pháp'),
            ('private_phone', 'employee_private_phone', 'SĐT cá nhân'),
            ('private_email', 'employee_private_email', 'Email cá nhân'),
            ('sex', 'employee_sex', 'Giới tính'),
            ('birthday', 'employee_birthday', 'Ngày sinh'),
            ('place_of_birth', 'employee_place_of_birth', 'Nơi sinh'),
            ('country_of_birth', 'employee_country_of_birth', 'Quốc gia nơi sinh'),
            ('country_id', 'employee_country_id', 'Quốc tịch'),
            ('identification_id', 'employee_identification_id', 'CCCD/CMND'),
            ('passport_id', 'employee_passport_id', 'Hộ chiếu'),
            ('passport_expiration_date', 'employee_passport_expiration_date', 'Ngày hết hạn hộ chiếu'),
            ('visa_no', 'employee_visa_no', 'Số Visa'),
            ('visa_expire', 'employee_visa_expire', 'Hạn Visa'),
            ('permit_no', 'employee_permit_no', 'Giấy phép lao động'),
            ('work_permit_expiration_date', 'employee_work_permit_expiration_date', 'Hạn GPLĐ'),
            ('ssnid', 'employee_ssnid', 'BHXH'),
            ('private_street', 'employee_private_street', 'Đường (Riêng)'),
            ('private_street2', 'employee_private_street2', 'Đường 2 (Riêng)'),
            ('private_city', 'employee_private_city', 'Tỉnh/TP (Riêng)'),
            ('private_state_id', 'employee_private_state_id', 'Quận/Huyện (Riêng)'),
            ('private_zip', 'employee_private_zip', 'Mã bưu chính'),
            ('private_country_id', 'employee_private_country_id', 'Quốc gia (Riêng)'),
            ('distance_home_work', 'employee_distance_home_work', 'Khoảng cách đi làm'),
            ('marital', 'employee_marital', 'Hôn nhân'),
            ('children', 'employee_children', 'Số con'),
            ('spouse_complete_name', 'employee_spouse_complete_name', 'Họ tên vợ/chồng'),
            ('spouse_birthdate', 'employee_spouse_birthdate', 'Ngày sinh vợ/chồng'),
            ('acc_number', False, 'Số tài khoản'),
            ('bank_id', False, 'Ngân hàng'),
            ('distance_home_work_unit', 'employee_distance_home_work_unit', 'Đơn vị khoảng cách'),
            ('emergency_contact', 'employee_emergency_contact', 'Liên hệ khẩn cấp'),
            ('emergency_phone', 'employee_emergency_phone', 'SĐT khẩn cấp'),
            ('certificate', 'employee_certificate', 'Bằng cấp'),
            ('study_field', 'employee_study_field', 'Chuyên ngành'),
            ('study_school', 'employee_study_school', 'Trường học'),
        ]

        for field, old_field, label in field_map:
            # Check if main field exists
            if field not in self._fields:
                continue
                
            val_new = self[field]
            
            # Handle old_field lookup
            val_old = False
            if old_field:
                 if old_field in self._fields:
                     val_old = self[old_field]
                 else:
                     # old_field name specified but not in fields? skip or treat as False
                     pass
            
            # Chỉ hiện nếu có giá trị mới và khác giá trị cũ
            try:
                # Compare
                if val_new != val_old:
                    # Format
                    display_old = self._format_change_value(old_field, val_old) if old_field else '---'
                    display_new = self._format_change_value(field, val_new)
                    # Chỉ thêm vào changes nếu giá trị hiển thị thực sự khác nhau
                    if display_old != display_new:
                        changes.append({
                            'field': field,
                            'label': label,
                            'old': display_old,
                            'new': display_new
                        })
            except Exception:
                continue
        return changes

    def _format_change_value(self, field_name, value):
        if not value: return '---'
        f = self._fields[field_name]
        try:
            if f.type == 'selection':
                sel = f.selection
                if isinstance(sel, list):
                    return dict(sel).get(value, value)
                # Fallback for callable selection (unlikely here but safe)
                return value
            if f.type == 'many2one':
                return value.display_name
            if f.type == 'date':
                return value.strftime('%d/%m/%Y')
            if f.type == 'datetime':
                return value.strftime('%d/%m/%Y %H:%M')
            if f.type == 'many2many':
                return ", ".join(value.mapped('display_name'))
        except:
            return str(value)
        return str(value)
