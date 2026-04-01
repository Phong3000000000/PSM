# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class LabTest(models.Model):
    _name = 'lab.test'
    _description = 'Lab Test'
    _inherit = ['mail.thread', 'mail.activity.mixin']
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
    
    test_type = fields.Selection([
        ('microbiological', 'Microbiological'),
        ('chemical', 'Chemical'),
        ('physical', 'Physical'),
        ('nutritional', 'Nutritional'),
        ('other', 'Other'),
    ], string='Test Type', required=True)
    
    sample_batch_number = fields.Char(string='Sample Batch Number')
    
    # Integration with quality_control module
    quality_check_ids = fields.Many2many(
        'quality.check',
        string='Quality Checks',
    )
    
    # Test results
    result = fields.Selection([
        ('pass', 'Pass'),
        ('fail', 'Fail'),
        ('pending', 'Pending'),
    ], string='Result', default='pending', tracking=True)
    
    # Documents: COA, Spec, Test Reports
    coa_document_id = fields.Many2one(
        'documents.document',
        string='COA (Certificate of Analysis)',
    )
    
    spec_document_id = fields.Many2one(
        'documents.document',
        string='Specification Document',
    )
    
    document_ids = fields.Many2many(
        'documents.document',
        string='Test Reports',
    )
    
    findings = fields.Html(string='Test Findings')
    note = fields.Html(string='Notes')
    
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('lab.test') or 'New'
        return super().create(vals_list)
