from odoo import models, fields, api

class TravelItinerary(models.Model):
    _name = 'x_psm_travel_itinerary'
    _description = 'Travel Itinerary Segment'
    _rec_name = 'display_name'

    x_psm_request_id = fields.Many2one('x_psm_travel_request', string='Travel Request', ondelete='cascade')
    x_psm_traveler_line_id = fields.Many2one('x_psm_travel_request_line', string='Traveler', ondelete='cascade')
    
    x_psm_from_city_id = fields.Many2one('x_psm_travel_destination', string='From')
    x_psm_to_city_id = fields.Many2one('x_psm_travel_destination', string='To')
    
    x_psm_departure_datetime = fields.Datetime(string='Departure Date & Time')
    x_psm_arrival_datetime = fields.Datetime(string='Arrival Date & Time')
    
    x_psm_transport_mode_id = fields.Many2one('x_psm_transport_mode', string='Transport Mode')
    x_psm_airline_id = fields.Many2one('x_psm_airline', string='Airline')
    x_psm_seat_class_id = fields.Many2one('x_psm_seat_class', string='Seat Class')
    x_psm_flight_number = fields.Char(string='Flight/Trip Number')
    
    x_psm_proposed_total = fields.Float(string='Estimated Cost')
    x_psm_actual_total = fields.Float(string='Actual Cost')
    
    x_psm_ticket_attachment_ids = fields.Many2many('ir.attachment', string='Tickets')
    
    x_psm_note = fields.Text(string='Note')
    
    x_psm_is_travel_admin = fields.Boolean(related='x_psm_request_id.x_psm_is_travel_admin')
    x_psm_state = fields.Selection(related='x_psm_request_id.x_psm_state', store=True)

    @api.depends('x_psm_from_city_id', 'x_psm_to_city_id')
    def _compute_display_name(self):
        for rec in self:
            if rec.x_psm_from_city_id and rec.x_psm_to_city_id:
                rec.display_name = f"{rec.x_psm_from_city_id.x_psm_name} -> {rec.x_psm_to_city_id.x_psm_name}"
            else:
                rec.display_name = "Chặng mới"

