# -*- coding: utf-8 -*-
from odoo import models, fields


class StockMoveLine(models.Model):
    _inherit = 'stock.move.line'

    qip_status = fields.Selection([
        ('pending', 'Chờ kiểm tra'),
        ('passed', 'Đạt'),
        ('failed', 'Lỗi'),
    ], string='Trạng thái QIP', default='pending', tracking=True)


class StockMove(models.Model):
    _inherit = 'stock.move'

    qip_status = fields.Selection([
        ('pending', 'Chờ kiểm tra'),
        ('passed', 'Đạt'),
        ('failed', 'Lỗi'),
    ], string='Trạng thái QIP', default='pending', tracking=True)
