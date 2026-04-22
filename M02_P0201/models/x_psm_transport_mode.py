from odoo import models, fields

class TransportMode(models.Model):
    _name = 'x_psm_transport_mode'
    _description = 'Transport Mode'
    _rec_name = 'name'

    name = fields.Char(string='Transport Mode Name', required=True)
    active = fields.Boolean(default=True)
    type = fields.Selection([
        ('airplane', 'Airplane'),
        ('train', 'Train'),
        ('car', 'Car/Bus'),
        ('other', 'Other')
    ], string='Type', default='airplane')
