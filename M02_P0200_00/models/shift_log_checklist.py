# -*- coding: utf-8 -*-
from odoo import models, fields


class ShiftLogChecklist(models.Model):
    _name = 'shift.log.checklist'
    _description = 'Master Checklist Ca Làm'
    _order = 'shift_phase, sequence, id'

    name = fields.Char(string='Tên Công Việc', required=True)
    shift_phase = fields.Selection([
        ('preshift', 'Pre-shift'),
        ('during', 'During Shift'),
        ('postshift', 'Post-shift'),
    ], string='Giai Đoạn', required=True)
    category = fields.Char(string='Phân Loại')
    sequence = fields.Integer(string='Thứ Tự', default=10)
    description = fields.Text(string='Mô Tả')
