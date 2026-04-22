from odoo import models, fields

class TravelHotel(models.Model):
    _name = 'x_psm_travel_hotel'
    _description = 'Travel Hotel'
    _rec_name = 'x_psm_name'

    x_psm_name = fields.Char(string='Name', required=True)
    x_psm_destination_id = fields.Many2one('x_psm_travel_destination', string='Destination', required=True)
    x_psm_zone_id = fields.Many2one('x_psm_travel_zone', related='x_psm_destination_id.x_psm_zone_id', store=True, string='Zone')
    x_psm_address = fields.Char(string='Address')
    x_psm_reference_price = fields.Float(string='Reference Price')
    x_psm_currency_id = fields.Many2one('res.currency', string='Currency')
    x_psm_active = fields.Boolean(string='Active', default=True)
    x_psm_is_preferred = fields.Boolean(string='Preferred', default=False)
    x_psm_note = fields.Text(string='Note')
