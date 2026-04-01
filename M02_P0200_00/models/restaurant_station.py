# -*- coding: utf-8 -*-
from odoo import models, fields


class RestaurantStation(models.Model):
    _name = 'restaurant.station'
    _description = 'Vị Trí Chi Tiết Nhà Hàng'
    _order = 'positioning_area_id, name'

    name = fields.Char(string='Tên Station', required=True)
    code = fields.Char(string='Positioning Code')
    positioning_area_id = fields.Many2one(
        'restaurant.positioning.area',
        string='Khu Vực Nhỏ',
        required=True,
        ondelete='cascade',
    )
    menu_type = fields.Selection([
        ('breakfast', 'Breakfast'),
        ('regular', 'Regular'),
        ('all', 'All'),
    ], string='Menu Type')
