# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import ValidationError


class SalaryIncreaseConfig(models.Model):
    _name = 'salary.increase.config'
    _description = 'Salary Increase Configuration'
    _order = 'rating_from desc'
    
    name = fields.Char(
        string='Name',
        required=True,
        help='Name of this salary increase level'
    )
    
    rating_from = fields.Float(
        string='Rating From',
        required=True,
        help='Minimum performance rating for this level (inclusive)'
    )
    
    rating_to = fields.Float(
        string='Rating To',
        required=True,
        help='Maximum performance rating for this level (inclusive)'
    )
    
    increase_percentage = fields.Float(
        string='Salary Increase (%)',
        required=True,
        help='Percentage of salary increase for this performance level'
    )
    
    active = fields.Boolean(
        default=True
    )
    
    department_id = fields.Many2one(
        'hr.department',
        string='Department',
        default=lambda self: self.env.user.employee_id.department_id
    )
    
    sequence = fields.Integer(
        default=10,
        help='Sequence for ordering'
    )
    
    @api.constrains('rating_from', 'rating_to')
    def _check_rating_range(self):
        """Validate that rating_from < rating_to"""
        for record in self:
            if record.rating_from >= record.rating_to:
                raise ValidationError(
                    'Rating From must be less than Rating To!'
                )
    
    @api.constrains('increase_percentage')
    def _check_increase_percentage(self):
        """Validate increase percentage is not negative"""
        for record in self:
            if record.increase_percentage < 0:
                raise ValidationError(
                    'Salary increase percentage cannot be negative!'
                )
    
    @api.model
    def get_increase_for_rating(self, rating):
        """Get salary increase percentage for a given performance rating."""
        if not rating:
            return 0.0
        
        config = self.search([
            ('rating_from', '<=', rating),
            ('rating_to', '>=', rating),
            ('active', '=', True)
        ], limit=1)
        
        return config.increase_percentage if config else 0.0
