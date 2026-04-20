# -*- coding: utf-8 -*-
from odoo import models, fields


class HrJobPositionDefault(models.Model):
    _name = 'hr.job.position.default'
    _description = 'Vị Trí Công Việc Mặc Định'
    _order = 'block_id, sequence, name'

    name = fields.Char(string='Tên Vị Trí', required=True)
    name_ll = fields.Char(string='Tên Tiếng Việt', help='Tên vị trí bằng tiếng Việt')
    code = fields.Char(string='Mã Viết Tắt', required=True)
    block_id = fields.Many2one(
        'department.block',
        string='Khối',
        required=True,
        ondelete='cascade',
    )
    contract_type_ids = fields.Many2many('hr.contract.type', string='Loại Hợp Đồng')
    grade_id = fields.Many2one('hr.job.grade', string='Ngạch (Job Grade)')
    level_id = fields.Many2one('hr.job.level', string='Level')
    sequence = fields.Integer(string='Thứ Tự', default=10)
    active = fields.Boolean(string='Hoạt Động', default=True)


    _sql_constraints = [
        ('code_block_unique', 'unique(code, block_id)',
         'Mã viết tắt phải là duy nhất trong mỗi khối!'),
    ]
