# -*- coding: utf-8 -*-
from odoo import models, fields, api, exceptions


class RecruitmentApplicationFieldMaster(models.Model):
    _name = 'recruitment.application.field.master'
    _description = 'Cấu hình master trường biểu mẫu ứng tuyển'
    _order = 'section, sequence, id'

    active = fields.Boolean('Active', default=True)

    field_label = fields.Char('Nhãn hiển thị', required=True, translate=True)
    field_name = fields.Char(
        'Tên trường (Technical)', required=True,
        help="Tên trường trong model hr.applicant hoặc property name. Phải unique."
    )
    field_type = fields.Selection([
        ('text', 'Văn bản (Dòng đơn)'),
        ('textarea', 'Văn bản (Nhiều dòng)'),
        ('email', 'Email'),
        ('tel', 'Số điện thoại'),
        ('date', 'Ngày'),
        ('select', 'Danh sách thả xuống'),
        ('radio', 'Nút lựa chọn (Radio)'),
        ('checkbox', 'Ô đánh dấu (Checkbox)'),
        ('number', 'Số'),
        ('file', 'Tập tin kèm theo'),
    ], string='Loại trường', required=True, default='text')

    section = fields.Selection([
        ('basic_info', 'Thông tin cơ bản'),
        ('other_info', 'Các thông tin khác'),
        ('supplementary_question', 'Câu hỏi bổ sung'),
        ('internal_question', 'Câu hỏi nội bộ'),
    ], string='Phân nhóm', required=True, default='supplementary_question')

    sequence = fields.Integer('Thứ tự', default=10)

    col_size = fields.Selection([
        ('6', 'Nửa hàng (1/2)'),
        ('12', 'Full hàng (1/1)'),
    ], string='Độ rộng', default='6', required=True)

    is_active_default = fields.Boolean('Mặc định Bật', default=True,
                                       help='Khi load vào job, trường này sẽ được bật sử dụng hay không')
    is_required_default = fields.Boolean('Mặc định Bắt buộc', default=False,
                                         help='Khi load vào job, trường này sẽ được đánh dấu bắt buộc hay không')

    is_answer_must_match_default = fields.Boolean(
        'Mặc định Phải đúng', default=False,
        help='Khi load vào job, trường này sẽ được đánh dấu "phải trả lời đúng" hay không.'
             ' Chỉ áp dụng cho select, radio, checkbox.'
    )
    expected_answer = fields.Char(
        'Đáp án phải đúng (Technical)',
        help='Giá trị (value) kỹ thuật mà ứng viên phải chọn. '
             'Với checkbox: "yes" hoặc "no". Được tự động cập nhật từ UI.'
    )

    # ===== UI Bridge Fields cho "Phải đúng" =====
    expected_answer_option_id = fields.Many2one(
        'recruitment.application.field.master.option',
        string='Đáp án phải đúng',
        compute='_compute_expected_answer_option_id',
        inverse='_inverse_expected_answer_option_id',
        domain="[('master_field_id', '=', id)]",
        help='Chọn đáp án phải đúng từ danh sách lựa chọn (cho select/radio).'
    )
    expected_answer_checkbox = fields.Selection(
        [('yes', 'Có'), ('no', 'Không')],
        string='Đáp án phải đúng',
        compute='_compute_expected_answer_checkbox',
        inverse='_inverse_expected_answer_checkbox',
        help='Chọn đáp án phải đúng cho checkbox.'
    )

    recruitment_scope = fields.Selection([
        ('store', 'Khối Cửa Hàng'),
        ('office', 'Khối Văn Phòng'),
        ('both', 'Cả Hai'),
    ], string='Phạm vi áp dụng', default='both', required=True,
       help='Trường này chỉ được load cho job thuộc khối tương ứng, hoặc cả hai.')

    option_ids = fields.One2many(
        'recruitment.application.field.master.option', 'master_field_id',
        string='Lựa chọn', copy=True
    )

    _sql_constraints = [
        ('field_name_uniq', 'unique(field_name)', 'Tên trường (Technical) phải là duy nhất trong master!'),
    ]

    # ===== Compute / Inverse cho expected_answer_option_id =====
    @api.depends('expected_answer', 'option_ids', 'field_type')
    def _compute_expected_answer_option_id(self):
        for rec in self:
            if rec.field_type in ('select', 'radio') and rec.expected_answer:
                opt = rec.option_ids.filtered(
                    lambda o: o.value == rec.expected_answer
                )
                rec.expected_answer_option_id = opt[0] if opt else False
            else:
                rec.expected_answer_option_id = False

    def _inverse_expected_answer_option_id(self):
        for rec in self:
            if rec.expected_answer_option_id:
                rec.expected_answer = rec.expected_answer_option_id.value
            elif rec.field_type in ('select', 'radio'):
                rec.expected_answer = ''

    # ===== Compute / Inverse cho expected_answer_checkbox =====
    @api.depends('expected_answer', 'field_type')
    def _compute_expected_answer_checkbox(self):
        for rec in self:
            if rec.field_type == 'checkbox' and rec.expected_answer in ('yes', 'no'):
                rec.expected_answer_checkbox = rec.expected_answer
            else:
                rec.expected_answer_checkbox = False

    def _inverse_expected_answer_checkbox(self):
        for rec in self:
            if rec.expected_answer_checkbox:
                rec.expected_answer = rec.expected_answer_checkbox
            elif rec.field_type == 'checkbox':
                rec.expected_answer = ''

    # ===== Onchange: reset khi đổi field_type =====
    @api.onchange('field_type')
    def _onchange_field_type_reset_expected(self):
        if self.field_type not in ('select', 'radio', 'checkbox'):
            self.is_answer_must_match_default = False
            self.expected_answer = ''
            self.expected_answer_option_id = False
            self.expected_answer_checkbox = False
        elif self.field_type == 'checkbox':
            self.expected_answer_option_id = False
        else:
            self.expected_answer_checkbox = False

    # ===== Onchange: reset expected_answer khi tắt phải đúng =====
    @api.onchange('is_answer_must_match_default')
    def _onchange_is_answer_must_match_default(self):
        if not self.is_answer_must_match_default:
            self.expected_answer = ''
            self.expected_answer_option_id = False
            self.expected_answer_checkbox = False

    # ===== Constrains: validate expected_answer =====
    @api.constrains('expected_answer', 'is_answer_must_match_default', 'field_type', 'option_ids')
    def _check_expected_answer_valid(self):
        for rec in self:
            if not rec.is_answer_must_match_default or not rec.expected_answer:
                continue
            if rec.field_type in ('select', 'radio'):
                valid_values = rec.option_ids.mapped('value')
                if rec.expected_answer not in valid_values:
                    raise exceptions.ValidationError(
                        f"Đáp án phải đúng '{rec.expected_answer}' không nằm trong danh sách lựa chọn "
                        f"của trường '{rec.field_label}'. Vui lòng chọn lại từ danh sách."
                    )
            elif rec.field_type == 'checkbox':
                if rec.expected_answer not in ('yes', 'no'):
                    raise exceptions.ValidationError(
                        f"Đáp án phải đúng cho checkbox '{rec.field_label}' chỉ được là 'yes' hoặc 'no'."
                    )


class RecruitmentApplicationFieldMasterOption(models.Model):
    _name = 'recruitment.application.field.master.option'
    _description = 'Lựa chọn của trường master biểu mẫu'
    _order = 'sequence, id'

    master_field_id = fields.Many2one(
        'recruitment.application.field.master', string='Trường master',
        ondelete='cascade', required=True
    )
    sequence = fields.Integer('Thứ tự', default=10)
    value = fields.Char('Giá trị (Technical)', required=True)
    name = fields.Char('Nhãn hiển thị', required=True, translate=True)

    def unlink(self):
        """Reset expected_answer nếu option đang được chọn làm đáp án phải đúng."""
        for opt in self:
            master = opt.master_field_id
            if master.expected_answer == opt.value:
                master.write({'expected_answer': ''})
        return super().unlink()

    def write(self, vals):
        """Reset expected_answer nếu value của option đang được chọn bị sửa."""
        if 'value' in vals:
            for opt in self:
                master = opt.master_field_id
                if master.expected_answer == opt.value and vals['value'] != opt.value:
                    master.write({'expected_answer': ''})
        return super().write(vals)
