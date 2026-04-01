# -*- coding: utf-8 -*-
from odoo import models, fields


class RestaurantArea(models.Model):
    _name = 'restaurant.area'
    _description = 'Khu Vực Lớn Nhà Hàng'
    _order = 'name'

    name = fields.Char(string='Tên Khu Vực', required=True)
    code = fields.Char(string='Mã Khu Vực')
    positioning_area_ids = fields.One2many(
        'restaurant.positioning.area', 'area_id',
        string='Khu Vực Nhỏ',
    )
