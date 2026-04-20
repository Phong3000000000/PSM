# -*- coding: utf-8 -*-
from odoo import models, fields


class RestaurantShift(models.Model):
    _name = 'restaurant.shift'
    _description = 'Ca Làm Việc'
    _order = 'hour_from'

    name = fields.Char(string='Tên Ca', required=True)
    code = fields.Char(string='Mã Ca')
    hour_from = fields.Float(string='Giờ Bắt Đầu', required=True)
    hour_to = fields.Float(string='Giờ Kết Thúc', required=True)

    _sql_constraints = [
        ('code_unique', 'unique(code)', 'Mã ca làm phải là duy nhất!'),
    ]
