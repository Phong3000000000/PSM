from odoo import models, fields, api

class TravelSchedule(models.Model):
    _name = 'x_psm_travel_schedule'
    _description = 'Business Trip Schedule'
    _order = 'x_psm_date, id'

    x_psm_request_id = fields.Many2one('x_psm_travel_request', string='Travel Request', ondelete='cascade')
    x_psm_traveler_line_id = fields.Many2one('x_psm_travel_request_line', string='Traveler', required=True, ondelete='cascade')
    x_psm_employee_id = fields.Many2one('hr.employee', related='x_psm_traveler_line_id.x_psm_employee_id', store=True, string='Participant')
    
    x_psm_date = fields.Date(string='Date', required=True)
    x_psm_type = fields.Selection([
        ('on', 'ON'),
        ('off', 'OFF')
    ], string='Type', default='on', required=True)
    
    x_psm_content = fields.Text(string='Work Content')
    x_psm_allowance = fields.Float(string='Allowance', compute='_compute_allowance', store=True)

    @api.depends('x_psm_traveler_line_id', 'x_psm_type', 'x_psm_date', 'x_psm_request_id.x_psm_destination_id')
    def _compute_allowance(self):
        for rec in self:
            if rec.x_psm_type == 'off' or not rec.x_psm_traveler_line_id or not rec.x_psm_request_id.x_psm_destination_id:
                rec.x_psm_allowance = 0.0
                continue
            
            # Re-use logic from traveler line to get the rate
            # Note: We use the traveler line's eligibility and job
            line = rec.x_psm_traveler_line_id
            if not line.x_psm_is_eligible_allowance:
                rec.x_psm_allowance = 0.0
                continue
                
            zone = rec.x_psm_request_id.x_psm_destination_id.x_psm_zone_id
            if not zone or not zone.x_psm_is_allowance:
                rec.x_psm_allowance = 0.0
                continue
            
            rate_line = zone.x_psm_allowance_line_ids.filtered(lambda l: line.x_psm_job_id in l.x_psm_job_ids)
            if not rate_line:
                rate_line = zone.x_psm_allowance_line_ids.filtered(lambda l: not l.x_psm_job_ids)
            
            rate = rate_line[0].x_psm_allowance_rate if rate_line else 0.0
            rec.x_psm_allowance = rate
