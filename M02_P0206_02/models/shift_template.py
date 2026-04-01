# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

class WorkforceShiftTemplate(models.Model):
    _name = 'workforce.shift.template'
    _description = 'Workforce Shift Template'
    _order = 'sequence, id'

    name = fields.Char(string='Tên ca', required=True)
    sequence = fields.Integer(string='Thứ tự', default=10)
    is_active = fields.Boolean(string='Đang hoạt động', default=True)
    
    start_hour = fields.Float(string='Giờ bắt đầu', required=True, help="Format: 6.5 means 06:30")
    end_hour = fields.Float(string='Giờ kết thúc', required=True, help="Format: 14.5 means 14:30")
    
    duration = fields.Float(string='Thời lượng (h)', compute='_compute_duration', store=True)
    
    # Optional: peak hour settings if we want to keep that logic, or just define peak shifts as separate templates
    is_peak = fields.Boolean(string='Là ca gãy (Peak)', default=False)
    
    store_id = fields.Many2one(
        'hr.department', 
        string='Cửa hàng (Áp dụng)',
        help='Nếu để trống, mẫu này áp dụng cho tất cả cửa hàng.'
    )

    @api.depends('start_hour', 'end_hour')
    def _compute_duration(self):
        for record in self:
            if record.end_hour >= record.start_hour:
                record.duration = record.end_hour - record.start_hour
            else:
                # Handle overnight shifts if necessary (e.g. 22:00 to 06:00)
                record.duration = (24 - record.start_hour) + record.end_hour

    @api.constrains('start_hour', 'end_hour')
    def _check_hours(self):
        for record in self:
            if record.start_hour < 0 or record.start_hour >= 24:
                raise ValidationError(_("Giờ bắt đầu phải từ 0 đến 24."))
            if record.end_hour < 0 or record.end_hour >= 24:
                raise ValidationError(_("Giờ kết thúc phải từ 0 đến 24."))
