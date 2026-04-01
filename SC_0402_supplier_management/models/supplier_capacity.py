# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class SupplierCapacity(models.Model):
    _name = 'supplier.capacity'
    _description = 'Supplier Capacity Assessment'
    
    name = fields.Char(string='Assessment Name', required=True, default='Capacity Assessment')
    
    partner_id = fields.Many2one(
        'res.partner',
        string='Supplier',
        required=True,
    )
    
    evaluation_id = fields.Many2one(
        'supplier.evaluation',
        string='Evaluation',
        ondelete='cascade',
    )
    
    assessment_date = fields.Date(string='Assessment Date', default=fields.Date.today)
    
    # Capacity metrics
    daily_capacity = fields.Float(string='Daily Capacity (units)')
    monthly_capacity = fields.Float(string='Monthly Capacity (units)')
    
    current_utilization = fields.Float(
        string='Current Utilization (%)',
        help='Current capacity utilization percentage',
    )
    
    available_capacity = fields.Float(
        string='Available Capacity (%)',
        compute='_compute_available_capacity',
        store=True,
    )
    
    # Resources
    number_of_employees = fields.Integer(string='Number of Employees')
    number_of_production_lines = fields.Integer(string='Production Lines')
    warehouse_area = fields.Float(string='Warehouse Area (m²)')
    
    # Scalability
    can_scale_up = fields.Boolean(string='Can Scale Up', default=True)
    scale_up_timeframe = fields.Integer(string='Scale-Up Timeframe (days)')
    
    note = fields.Html(string='Notes')
    
    @api.depends('current_utilization')
    def _compute_available_capacity(self):
        for capacity in self:
            capacity.available_capacity = 100 - capacity.current_utilization
