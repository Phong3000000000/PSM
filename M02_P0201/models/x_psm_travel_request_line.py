from odoo import models, fields, api

class TravelRequestLine(models.Model):
    _name = 'x_psm_travel_request_line'
    _description = 'Travel Request Line'
    _rec_name = 'x_psm_employee_id'

    x_psm_request_id = fields.Many2one('x_psm_travel_request', string='Request', ondelete='cascade')
    x_psm_employee_id = fields.Many2one('hr.employee', string='Employee', required=True)
    x_psm_job_id = fields.Many2one('hr.job', related='x_psm_employee_id.job_id', store=True, string='Job Position')
    x_psm_department_id = fields.Many2one('hr.department', related='x_psm_employee_id.department_id', store=True, string='Department')
    
    x_psm_identification_id = fields.Char(string='ID/CCCD', related='x_psm_employee_id.identification_id', store=True)
    x_psm_phone = fields.Char(string='Phone', related='x_psm_employee_id.mobile_phone', store=True)
    x_psm_email = fields.Char(string='Email', related='x_psm_employee_id.work_email', store=True)
    
    x_psm_is_eligible_allowance = fields.Boolean(string='Eligible for Allowance', compute='_compute_eligibility')
    x_psm_allowance_per_day = fields.Float(string='Daily Allowance', compute='_compute_allowance', store=True)
    x_psm_allowance_total = fields.Float(string='Total Allowance', compute='_compute_allowance', store=True)
    
    x_psm_schedule_ids = fields.One2many('x_psm_travel_schedule', 'x_psm_traveler_line_id', string='Schedules')
    x_psm_accommodation_ids = fields.One2many('x_psm_travel_accommodation', 'x_psm_traveler_line_id', string='Accommodations')
    
    x_psm_hotel_cost_share = fields.Float(string='Hotel Cost Share', compute='_compute_hotel_share', store=True)
    x_psm_laundry_cost = fields.Float(
        string='Laundry Cost', 
        compute='_compute_laundry_cost', 
        store=True, 
        readonly=False
    )

    @api.onchange('x_psm_employee_id')
    def _onchange_employee_id(self):
        # Fields like ID, Phone and Email are now automatic related fields
        pass

    @api.depends('x_psm_request_id.x_psm_duration_days', 'x_psm_request_id.x_psm_destination_id')
    def _compute_laundry_cost(self):
        """Tự động tính phí giặt ủi khi lưu hoặc thay đổi thông tin."""
        for line in self:
            req = line.x_psm_request_id
            if req and req.x_psm_duration_days > 7 and req.x_psm_destination_id:
                zone = req.x_psm_destination_id.x_psm_zone_id
                # Chỉ tự điền nếu đang bằng 0 hoặc chưa có giá trị
                if zone and not line.x_psm_laundry_cost:
                    line.x_psm_laundry_cost = zone.x_psm_laundry_limit
            elif req and req.x_psm_duration_days <= 7:
                line.x_psm_laundry_cost = 0.0

    @api.depends('x_psm_request_id.x_psm_destination_id', 'x_psm_request_id.x_psm_overnight_count')
    def _compute_eligibility(self):
        for line in self:
            req = line.x_psm_request_id
            if req.x_psm_destination_id and req.x_psm_destination_id.x_psm_is_international:
                line.x_psm_is_eligible_allowance = True
            elif req.x_psm_destination_id:
                adj = req.x_psm_destination_id.x_psm_is_adjacent_hcm
                overnight = req.x_psm_overnight_count > 0
                if not adj:
                    line.x_psm_is_eligible_allowance = True
                elif adj and overnight:
                    line.x_psm_is_eligible_allowance = True
                else:
                    line.x_psm_is_eligible_allowance = False
            else:
                line.x_psm_is_eligible_allowance = False

    @api.depends('x_psm_job_id', 'x_psm_is_eligible_allowance', 'x_psm_request_id.x_psm_destination_id', 
                 'x_psm_request_id.x_psm_duration_days', 'x_psm_schedule_ids.x_psm_allowance', 'x_psm_schedule_ids.x_psm_type')
    def _compute_allowance(self):
        for line in self:
            if not line.x_psm_is_eligible_allowance or not line.x_psm_job_id or not line.x_psm_request_id.x_psm_destination_id:
                line.x_psm_allowance_per_day = 0.0
                line.x_psm_allowance_total = 0.0
                continue
                
            zone = line.x_psm_request_id.x_psm_destination_id.x_psm_zone_id
            if not zone or not zone.x_psm_is_allowance:
                line.x_psm_allowance_per_day = 0.0
                line.x_psm_allowance_total = 0.0
                continue
            
            # Rate detection (lookup in zone lines)
            rate_line = zone.x_psm_allowance_line_ids.filtered(lambda l: line.x_psm_job_id in l.x_psm_job_ids)
            if not rate_line:
                rate_line = zone.x_psm_allowance_line_ids.filtered(lambda l: not l.x_psm_job_ids)
            
            rate = rate_line[0].x_psm_allowance_rate if rate_line else 0.0
            line.x_psm_allowance_per_day = rate
            
            # Sum of ON days from schedule
            if line.x_psm_schedule_ids:
                on_lines = line.x_psm_schedule_ids.filtered(lambda s: s.x_psm_type == 'on')
                line.x_psm_allowance_total = sum(on_lines.mapped('x_psm_allowance'))
            else:
                # Default to duration based
                line.x_psm_allowance_total = rate * line.x_psm_request_id.x_psm_duration_days

    @api.depends('x_psm_accommodation_ids.x_psm_hotel_cost')
    def _compute_hotel_share(self):
        for line in self:
            if line.x_psm_accommodation_ids:
                line.x_psm_hotel_cost_share = sum(line.x_psm_accommodation_ids.mapped('x_psm_hotel_cost'))
            else:
                # Fallback to header hotel based calculation if no accommodation lines yet
                req = line.x_psm_request_id
                if not req or not req.x_psm_destination_id:
                    line.x_psm_hotel_cost_share = 0.0
                    continue
                
                zone = req.x_psm_destination_id.x_psm_zone_id
                if not zone:
                    line.x_psm_hotel_cost_share = 0.0
                    continue
                
                # Find hotel rate from zone policy lines
                rate_line = zone.x_psm_allowance_line_ids.filtered(lambda l: line.x_psm_job_id in l.x_psm_job_ids)
                if not rate_line:
                    rate_line = zone.x_psm_allowance_line_ids.filtered(lambda l: not l.x_psm_job_ids)
                
                max_rate = rate_line[0].x_psm_hotel_rate if rate_line else 0.0
                rate = max_rate
                if req.x_psm_hotel_id and req.x_psm_hotel_id.x_psm_reference_price > 0:
                    rate = min(req.x_psm_hotel_id.x_psm_reference_price, max_rate)
                
                line.x_psm_hotel_cost_share = rate * req.x_psm_duration_days

    @api.constrains('x_psm_laundry_cost')
    def _check_laundry_limit(self):
        for line in self:
            if line.x_psm_laundry_cost <= 0:
                continue
            
            zone = line.x_psm_request_id.x_psm_destination_id.x_psm_zone_id
            if not zone:
                continue
                
            limit = zone.x_psm_laundry_limit
            if line.x_psm_laundry_cost > limit:
                raise ValidationError(_(
                    "Phí giặt ủi của %s vượt quá hạn mức %s VND của vùng %s!"
                ) % (line.x_psm_employee_id.name, "{:,.0f}".format(limit), zone.x_psm_name))
