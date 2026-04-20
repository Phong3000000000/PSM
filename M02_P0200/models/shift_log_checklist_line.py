# -*- coding: utf-8 -*-
from odoo import models, fields


class ShiftLogChecklistLine(models.Model):
    _name = 'shift.log.checklist.line'
    _description = 'Dòng Checklist Ca Làm'
    _order = 'shift_phase, sequence, id'

    shift_log_id = fields.Many2one(
        'shift.log',
        string='Ca Làm',
        required=True,
        ondelete='cascade',
    )
    checklist_id = fields.Many2one(
        'shift.log.checklist',
        string='Công Việc',
        required=True,
    )
    shift_phase = fields.Selection([
        ('preshift', 'Pre-shift'),
        ('during', 'During Shift'),
        ('postshift', 'Post-shift'),
    ], string='Giai Đoạn')
    sequence = fields.Integer(
        related='checklist_id.sequence',
        store=True,
    )
    is_done = fields.Boolean(string='Hoàn Thành', default=False)
    responsible_id = fields.Many2one(
        'hr.employee',
        string='Người Thực Hiện',
    )
    result = fields.Char(string='Kết Quả')
    notes = fields.Text(string='Ghi Chú')
