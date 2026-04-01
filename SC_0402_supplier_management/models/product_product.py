# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class ProductProduct(models.Model):
    _inherit = 'product.product'
    
    # ===== McDonald's Fields (Related to Template) =====
    
    # GRI - Related from Template
    x_gri = fields.Char(
        related='product_tmpl_id.x_gri_code',
        string='GRI Code',
        readonly=False,  # Allow editing through variant
        store=True,
    )
    
    x_raw_item_desc = fields.Char(
        related='product_tmpl_id.x_raw_item_desc',
        string='Raw Item Description',
        readonly=False,
        store=True,
    )
    
    # Computed display field (related)
    x_gri_full = fields.Char(
        related='product_tmpl_id.x_gri_full',
        string='GRI - Description',
        store=True,
    )

