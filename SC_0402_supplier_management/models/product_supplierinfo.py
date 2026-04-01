# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class ProductSupplierinfo(models.Model):
    _inherit = 'product.supplierinfo'
    
    @api.model_create_multi
    def create(self, vals_list):
        """Auto-init vendor fields when adding SupplierInfo"""
        records = super().create(vals_list)
        for record in records:
            partner = record.partner_id
            if partner:
                # Auto set supplier_rank so it shows in Vendor menus
                vals_to_update = {}
                if partner.supplier_rank == 0:
                    vals_to_update['supplier_rank'] = 1
                # Set draft status if not already set
                if not partner.x_supplier_status:
                    vals_to_update['x_supplier_status'] = 'draft'
                if vals_to_update:
                    partner.sudo().write(vals_to_update)
        return records
    
    def name_get(self):
        """Display vendor name with price in M2M tags for easy comparison"""
        result = []
        for record in self:
            name = f"{record.partner_id.name} ({record.price:,.0f})"
            result.append((record.id, name))
        return result
    
    # ===== McDonald's Supplier-Specific Fields =====
    
    # WRIN - Warehouse Receipt ID Number (GRI + Supplier)
    x_wrin = fields.Char(
        string='WRIN Code',
        help='Warehouse Receipt ID Number - supplier specific code (mã riêng của NCC)',
        index=True,
        copy=False,
    )
    
    x_case_pack = fields.Integer(
        string='Case Pack',
        help='Number of units per case from this supplier (số lượng/thùng)',
        default=1,
    )
    
    x_lead_time_days = fields.Integer(
        string='Lead Time (Days)',
        help='Supplier lead time in days (thời gian giao hàng)',
        default=0,
    )
    
    # Override price field to add currency
    price = fields.Monetary(
        currency_field='currency_id',
        help='Supplier unit price',
    )
    
    currency_id = fields.Many2one(
        related='company_id.currency_id',
        readonly=True,
    )
