from odoo import models, fields

class SeatClass(models.Model):
    _name = 'x_psm_seat_class'
    _description = 'Seat Class'
    _rec_name = 'name'

    name = fields.Char(string='Seat Class Name', required=True)
    active = fields.Boolean(default=True)
    x_psm_transport_mode_id = fields.Many2one('x_psm_transport_mode', string='Transport Mode')
