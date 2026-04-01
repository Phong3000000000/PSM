# -*- coding: utf-8 -*-
from odoo import models, fields


class RestaurantPositioningArea(models.Model):
    _name = 'restaurant.positioning.area'
    _description = 'Khu Vực Nhỏ Nhà Hàng'
    _order = 'area_id, name'

    name = fields.Char(string='Tên Vị Trí', required=True)
    area_id = fields.Many2one(
        'restaurant.area',
        string='Khu Vực Lớn',
        required=True,
        ondelete='cascade',
    )
    station_ids = fields.One2many(
        'restaurant.station', 'positioning_area_id',
        string='Các Station',
    )
