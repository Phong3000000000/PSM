# -*- coding: utf-8 -*-

from odoo import models, fields, api


class PostShift(models.Model):
    _name = 'post.shift'
    _description = 'Post Shift Score'
    _order = 'shift_evaluation_id, employee_id'

    shift_evaluation_id = fields.Many2one(
        'shift.evaluation',
        string='Shift Evaluation',
        required=True,
        ondelete='cascade'
    )
    employee_id = fields.Many2one(
        'hr.employee',
        string='Nhân viên',
        required=True
    )
    shift = fields.Selection(
        related='shift_evaluation_id.shift',
        string='Ca làm',
        store=True,
        readonly=True
    )
    date = fields.Date(
        related='shift_evaluation_id.date',
        string='Ngày',
        store=True,
        readonly=True
    )
    score = fields.Float(
        string='Điểm',
        default=0.0
    )
    description = fields.Char(
        string='Mô tả'
    )