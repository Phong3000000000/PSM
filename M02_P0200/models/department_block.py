# -*- coding: utf-8 -*-
from odoo import models, fields


class DepartmentBlock(models.Model):
    _name = 'department.block'
    _description = 'Khối Phòng Ban'
    _order = 'name'

    name = fields.Char(string='Tên Khối', required=True)
    code = fields.Char(string='Mã Viết Tắt', required=True)
    active = fields.Boolean(string='Hoạt Động', default=True)

    _sql_constraints = [
        ('code_unique', 'unique(code)', 'Mã khối phải là duy nhất!'),
    ]
