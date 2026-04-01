# -*- coding: utf-8 -*-

from odoo import api, fields, models, _

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    # Raw Material checkbox
    x_is_raw_material = fields.Boolean(
        string='Is Raw Material',
        default=False,
        help='Check this for raw materials used in manufacturing'
    )
    
    # GRI Code for raw materials (EDITABLE - auto-generate if empty)
    x_gri_code = fields.Char(
        string='GRI Code',
        index=True,
        copy=False,
        help='Global Raw Item code. If left empty, will be auto-generated.'
    )
    
    # Raw Item Description (short desc, e.g., "BIC TRAY LINER (PE BBQ Liner)")
    x_raw_item_desc = fields.Char(
        string='Raw Item Description',
        help='Short description of raw material (e.g., BIC TRAY LINER)',
    )
    
    # Computed: GRI - Description
    x_gri_full = fields.Char(
        string='GRI - Description',
        compute='_compute_gri_full',
        store=True,
        help='Format: GRI-Description',
    )
    
    # ===== REMOVED: PIF IMPLEMENTATION (Handled in mrp.bom) =====
    # x_pif_implementation_state removed
    
    # Finished Good WRIN (Internal Reference)
    # default_code is already in Odoo, we just use it as WRIN
    
    @api.depends('x_gri_code', 'x_raw_item_desc')
    def _compute_gri_full(self):
        for product in self:
            if product.x_gri_code and product.x_raw_item_desc:
                product.x_gri_full = f"{product.x_gri_code}-{product.x_raw_item_desc}"
            elif product.x_gri_code:
                product.x_gri_full = product.x_gri_code
            else:
                product.x_gri_full = ''

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('x_is_raw_material'):
                # LOGIC CHUẨN: Raw Material = Mua vào, Không bán
                vals['sale_ok'] = False
                vals['purchase_ok'] = True
                vals['type'] = 'consu'  # Goods (storable product in Odoo 19)
                # Sinh GRI chỉ khi user không nhập
                if not vals.get('x_gri_code'):
                    vals['x_gri_code'] = self.env['ir.sequence'].next_by_code('product.gri.code') or 'NEW'
        return super().create(vals_list)

    def write(self, vals):
        # Nếu user tick vào checkbox sau khi tạo, cập nhật lại thuộc tính
        if vals.get('x_is_raw_material'):
            vals['sale_ok'] = False
            vals['purchase_ok'] = True
            # Sinh GRI nếu chưa có (và user không nhập)
            for product in self:
                if not product.x_gri_code and not vals.get('x_gri_code'):
                    vals['x_gri_code'] = self.env['ir.sequence'].next_by_code('product.gri.code') or 'NEW'
        return super().write(vals)

    # Actions removed: action_menu_approve_pif, action_create_finished_wrin
    # Workflow is now managed in mrp.bom model


