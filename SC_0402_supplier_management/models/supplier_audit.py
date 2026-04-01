# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class SupplierAudit(models.Model):
    _name = 'supplier.audit'
    _description = 'Factory Audit'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'audit_date desc, id desc'
    
    name = fields.Char(string='Audit Number', required=True, copy=False, default='New')
    
    evaluation_id = fields.Many2one(
        'supplier.evaluation',
        string='Evaluation',
        ondelete='cascade',
    )
    
    partner_id = fields.Many2one(
        'res.partner',
        string='Supplier',
        required=True,
        tracking=True,
    )
    
    audit_type = fields.Selection([
        ('initial', 'Initial Audit'),
        ('periodic', 'Periodic Audit'),
        ('follow_up', 'Follow-up Audit'),
        ('special', 'Special Audit'),
    ], string='Audit Type', required=True, default='initial', tracking=True)
    
    audit_date = fields.Date(string='Audit Date', required=True, tracking=True)
    
    auditor_ids = fields.Many2many(
        'res.users',
        string='Auditors',
    )
    
    # Ratings
    quality_rating = fields.Selection([
        ('1', 'Poor'),
        ('2', 'Fair'),
        ('3', 'Good'),
        ('4', 'Very Good'),
        ('5', 'Excellent'),
    ], string='Quality Rating')
    
    safety_rating = fields.Selection([
        ('1', 'Poor'),
        ('2', 'Fair'),
        ('3', 'Good'),
        ('4', 'Very Good'),
        ('5', 'Excellent'),
    ], string='Safety Rating')
    
    hygiene_rating = fields.Selection([
        ('1', 'Poor'),
        ('2', 'Fair'),
        ('3', 'Good'),
        ('4', 'Very Good'),
        ('5', 'Excellent'),
    ], string='Hygiene Rating')
    
    overall_score = fields.Float(
        string='Overall Score',
        compute='_compute_overall_score',
        store=True,
    )
    
    result = fields.Selection([
        ('pass', 'Pass'),
        ('conditional_pass', 'Conditional Pass'),
        ('fail', 'Fail'),
    ], string='Result', tracking=True)
    
    # Integration with quality_control module
    quality_check_ids = fields.Many2many(
        'quality.check',
        string='Quality Checks',
    )
    
    # Integration with documents module
    document_ids = fields.Many2many(
        'documents.document',
        string='Audit Documents',
        help='Photos, videos, reports from factory visit',
    )
    
    findings = fields.Html(string='Findings')
    recommendations = fields.Html(string='Recommendations')
    
    follow_up_required = fields.Boolean(string='Follow-up Required')
    follow_up_deadline = fields.Date(string='Follow-up Deadline')
    
    @api.depends('quality_rating', 'safety_rating', 'hygiene_rating')
    def _compute_overall_score(self):
        for audit in self:
            ratings = [
                int(audit.quality_rating) if audit.quality_rating else 0,
                int(audit.safety_rating) if audit.safety_rating else 0,
                int(audit.hygiene_rating) if audit.hygiene_rating else 0,
            ]
            audit.overall_score = sum(ratings) / len([r for r in ratings if r > 0]) if any(ratings) else 0.0
    
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('supplier.audit') or 'New'
        return super().create(vals_list)
