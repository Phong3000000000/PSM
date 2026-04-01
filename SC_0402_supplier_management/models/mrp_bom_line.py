# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class MrpBomLine(models.Model):
    _inherit = 'mrp.bom.line'
    
    # ===== GRI & Description (from product) =====
    
    gri = fields.Char(
        related='product_id.product_tmpl_id.x_gri_code',
        string='GRI',
        readonly=True,
        store=True,
    )
    
    raw_item_desc = fields.Char(
        related='product_id.product_tmpl_id.x_raw_item_desc',
        string='Raw Item Description',
        readonly=True,
        store=True,
    )
    
    gri_full = fields.Char(
        string='GRI - Description',
        compute='_compute_gri_full',
        help='Column1: GRI-Description',
    )
    
    # ===== Quantity Display =====
    
    qty_unit_display = fields.Char(
        string='Quantity x Unit',
        compute='_compute_qty_unit_display',
        help='Column2: Formatted quantity display',
    )
    
    # ===== CONVERSION RATE =====
    
    x_conversion_rate = fields.Float(
        string='Conversion Rate',
        default=1.0,
        digits=(12, 6),
        help='Conversion rate from stock UoM to BOM UoM.',
    )
    
    conversion_rate = fields.Float(
        string='Conv. Rate',
        compute='_compute_conversion_rate',
        inverse='_inverse_conversion_rate',
        store=True,
        digits=(12, 6),
        help='UoM conversion rate',
    )
    
    # ===== COST FIELDS =====
    
    inventory_price = fields.Float(
        related='product_id.standard_price',
        string='Unit Price',
        readonly=True,
        digits='Product Price',
    )
    
    total_cost = fields.Monetary(
        string='Total Cost',
        compute='_compute_total_cost',
        store=True,
        currency_field='currency_id',
    )
    
    currency_id = fields.Many2one(
        'res.currency',
        related='company_id.currency_id',
        string='Currency',
        readonly=True,
    )
    
    # ===== NEW: SUPPLIERINFO-BASED VENDOR FIELDS =====
    
    # Helper field for domain filtering
    product_tmpl_id = fields.Many2one(
        related='product_id.product_tmpl_id',
        string='Product Template',
        readonly=True,
        store=True,
    )
    
    # All available suppliers for this product (computed)
    valid_supplierinfo_ids = fields.Many2many(
        'product.supplierinfo',
        string='Available Vendors',
        compute='_compute_valid_supplierinfo',
        help='All vendors that supply this product',
    )
    
    # Selected vendor (Sourcing picks this) - Only show APPROVED vendors
    selected_supplierinfo_id = fields.Many2one(
        'product.supplierinfo',
        string='Selected Vendor',
        domain="[('product_tmpl_id', '=', product_tmpl_id), ('partner_id.x_supplier_status', '=', 'approved')]",
        help='Vendor selected by Sourcing for this BOM line (only approved vendors shown)',
    )
    
    # Selected vendor's partner (for display)
    selected_vendor_id = fields.Many2one(
        related='selected_supplierinfo_id.partner_id',
        string='Approved Vendor',
        readonly=True,
        store=True,
    )
    
    # Price from selected vendor
    price_unit = fields.Monetary(
        string='Cost',
        related='selected_supplierinfo_id.price',
        readonly=True,
        store=True,
        currency_field='currency_id',
        help='Price from selected vendor',
    )
    
    # WRIN display (Now related to SupplierInfo)
    wrin = fields.Char(
        related='selected_supplierinfo_id.x_wrin',
        string='WRIN',
        readonly=True,
        help='Warehouse Receipt ID - generated immediately upon vendor selection',
    )
    
    case_pack = fields.Integer(
        string='Case Pack',
        compute='_compute_supplier_info',
    )
    
    lead_time_days = fields.Integer(
        string='Lead Time (Days)',
        compute='_compute_supplier_info',
    )
    
    # ===== WRITE METHOD OVERRIDE =====

    def write(self, vals):
        """
        Trigger WRIN generation when Sourcing selects a vendor.
        """
        res = super().write(vals)
        if 'selected_supplierinfo_id' in vals:
            for line in self:
                if line.selected_supplierinfo_id:
                    line._generate_material_wrin(line.selected_supplierinfo_id)
        return res

    def _generate_material_wrin(self, info):
        """
        Generate WRIN immediately: GRI-SUP (e.g., GRI0052-SUP001)
        Save it to product.supplierinfo so it persists.
        Only generate if vendor is APPROVED.
        """
        vendor = info.partner_id
        product = info.product_tmpl_id
        
        # CRITICAL: Only generate WRIN if vendor is APPROVED
        if vendor.x_supplier_status != 'approved':
            return  # Skip - vendor not approved yet
        
        # 1. Ensure Vendor has Supplier Code (SUP)
        if not vendor.x_supplier_code:
            vendor.action_approve_vendor()
            
        # 2. Ensure Product has GRI Code
        if not product.x_gri_code:
            product.x_gri_code = self.env['ir.sequence'].next_by_code('product.gri.code') or f"GRI{product.id}"

        # 3. Generate WRIN
        gri = product.x_gri_code
        sup_code = vendor.x_supplier_code
        new_wrin = f"{gri}-{sup_code}"
        
        # 4. Save to SupplierInfo (Master Data)
        # Avoid unnecessary writes if already set correctly
        if info.x_wrin != new_wrin:
            info.write({'x_wrin': new_wrin})

    def action_create_line_contract(self):
        """
        Open Purchase Agreement form to create contract for this BOM line.
        Called from button in BOM line list (only when BOM is approved).
        """
        self.ensure_one()
        
        if not self.selected_supplierinfo_id:
            from odoo.exceptions import UserError
            raise UserError(_("Vui lòng chọn Vendor trước khi tạo Contract."))
        
        vendor = self.selected_vendor_id
        product = self.product_id
        
        # Open Purchase Agreement form with pre-filled values
        return {
            'type': 'ir.actions.act_window',
            'name': 'Tạo Purchase Agreement',
            'res_model': 'purchase.requisition',
            'view_mode': 'form',
            'target': 'current',
            'context': {
                'default_vendor_id': vendor.id,
                'default_line_ids': [(0, 0, {
                    'product_id': product.id,
                    'product_qty': self.product_qty,
                    'product_uom_id': self.product_uom_id.id,
                    'price_unit': self.price_unit or 0,
                })],
            },
        }

    # ===== COMPUTE METHODS =====
    
    @api.depends('product_tmpl_id')
    def _compute_valid_supplierinfo(self):
        """Compute all available vendors for this product from product.supplierinfo"""
        for line in self:
            if line.product_tmpl_id:
                supplierinfos = self.env['product.supplierinfo'].search([
                    ('product_tmpl_id', '=', line.product_tmpl_id.id)
                ])
                line.valid_supplierinfo_ids = supplierinfos
            else:
                line.valid_supplierinfo_ids = False
    
    # _compute_wrin_display removed as WRIN is now a related field
    
    @api.depends('gri', 'raw_item_desc')
    
    @api.depends('gri', 'raw_item_desc')
    def _compute_gri_full(self):
        for line in self:
            if line.gri and line.raw_item_desc:
                line.gri_full = f"{line.gri}-{line.raw_item_desc}"
            elif line.gri:
                line.gri_full = line.gri
            else:
                line.gri_full = ''
    
    @api.depends('product_qty', 'product_uom_id')
    def _compute_qty_unit_display(self):
        for line in self:
            if line.product_qty and line.product_uom_id:
                line.qty_unit_display = f"{line.product_qty} x {line.product_uom_id.name}"
            else:
                line.qty_unit_display = ''
    
    @api.depends('product_uom_id', 'product_id.uom_id', 'x_conversion_rate')
    def _compute_conversion_rate(self):
        for line in self:
            # Priority 1: Use manual conversion rate if set
            if line.x_conversion_rate and line.x_conversion_rate != 1.0:
                line.conversion_rate = line.x_conversion_rate
            # Priority 2: Calculate from UoM
            elif line.product_uom_id and line.product_id.uom_id:
                if line.product_uom_id == line.product_id.uom_id:
                    line.conversion_rate = 1.0
                else:
                    try:
                        line.conversion_rate = line.product_uom_id._compute_quantity(
                            1.0, 
                            line.product_id.uom_id,
                            round=False
                        )
                    except Exception:
                        line.conversion_rate = 1.0
            else:
                line.conversion_rate = 1.0
    
    def _inverse_conversion_rate(self):
        """Allow manual override of conversion rate"""
        for line in self:
            line.x_conversion_rate = line.conversion_rate
    
    @api.depends('product_qty', 'product_id.standard_price')
    def _compute_total_cost(self):
        for line in self:
            line.total_cost = line.product_qty * line.product_id.standard_price
    
    @api.depends('selected_supplierinfo_id')
    def _compute_supplier_info(self):
        for line in self:
            if line.selected_supplierinfo_id:
                line.case_pack = line.selected_supplierinfo_id.x_case_pack or 0
                line.lead_time_days = line.selected_supplierinfo_id.x_lead_time_days or 0
            else:
                line.case_pack = 0
                line.lead_time_days = 0
