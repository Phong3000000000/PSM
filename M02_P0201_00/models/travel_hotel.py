from odoo import models, fields


class TravelHotel(models.Model):
    _name = 'travel.hotel'
    _description = 'Travel Hotel'
    _order = 'province_id, name'

    name = fields.Char(
        string='Hotel Name',
        required=True,
    )

    province_id = fields.Many2one(
        'travel.province',
        string='Province / City',
        required=True,
        ondelete='restrict',
    )

    address = fields.Char(
        string='Address'
    )

    price_per_night = fields.Monetary(
        string='Price per Night',
        required=True,
    )

    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        default=lambda self: self.env.company.currency_id.id,
        required=True,
    )

    note = fields.Text(
        string='Notes'
    )

    active = fields.Boolean(
        default=True
    )
