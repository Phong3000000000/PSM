# -*- coding: utf-8 -*-
from odoo import models, fields, api


class AttendanceRating(models.Model):
    """
    Đánh giá hiệu suất cuối ca
    Lưu dữ liệu rating khi nhân viên check-out
    """
    _name = 'attendance.rating'
    _description = 'Đánh giá hiệu suất cuối ca'
    _order = 'create_date desc'

    employee_id = fields.Many2one(
        'hr.employee',
        string='Nhân viên',
        required=True,
        ondelete='cascade'
    )
    attendance_id = fields.Many2one(
        'hr.attendance',
        string='Bản ghi chấm công',
        ondelete='set null'
    )
    date = fields.Date(
        string='Ngày',
        default=fields.Date.today,
        required=True
    )
    
    # Rating fields
    performance_rating = fields.Selection([
        ('1', '⭐ Rất tệ'),
        ('2', '⭐⭐ Tệ'),
        ('3', '⭐⭐⭐ Bình thường'),
        ('4', '⭐⭐⭐⭐ Tốt'),
        ('5', '⭐⭐⭐⭐⭐ Xuất sắc'),
    ], string='Hiệu suất tự đánh giá', default='3')
    
    confirmed_hours = fields.Float(
        string='Giờ làm xác nhận',
        help='Số giờ nhân viên xác nhận đã làm'
    )
    
    note = fields.Text(
        string='Ghi chú',
        help='Ghi chú về công việc, sự cố nếu có'
    )
    
    is_confirmed = fields.Boolean(
        string='Đã xác nhận',
        default=False
    )


class HrAttendanceExt(models.Model):
    """
    Mở rộng hr.attendance để liên kết với rating
    """
    _inherit = 'hr.attendance'
    
    rating_id = fields.Many2one(
        'attendance.rating',
        string='Đánh giá cuối ca',
        readonly=True
    )
    
    is_late = fields.Boolean(
        string='Đi muộn',
        compute='_compute_late_early',
        store=True
    )
    is_early_leave = fields.Boolean(
        string='Về sớm',
        compute='_compute_late_early',
        store=True
    )
    
    @api.depends('check_in', 'check_out')
    def _compute_late_early(self):
        """Tính toán đi muộn/về sớm dựa trên planning slot"""
        for rec in self:
            rec.is_late = False
            rec.is_early_leave = False
            # TODO: So sánh với planning.slot để xác định muộn/sớm

