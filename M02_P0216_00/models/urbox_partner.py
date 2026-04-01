# models/urbox_partner.py
from odoo import models, fields, api

class UrboxPartner(models.Model):
    _name = 'urbox.partner'
    _description = 'Urbox Partner'
    _rec_name = 'name'

    name = fields.Char(
        string='Tên đối tác',
        required=True
    )
    code = fields.Char(
        string='Mã đối tác',
        copy=False
    )
    logo = fields.Image(
        string='Logo',
        max_width=256,
        max_height=256
    )
    description = fields.Text(
        string='Mô tả'
    )
    website = fields.Char(
        string='Website'
    )
    active = fields.Boolean(
        string='Hoạt động',
        default=True
    )
    voucher_count = fields.Integer(
        string='Số lượng voucher',
        compute='_compute_voucher_count'
    )

    _sql_constraints = [
        ('code_unique', 'unique(code)', 'Mã đối tác phải là duy nhất!')
    ]

    def _compute_voucher_count(self):
        for partner in self:
            partner.voucher_count = self.env['voucher.voucher'].search_count([
                ('partner_id', '=', partner.id)
            ])
