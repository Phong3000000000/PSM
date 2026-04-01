# -*- coding: utf-8 -*-
from odoo import models, fields


class ShiftLogEmployee(models.Model):
    _name = 'shift.log.employee'
    _description = 'Nhân Viên Trong Ca'
    _order = 'employee_id'

    shift_log_id = fields.Many2one(
        'shift.log',
        string='Ca Làm',
        required=True,
        ondelete='cascade',
    )
    employee_id = fields.Many2one(
        'hr.employee',
        string='Nhân Viên',
        required=True,
    )
    working_hours = fields.Float(
        string='Số Giờ Làm',
        help='Số giờ làm việc của nhân viên trong ca này',
    )
    attendance_status = fields.Selection([
        ('present', 'Có Mặt'),
        ('absent', 'Vắng'),
        ('late', 'Đi Trễ'),
    ], string='Trạng Thái', default='present')
    notes = fields.Char(string='Ghi Chú')
