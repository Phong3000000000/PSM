# -*- coding: utf-8 -*-
from odoo import models, fields, api


class WorkforceForecast(models.Model):
    """
    Model lưu trữ dữ liệu dự báo VLH (Sales, Guest Count)
    Import từ file Excel hàng tuần
    """
    _name = 'workforce.forecast'
    _description = 'VLH Forecast Data'
    _order = 'date, hour'

    name = fields.Char(
        string='Mã',
        compute='_compute_name',
        store=True
    )
    date = fields.Date(
        string='Ngày',
        required=True,
        index=True
    )
    hour = fields.Float(
        string='Khung giờ',
        required=True,
        help='Giờ trong ngày (0-23), VD: 12.0 = 12:00, 12.5 = 12:30'
    )
    
    # Dữ liệu từ VLH
    projected_sales = fields.Float(
        string='Doanh thu dự kiến',
        help='Doanh thu dự kiến tại khung giờ này'
    )
    projected_gc = fields.Float(
        string='Guest Count',
        help='Số lượng khách dự kiến'
    )
    trend_factor = fields.Float(
        string='Trend Factor',
        default=1.0,
        help='Hệ số điều chỉnh theo xu hướng'
    )
    
    # Config
    target_gcpch = fields.Float(
        string='Target GCPCH',
        default=10.0,
        help='Guest Count Per Crew Hour - Số khách mỗi nhân viên phục vụ được 1 giờ'
    )
    
    # Computed
    staff_needed = fields.Float(
        string='Số nhân sự cần',
        compute='_compute_staff_needed',
        store=True,
        help='Tính toán: projected_gc / target_gcpch * trend_factor'
    )
    
    period_id = fields.Many2one(
        'planning.period',
        string='Kỳ đăng ký',
        ondelete='cascade'
    )
    
    @api.depends('date', 'hour')
    def _compute_name(self):
        for rec in self:
            if rec.date and rec.hour:
                hour_str = '%02d:%02d' % (int(rec.hour), int((rec.hour % 1) * 60))
                rec.name = '%s %s' % (rec.date.strftime('%d/%m'), hour_str)
            else:
                rec.name = 'Draft'
    
    @api.depends('projected_gc', 'target_gcpch', 'trend_factor')
    def _compute_staff_needed(self):
        for rec in self:
            if rec.target_gcpch and rec.target_gcpch > 0:
                rec.staff_needed = (rec.projected_gc / rec.target_gcpch) * rec.trend_factor
            else:
                rec.staff_needed = 0
    
    _sql_constraints = [
        (
            'date_hour_unique',
            'UNIQUE(date, hour)',
            'Đã tồn tại dữ liệu forecast cho ngày và khung giờ này!'
        ),
    ]

