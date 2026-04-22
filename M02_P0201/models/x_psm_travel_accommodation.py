from odoo import models, fields, api

class TravelAccommodation(models.Model):
    _name = 'x_psm_travel_accommodation'
    _description = 'Travel Accommodation'
    _rec_name = 'display_name'

    x_psm_request_id = fields.Many2one('x_psm_travel_request', string='Travel Request', ondelete='cascade')
    x_psm_traveler_line_id = fields.Many2one('x_psm_travel_request_line', string='Traveler', ondelete='cascade')
    
    x_psm_hotel_id = fields.Many2one('x_psm_travel_hotel', string='Hotel')
    x_psm_location_id = fields.Many2one('x_psm_travel_destination', string='City/Destination')
    
    x_psm_check_in = fields.Datetime(string='Check-in Date & Time')
    x_psm_check_out = fields.Datetime(string='Check-out Date & Time')
    
    x_psm_night_count = fields.Integer(string='Nights', compute='_compute_hotel_cost', store=True)
    x_psm_hotel_cost = fields.Float(string='Hotel Cost', compute='_compute_hotel_cost', store=True)
    x_psm_actual_total = fields.Float(string='Actual Cost')
    
    x_psm_voucher_attachment_ids = fields.Many2many('ir.attachment', string='Vouchers/Booking')
    
    x_psm_note = fields.Text(string='Note')
    
    x_psm_is_travel_admin = fields.Boolean(related='x_psm_request_id.x_psm_is_travel_admin')
    x_psm_state = fields.Selection(related='x_psm_request_id.x_psm_state', store=True)

    @api.onchange('x_psm_hotel_id')
    def _onchange_hotel_id(self):
        if self.x_psm_hotel_id:
            self.x_psm_location_id = self.x_psm_hotel_id.x_psm_destination_id

    @api.depends('x_psm_hotel_id', 'x_psm_check_in', 'x_psm_check_out', 'x_psm_traveler_line_id')
    def _compute_hotel_cost(self):
        for rec in self:
            nights = 0
            if rec.x_psm_check_in and rec.x_psm_check_out:
                delta = rec.x_psm_check_out - rec.x_psm_check_in
                nights = max(0, delta.days)
            rec.x_psm_night_count = nights
            
            # Calculate cost
            if not rec.x_psm_traveler_line_id or not rec.x_psm_request_id.x_psm_destination_id:
                rec.x_psm_hotel_cost = 0.0
                continue
                
            zone = rec.x_psm_request_id.x_psm_destination_id.x_psm_zone_id
            if not zone or not zone.x_psm_is_allowance:
                rec.x_psm_hotel_cost = 0.0
                continue
            
            # Find hotel rate from zone policy lines
            rate_line = zone.x_psm_allowance_line_ids.filtered(lambda l: rec.x_psm_traveler_line_id.x_psm_job_id in l.x_psm_job_ids)
            if not rate_line:
                rate_line = zone.x_psm_allowance_line_ids.filtered(lambda l: not l.x_psm_job_ids)
            
            max_rate = rate_line[0].x_psm_hotel_rate if rate_line else 0.0
            rate = max_rate
            if rec.x_psm_hotel_id and rec.x_psm_hotel_id.x_psm_reference_price > 0:
                rate = min(rec.x_psm_hotel_id.x_psm_reference_price, max_rate)
            
            rec.x_psm_hotel_cost = rate * nights

    @api.depends('x_psm_hotel_id', 'x_psm_check_in', 'x_psm_check_out')
    def _compute_display_name(self):
        for rec in self:
            if rec.x_psm_hotel_id:
                check_in_str = rec.x_psm_check_in.strftime('%Y-%m-%d %H:%M') if rec.x_psm_check_in else ""
                check_out_str = rec.x_psm_check_out.strftime('%Y-%m-%d %H:%M') if rec.x_psm_check_out else ""
                dates = f" ({check_in_str} - {check_out_str})" if check_in_str and check_out_str else ""
                rec.display_name = f"{rec.x_psm_hotel_id.x_psm_name}{dates}"
            else:
                rec.display_name = "Chỗ ở mới"

