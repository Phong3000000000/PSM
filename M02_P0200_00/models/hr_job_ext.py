# -*- coding: utf-8 -*-
from odoo import models, fields


class HrJob(models.Model):
    _inherit = 'hr.job'

    code = fields.Char(string='Mã Viết Tắt')
    name_ll = fields.Char(string='Tên Tiếng Việt', help='Tên vị trí bằng tiếng Việt')
    level_id = fields.Many2one('hr.job.level', string='Level')

    _sql_constraints = [
        ('code_dept_unique', 'unique(code, department_id, company_id)',
         'Mã viết tắt phải là duy nhất trong mỗi phòng ban!'),
    ]
