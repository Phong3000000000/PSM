# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class SupplierCertificate(models.Model):
    _name = 'supplier.certificate'
    _description = 'Supplier Certificate'
    _order = 'expiry_date desc, id desc'
    
    name = fields.Char(string='Certificate Name', required=True)
    
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
    
    certificate_type = fields.Selection([
        ('haccp', 'HACCP'),
        ('iso_9001', 'ISO 9001'),
        ('iso_22000', 'ISO 22000'),
        ('halal', 'Halal'),
        ('brc', 'BRC'),
        ('gmp', 'GMP'),
        ('fda', 'FDA'),
        ('other', 'Other'),
    ], string='Type', required=True)
    
    certificate_number = fields.Char(string='Certificate Number')
    
    issue_date = fields.Date(string='Issue Date')
    
    expiry_date = fields.Date(string='Expiry Date')
    
    is_expired = fields.Boolean(
        string='Expired',
        compute='_compute_is_expired',
        store=True,
    )
    
    issuing_authority = fields.Char(string='Issuing Authority')
    
    # Documents module integration
    document_ids = fields.Many2many(
        'documents.document',
        string='Certificate Files',
    )
    
    note = fields.Text(string='Notes')
    
    @api.depends('expiry_date')
    def _compute_is_expired(self):
        today = fields.Date.today()
        for cert in self:
            cert.is_expired = cert.expiry_date and cert.expiry_date < today
