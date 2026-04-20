# -*- coding: utf-8 -*-
from odoo import models, fields

class HrJobLevel(models.Model):
    _name = 'hr.job.level'
    _description = 'Cấp Bậc Công Việc'
    _order = 'sequence, name'

    name = fields.Char(string='Tên Cấp Bậc', required=True)
    code = fields.Char(string='Mã Cấp Bậc')
    grade_id = fields.Many2one('hr.job.grade', string='Ngạch (Job Grade)')
    sequence = fields.Integer(string='Thứ Tự', default=10)
    active = fields.Boolean(string='Hoạt Động', default=True)
