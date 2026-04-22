from odoo import models, fields

class Airline(models.Model):
    _name = 'x_psm_airline'
    _description = 'Airline'
    _rec_name = 'name'

    name = fields.Char(string='Airline Name', required=True)
    active = fields.Boolean(default=True)
    logo = fields.Binary(string='Logo')
