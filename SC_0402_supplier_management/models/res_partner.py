# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class ResPartner(models.Model):
    _inherit = 'res.partner'

    # ===== SUPPLIER STATUS =====
    x_supplier_status = fields.Selection([
        ('draft', 'SE / Draft'),
        ('approved', 'Official Vendor')
    ], string='Supplier Status', default='draft', tracking=True)

    x_supplier_code = fields.Char(
        string='Supplier Code',
        readonly=True,
        index=True,
        copy=False,
        help='Auto-generated SE code (e.g., SE-0001)'
    )
    
    # ===== SUPPLIED PRODUCTS (From SupplierInfo) =====
    
    supplied_product_ids = fields.Many2many(
        'product.template',
        string='Supplied Products',
        compute='_compute_supplied_products',
        store=False,
        help='Products this vendor supplies (from Purchase tab)'
    )
    
    supplied_product_count = fields.Integer(
        string='# Products',
        compute='_compute_supplied_products',
    )
    
    supplied_product_info = fields.Char(
        string='Products & Prices',
        compute='_compute_supplied_product_info',
        help='Summary of products and prices for quick reference',
    )
    
    # ===== EVALUATION LINK =====
    
    evaluation_ids = fields.One2many(
        'supplier.evaluation',
        'partner_id',
        string='Evaluations',
    )
    
    evaluation_count = fields.Integer(
        string='# Evaluations',
        compute='_compute_evaluation_count',
    )
    
    current_evaluation_id = fields.Many2one(
        'supplier.evaluation',
        string='Current Evaluation',
        compute='_compute_current_evaluation',
        store=False,
        help='The latest active evaluation for this vendor',
    )
    
    # ===== COMPUTE METHODS =====
    
    @api.depends_context('lang')
    def _compute_supplied_products(self):
        """Get all products this vendor supplies from product.supplierinfo"""
        for partner in self:
            supplierinfos = self.env['product.supplierinfo'].search([
                ('partner_id', '=', partner.id)
            ])
            product_tmpls = supplierinfos.mapped('product_tmpl_id')
            partner.supplied_product_ids = product_tmpls
            partner.supplied_product_count = len(product_tmpls)
    
    @api.depends_context('lang')
    def _compute_supplied_product_info(self):
        """Generate summary text: 'Product1 (50k), Product2 (30k)' """
        for partner in self:
            supplierinfos = self.env['product.supplierinfo'].search([
                ('partner_id', '=', partner.id)
            ])
            if supplierinfos:
                info_parts = []
                for info in supplierinfos[:5]:  # Max 5 to avoid overflow
                    product_name = info.product_tmpl_id.name or 'N/A'
                    price = f"{info.price:,.0f}" if info.price else '0'
                    info_parts.append(f"{product_name} ({price})")
                partner.supplied_product_info = ', '.join(info_parts)
                if len(supplierinfos) > 5:
                    partner.supplied_product_info += f'... (+{len(supplierinfos) - 5})'
            else:
                partner.supplied_product_info = ''
    
    def _compute_evaluation_count(self):
        for partner in self:
            partner.evaluation_count = len(partner.evaluation_ids)
    
    @api.depends('evaluation_ids', 'evaluation_ids.state')
    def _compute_current_evaluation(self):
        """Get the latest non-rejected evaluation"""
        for partner in self:
            eval_record = self.env['supplier.evaluation'].search([
                ('partner_id', '=', partner.id),
                ('state', 'not in', ['approved', 'rejected_sourcing', 'rejected_qa'])
            ], order='create_date desc', limit=1)
            partner.current_evaluation_id = eval_record
    
    # ===== VALIDATION =====
    
    @api.constrains('name', 'vat', 'email', 'x_supplier_status', 'supplier_rank')
    def _check_draft_vendor_fields(self):
        """Validate required fields for draft vendors"""
        for partner in self:
            # Only check if this is a draft vendor
            if partner.x_supplier_status == 'draft' and partner.supplier_rank > 0:
                if not partner.vat:
                    raise ValidationError(_("Tax ID (VAT) is required for draft vendors"))
                if not partner.email:
                    raise ValidationError(_("Email is required for draft vendors"))
                if not partner.name:
                    raise ValidationError(_("Name is required for draft vendors"))

    # ===== ACTIONS =====
    
    def action_approve_vendor(self):
        """Approve draft vendor and generate SE code"""
        for partner in self:
            if not partner.x_supplier_code:
                # Generate SE code using sequence
                partner.x_supplier_code = self.env['ir.sequence'].next_by_code('res.partner.supplier.code') or 'SE-NEW'
            partner.x_supplier_status = 'approved'
            partner.supplier_rank = 1  # Mark as vendor
    
    def action_create_evaluation(self):
        """Create a new Supplier Evaluation for this vendor"""
        self.ensure_one()
        
        # Check if there's already an active evaluation
        active_eval = self.env['supplier.evaluation'].search([
            ('partner_id', '=', self.id),
            ('state', 'not in', ['approved', 'rejected_sourcing', 'rejected_qa'])
        ], limit=1)
        
        if active_eval:
            # Open existing evaluation
            return {
                'name': _('Supplier Evaluation'),
                'type': 'ir.actions.act_window',
                'res_model': 'supplier.evaluation',
                'res_id': active_eval.id,
                'view_mode': 'form',
                'target': 'current',
            }
        
        # Get supplied products
        supplierinfos = self.env['product.supplierinfo'].search([
            ('partner_id', '=', self.id)
        ])
        product_tmpls = supplierinfos.mapped('product_tmpl_id')
        
        # Auto-fill product if only one
        default_product = product_tmpls[0].id if len(product_tmpls) == 1 else False
        
        # Create new evaluation
        return {
            'name': _('Create Supplier Evaluation'),
            'type': 'ir.actions.act_window',
            'res_model': 'supplier.evaluation',
            'view_mode': 'form',
            'target': 'current',
            'context': {
                'default_partner_id': self.id,
                'default_product_tmpl_id': default_product,
                'default_is_new_supplier': self.x_supplier_status == 'draft',
            },
        }
    
    def action_view_evaluations(self):
        """View all evaluations for this vendor"""
        self.ensure_one()
        return {
            'name': _('Evaluations'),
            'type': 'ir.actions.act_window',
            'res_model': 'supplier.evaluation',
            'view_mode': 'list,form',
            'domain': [('partner_id', '=', self.id)],
            'context': {'default_partner_id': self.id},
        }
    
    def action_view_supplied_products(self):
        """View all products this vendor supplies"""
        self.ensure_one()
        return {
            'name': _('Supplied Products'),
            'type': 'ir.actions.act_window',
            'res_model': 'product.template',
            'view_mode': 'list,form',
            'domain': [('id', 'in', self.supplied_product_ids.ids)],
        }
