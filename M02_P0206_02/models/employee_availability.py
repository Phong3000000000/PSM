# -*- coding: utf-8 -*-
from odoo import models, fields


class EmployeeAvailability(models.Model):
    """
    Lưu khung giờ rảnh/bận của nhân viên
    Dùng cho thuật toán gợi ý ca phù hợp
    """
    _name = 'employee.availability'
    _description = 'Employee Availability'
    _order = 'day_of_week, start_time'

    employee_id = fields.Many2one(
        'hr.employee',
        string='Nhân viên',
        required=True,
        ondelete='cascade'
    )
    
    day_of_week = fields.Selection([
        ('0', 'Thứ Hai'),
        ('1', 'Thứ Ba'),
        ('2', 'Thứ Tư'),
        ('3', 'Thứ Năm'),
        ('4', 'Thứ Sáu'),
        ('5', 'Thứ Bảy'),
        ('6', 'Chủ Nhật'),
    ], string='Ngày trong tuần', required=True)
    
    start_time = fields.Float(
        string='Giờ bắt đầu',
        help='VD: 8.0 = 08:00, 8.5 = 08:30'
    )
    end_time = fields.Float(
        string='Giờ kết thúc',
        help='VD: 17.0 = 17:00, 17.5 = 17:30'
    )
    
    is_available = fields.Boolean(
        string='Có thể làm việc',
        default=True,
        help='True = Rảnh, False = Bận'
    )
    
    note = fields.Char(
        string='Ghi chú',
        help='VD: Học buổi tối, Đi học thêm...'
    )

