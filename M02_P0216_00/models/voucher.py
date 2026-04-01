# models/voucher.py
from odoo import models, fields, api

class Voucher(models.Model):
    _name = 'voucher.voucher'
    _description = 'Voucher'
    _rec_name = 'name'

    code = fields.Char(
        string='Mã voucher',
        required=True,
        copy=False
    )
    name = fields.Char(
        string='Tên voucher',
        required=True
    )
    value = fields.Monetary(
        string='Mệnh giá',
        required=True
    )
    denomination = fields.Selection([
        ('50000', '50.000'),
        ('100000', '100.000'),
        ('200000', '200.000'),
    ], string='Mệnh giá (Danh mục)', required=True, default='50000')
    point_required = fields.Integer(
        string='Điểm để đổi',
        required=True
    )
    quantity = fields.Integer(
        string='Số lượng',
        default=0
    )
    state = fields.Selection([
        ('draft', 'Nháp'),
        ('active', 'Đang dùng'),
        ('expired', 'Hết hạn'),
    ], default='draft')

    partner_id = fields.Many2one(
        'urbox.partner',
        string='Đối tác Urbox',
        ondelete='restrict'
    )

    currency_id = fields.Many2one(
        'res.currency',
        default=lambda self: self.env.company.currency_id
    )