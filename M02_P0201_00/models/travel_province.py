from odoo import models, fields


class TravelProvince(models.Model):
    _name = 'travel.province'
    _description = 'Travel Province / City'
    _order = 'name'

    name = fields.Char(
        string='Province / City',
        required=True,
    )

    code = fields.Char(
        string='Code',
        help='Optional short code (HN, HCM, DN, ...)'
    )

    active = fields.Boolean(
        default=True
    )
