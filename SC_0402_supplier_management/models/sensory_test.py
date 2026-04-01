# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class SensoryTest(models.Model):
    _name = 'sensory.test'
    _description = 'Sensory Test'
    _order = 'test_date desc, id desc'
    
    name = fields.Char(string='Test Number', required=True, copy=False, default='New')
    
    evaluation_id = fields.Many2one(
        'supplier.evaluation',
        string='Evaluation',
        ondelete='cascade',
    )
    
    product_tmpl_id = fields.Many2one(
        'product.template',
        string='Product',
        required=True,
    )
    
    test_date = fields.Date(string='Test Date', required=True, default=fields.Date.today)
    
    tester_ids = fields.Many2many(
        'res.users',
        string='Testers',
    )
    
    # Sensory attributes (1-5 scale)
    appearance_score = fields.Selection([
        ('1', '1 - Poor'),
        ('2', '2 - Fair'),
        ('3', '3 - Good'),
        ('4', '4 - Very Good'),
        ('5', '5 - Excellent'),
    ], string='Appearance')
    
    aroma_score = fields.Selection([
        ('1', '1 - Poor'),
        ('2', '2 - Fair'),
        ('3', '3 - Good'),
        ('4', '4 - Very Good'),
        ('5', '5 - Excellent'),
    ], string='Aroma')
    
    taste_score = fields.Selection([
        ('1', '1 - Poor'),
        ('2', '2 - Fair'),
        ('3', '3 - Good'),
        ('4', '4 - Very Good'),
        ('5', '5 - Excellent'),
    ], string='Taste')
    
    texture_score = fields.Selection([
        ('1', '1 - Poor'),
        ('2', '2 - Fair'),
        ('3', '3 - Good'),
        ('4', '4 - Very Good'),
        ('5', '5 - Excellent'),
    ], string='Texture')
    
    overall_score = fields.Float(
        string='Overall Score',
        compute='_compute_overall_score',
        store=True,
    )
    
    # Step 12: Sample comparison
    compared_with_standard = fields.Boolean(string='Compared with Standard Sample')
    standard_sample_ref = fields.Char(string='Standard Sample Reference')
    
    meets_standard = fields.Boolean(string='Meets Standard')
    
    result = fields.Selection([
        ('pass', 'Pass'),
        ('fail', 'Fail'),
        ('conditional', 'Conditional'),
    ], string='Result', tracking=True)
    
    comments = fields.Html(string='Comments')
    
    @api.depends('appearance_score', 'aroma_score', 'taste_score', 'texture_score')
    def _compute_overall_score(self):
        for test in self:
            scores = [
                int(test.appearance_score) if test.appearance_score else 0,
                int(test.aroma_score) if test.aroma_score else 0,
                int(test.taste_score) if test.taste_score else 0,
                int(test.texture_score) if test.texture_score else 0,
            ]
            test.overall_score = sum(scores) / len([s for s in scores if s > 0]) if any(scores) else 0.0
    
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('sensory.test') or 'New'
        return super().create(vals_list)
