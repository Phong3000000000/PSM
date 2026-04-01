# -*- coding: utf-8 -*-
from odoo import models, fields, api, exceptions
import json
import logging

_logger = logging.getLogger(__name__)

class JobApplicationField(models.Model):
    _name = 'job.application.field'
    _description = 'Cấu hình trường biểu mẫu ứng tuyển'
    _order = 'sequence, id'

    job_id = fields.Many2one('hr.job', string='Vị trí tuyển dụng', ondelete='cascade', required=True)
    sequence = fields.Integer('Thứ tự', default=10)
    is_active = fields.Boolean('Sử dụng', default=True)
    is_required = fields.Boolean('Bắt buộc', default=True)
    
    field_name = fields.Char('Tên trường (Technical)', required=True, 
                             help="Tên trường trong model hr.applicant hoặc property name")
    field_label = fields.Char('Nhãn hiển thị', required=True, translate=True)
    
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

    is_default = fields.Boolean('Trường mặc định', default=False, readonly=True)
    is_core_required_field = fields.Boolean(
        string='Là trường cốt lõi',
        compute='_compute_is_core_required_field',
        store=False
    )
    col_size = fields.Selection([
        ('6', 'Nửa hàng (1/2)'),
        ('12', 'Full hàng (1/1)'),
    ], string='Độ rộng', default='6', required=True)

    # ===== Master link =====
    master_field_id = fields.Many2one(
        'recruitment.application.field.master',
        string='Master Source',
        ondelete='set null',
        readonly=True,
        help='Trường master nguồn. Nếu có, dòng này được quản lý từ master.'
    )
    is_from_master = fields.Boolean(
        'Từ Master', default=False, readonly=True,
        help='True nếu dòng này được sinh ra từ cấu hình master.'
    )

    # ===== Answer matching (Phải đúng) =====
    is_answer_must_match = fields.Boolean(
        'Phải đúng', default=False,
        help='Ứng viên phải trả lời đúng đáp án mong đợi. Chỉ áp dụng cho select, radio, checkbox.'
    )
    expected_answer = fields.Char(
        'Đáp án phải đúng (Technical)',
        help='Giá trị (value) kỹ thuật mà ứng viên phải chọn. Với checkbox: "yes" hoặc "no". Được tự động cập nhật từ UI.'
    )

    # ===== UI Bridge Fields cho "Phải đúng" =====
    expected_answer_option_id = fields.Many2one(
        'job.application.field.option',
        string='Đáp án phải đúng',
        compute='_compute_expected_answer_option_id',
        inverse='_inverse_expected_answer_option_id',
        domain="[('field_id', '=', id)]",
        help='Chọn đáp án phải đúng từ danh sách lựa chọn (cho select/radio).'
    )
    expected_answer_checkbox = fields.Selection(
        [('yes', 'Có'), ('no', 'Không')],
        string='Đáp án phải đúng',
        compute='_compute_expected_answer_checkbox',
        inverse='_inverse_expected_answer_checkbox',
        help='Chọn đáp án phải đúng cho checkbox.'
    )

    selection_options = fields.Text('Lựa chọn (JSON)', 
                                   help='Dạng: [{"value": "v1", "label": "L1"}, {"value": "v2", "label": "L2"}]')
    
    option_ids = fields.One2many('job.application.field.option', 'field_id', string='Lựa chọn', copy=True)

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
            self.is_answer_must_match = False
            self.expected_answer = ''
            self.expected_answer_option_id = False
            self.expected_answer_checkbox = False
        elif self.field_type == 'checkbox':
            self.expected_answer_option_id = False
        else:
            self.expected_answer_checkbox = False

    # ===== Onchange: reset expected_answer khi tắt phải đúng =====
    @api.onchange('is_answer_must_match')
    def _onchange_is_answer_must_match(self):
        if not self.is_answer_must_match:
            self.expected_answer = ''
            self.expected_answer_option_id = False
            self.expected_answer_checkbox = False

    # ===== Constrains: validate expected_answer =====
    @api.constrains('expected_answer', 'is_answer_must_match', 'field_type', 'option_ids')
    def _check_expected_answer_valid(self):
        for rec in self:
            if not rec.is_answer_must_match or not rec.expected_answer:
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

    @api.depends('field_name')
    def _compute_is_core_required_field(self):
        for rec in self:
            rec.is_core_required_field = rec.field_name in ('partner_name', 'email_from', 'attachment')

    @api.constrains('field_name', 'job_id')
    def _check_unique_field_name(self):
        for rec in self:
            count = self.search_count([('job_id', '=', rec.job_id.id), ('field_name', '=', rec.field_name)])
            if count > 1:
                raise exceptions.ValidationError(f"Tên trường (Technical) '{rec.field_name}' bị trùng lặp trong cùng vị trí tuyển dụng này!")

    @api.constrains('section', 'is_default', 'is_from_master')
    def _check_custom_field_section(self):
        for rec in self:
            # Dòng master hoặc default được phép nằm ở bất kỳ section nào
            if not rec.is_default and not rec.is_from_master and rec.section not in ['supplementary_question', 'internal_question']:
                raise exceptions.ValidationError("Trường tự tạo (Custom) chỉ được phép nằm trong nhóm 'Câu hỏi bổ sung' hoặc 'Câu hỏi nội bộ'!")

    def get_selection_list(self):
        """Trả về list các dict lựa chọn từ option_ids (ưu tiên) hoặc JSON string."""
        if self.option_ids:
            return [{'value': opt.value, 'label': opt.name} for opt in self.option_ids.sorted('sequence')]
        
        if not self.selection_options:
            return []
        try:
            return json.loads(self.selection_options)
        except Exception:
            return []

    @api.onchange('field_label')
    def _onchange_field_label(self):
        if self.field_label and not self.field_name:
            self.field_name = self._slugify(self.field_label)

    def _slugify(self, text):
        if not text:
            return ''
        import re
        
        # Chuyển tiếng Việt có dấu thành không dấu
        s1 = u'ÀÁÂÃÈÉÊÌÍÒÓÔÕÙÚÝàáâãèéêìíòóôõùúýĂăĐđĨĩŨũƠơƯưẠạẢảẤấẦầẨẩẪẫẬậẮắẰằẲẳẴẵẶặẸẹẺẻẼẽẾếỀềỂểỄễỆệỈỉỊịỌọỎỏỐốỒồỔổỖỗỘộỚớỜờỞởỠỡỢợỤụỦủỨứỪừỬửỮữỰựỲỳỴỵỶỷỸỹ'
        s0 = u'AAAAEEEIIOOOOUUYaaaaeeeiiiiiouuAaDdIiUuOoUuAaAaAaAaAaAaAaAaAaAaAaAaEeEeEeEeEeEeEeEeIiIiOoOoOoOoOoOoOoOoOoOoOoOoUuUuUuUuUuUuUuYyYyYyYy'
        s = ''
        for c in text:
            if c in s1:
                s += s0[s1.index(c)]
            else:
                s += c
        
        # Chuyển về chữ thường
        s = s.lower()
        # Thay thế ký tự không phải chữ cái/số bằng _
        s = re.sub(r'[^a-z0-9]+', '_', s)
        # Loại bỏ _ ở đầu và cuối
        s = s.strip('_')
        return s

    @api.model_create_multi
    def create(self, vals_list):
        """Khi tạo trường custom, cập nhật lại Properties Definition"""
        res = super().create(vals_list)
        jobs_to_update = res.filtered(lambda r: not r.is_default).mapped('job_id')
        for job in jobs_to_update:
            self._rebuild_job_properties_definition(job)
        return res

    def write(self, vals):
        # Cho phép bypass protection khi reload từ master (context key)
        bypass_protection = self.env.context.get('master_reload', False)

        for rec in self:
            if rec.is_core_required_field and not bypass_protection:
                if 'is_active' in vals and vals['is_active'] is False:
                    raise exceptions.UserError("Không thể tắt trạng thái 'Sử dụng' của trường cốt lõi (Tên, Email, CV)!")
                if 'is_required' in vals and vals['is_required'] is False:
                    raise exceptions.UserError("Không thể tắt trạng thái 'Bắt buộc' của trường cốt lõi (Tên, Email, CV)!")

        # Validate modifications on default/master fields (chỉ khi KHÔNG phải reload từ master)
        if not bypass_protection:
            protected_fields = {'field_name', 'field_type', 'field_label', 'section', 'sequence', 'selection_options', 'option_ids'}
            if any(f in vals for f in protected_fields):
                for rec in self:
                    if rec.is_default or rec.is_from_master:
                        raise exceptions.UserError(
                            "Không được phép sửa đổi cấu trúc (Tên, Loại, Nhãn, Phân nhóm, Thứ tự, Lựa chọn) "
                            "của các trường mặc định/master! Chỉ có thể đổi trạng thái 'Sử dụng', 'Bắt buộc' và 'Phải đúng'. "
                            "Nếu cần thay đổi cấu trúc, hãy sửa trong Configuration > Default Application Fields rồi load lại."
                        )

        res = super().write(vals)
        # Update properties definition if any custom field changed
        jobs_to_update = self.filtered(lambda r: not r.is_default and not r.is_from_master).mapped('job_id')
        for job in jobs_to_update:
            self._rebuild_job_properties_definition(job)
        return res

    def unlink(self):
        jobs_to_update = self.filtered(lambda r: not r.is_default).mapped('job_id')
        res = super().unlink()
        for job in jobs_to_update:
            self._rebuild_job_properties_definition(job)
        return res

    @api.model
    def _rebuild_job_properties_definition(self, job):
        """Thực thi update toàn bộ các custom fields của job thành properties definition."""
        if not job:
            return

        # Chỉ nạp những custom fields (is_default = False)
        custom_fields = self.search([
            ('job_id', '=', job.id),
            ('is_default', '=', False)
        ], order='sequence, id')

        prop_type_map = {
            'text': 'char',
            'textarea': 'text',
            'email': 'char',
            'tel': 'char',
            'date': 'date',
            'select': 'selection',
            'radio': 'selection',
            'checkbox': 'boolean',
            'number': 'integer',
            'file': 'char',
        }

        current_definition = []
        for cf in custom_fields:
            prop_type = prop_type_map.get(cf.field_type, 'char')
            prop_vals = {
                'name': cf.field_name,
                'string': cf.field_label,
                'type': prop_type,
            }
            if prop_type == 'selection':
                opts = cf.get_selection_list()
                prop_vals['selection'] = [[opt['value'], opt['label']] for opt in opts]
            
            current_definition.append(prop_vals)

        job.sudo().write({'applicant_properties_definition': current_definition})

class JobApplicationFieldOption(models.Model):
    _name = 'job.application.field.option'
    _description = 'Lựa chọn của trường biểu mẫu'
    _order = 'sequence, id'

    field_id = fields.Many2one('job.application.field', string='Trường biểu mẫu', ondelete='cascade', required=True)
    sequence = fields.Integer('Thứ tự', default=10)
    value = fields.Char('Giá trị (Technical)', required=True)
    name = fields.Char('Nhãn hiển thị', required=True, translate=True)

    @api.onchange('name')
    def _onchange_name(self):
        if self.name and not self.value:
            # Re-use slugify logic or similar
            self.value = self.field_id._slugify(self.name)

    def unlink(self):
        """Reset expected_answer nếu option đang được chọn làm đáp án phải đúng."""
        for opt in self:
            field = opt.field_id
            if field.expected_answer == opt.value:
                field.write({'expected_answer': ''})
        return super().unlink()

    def write(self, vals):
        """Reset expected_answer nếu value của option đang được chọn bị sửa."""
        if 'value' in vals:
            for opt in self:
                field = opt.field_id
                if field.expected_answer == opt.value and vals['value'] != opt.value:
                    field.write({'expected_answer': ''})
        return super().write(vals)
