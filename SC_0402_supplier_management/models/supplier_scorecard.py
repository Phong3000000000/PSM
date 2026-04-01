# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class SupplierScorecard(models.Model):
    _name = 'supplier.scorecard'
    _description = 'Supplier Scorecard'
    
    name = fields.Char(string='Scorecard Name', compute='_compute_name', store=True)
    
    evaluation_id = fields.Many2one(
        'supplier.evaluation',
        string='Evaluation',
        ondelete='cascade',
    )
    
    partner_id = fields.Many2one(
        'res.partner',
        string='Supplier',
        required=True,
    )
    
    product_tmpl_id = fields.Many2one(
        'product.template',
        string='Product',
    )
    
    scorecard_date = fields.Date(string='Date', default=fields.Date.today)
    
    # Scoring categories (out of 100)
    quality_score = fields.Float(string='Quality Score')
    capacity_score = fields.Float(string='Capacity Score')
    compliance_score = fields.Float(string='Compliance Score')
    cost_score = fields.Float(string='Cost Score')
    
    total_score = fields.Float(
        string='Total Score',
        compute='_compute_total_score',
        store=True,
    )
    
    rating = fields.Selection([
        ('a', 'A - Excellent (≥90)'),
        ('b', 'B - Good (80-89)'),
        ('c', 'C - Fair (70-79)'),
        ('d', 'D - Poor (60-69)'),
        ('f', 'F - Fail (<60)'),
    ], string='Rating', compute='_compute_rating', store=True)
    
    recommendation = fields.Selection([
        ('approved', 'Approved'),
        ('approved_conditional', 'Approved with Conditions'),
        ('not_approved', 'Not Approved'),
    ], string='Recommendation')
    
    notes = fields.Html(string='Notes')
    
    @api.depends('partner_id', 'product_tmpl_id')
    def _compute_name(self):
        for scorecard in self:
            if scorecard.partner_id and scorecard.product_tmpl_id:
                scorecard.name = f"{scorecard.partner_id.name} - {scorecard.product_tmpl_id.name}"
            elif scorecard.partner_id:
                scorecard.name = scorecard.partner_id.name
            else:
                scorecard.name = 'New Scorecard'
    
    @api.depends('quality_score', 'capacity_score', 'compliance_score', 'cost_score')
    def _compute_total_score(self):
        for scorecard in self:
            # Weighted average: Quality 40%, Capacity 20%, Compliance 30%, Cost 10%
            scorecard.total_score = (
                scorecard.quality_score * 0.4 +
                scorecard.capacity_score * 0.2 +
                scorecard.compliance_score * 0.3 +
                scorecard.cost_score * 0.1
            )
    
    @api.depends('total_score')
    def _compute_rating(self):
        for scorecard in self:
            if scorecard.total_score >= 90:
                scorecard.rating = 'a'
            elif scorecard.total_score >= 80:
                scorecard.rating = 'b'
            elif scorecard.total_score >= 70:
                scorecard.rating = 'c'
            elif scorecard.total_score >= 60:
                scorecard.rating = 'd'
            else:
                scorecard.rating = 'f'
    
    def action_calculate_score(self):
        """Auto-calculate scores from evaluation data"""
        for scorecard in self:
            if not scorecard.evaluation_id:
                continue
            
            evaluation = scorecard.evaluation_id
            
            # Quality score from lab tests and sensory tests
            lab_pass_rate = 0
            if evaluation.lab_test_ids:
                passed = len(evaluation.lab_test_ids.filtered(lambda t: t.result == 'pass'))
                lab_pass_rate = (passed / len(evaluation.lab_test_ids)) * 100
            
            sensory_avg = 0
            if evaluation.sensory_test_ids:
                scores = evaluation.sensory_test_ids.mapped('overall_score')
                sensory_avg = (sum(scores) / len(scores)) * 20  # Convert 5-scale to 100-scale
            
            scorecard.quality_score = (lab_pass_rate + sensory_avg) / 2 if lab_pass_rate or sensory_avg else 0
            
            # Capacity score from capacity assessment
            if evaluation.capacity_id:
                scorecard.capacity_score = evaluation.capacity_id.available_capacity
            
            # Compliance score from certificates and audits
            cert_score = len(evaluation.certificate_ids.filtered(lambda c: not c.is_expired)) * 20  # Max 100
            audit_score = 0
            if evaluation.audit_ids:
                audit_score = evaluation.audit_ids[0].overall_score * 20  # Convert 5-scale to 100
            
            scorecard.compliance_score = min((cert_score + audit_score) / 2, 100)
            
            # Cost score (placeholder - would need pricing data)
            scorecard.cost_score = 75.0  # Default
