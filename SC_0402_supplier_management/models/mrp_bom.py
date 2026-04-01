# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class MrpBom(models.Model):
    """
    Extend mrp.bom to support McDonald's PIF workflow
    Instead of creating separate product.pif model, we use standard BOM
    """
    _inherit = 'mrp.bom'
    
    # ===== PIF WORKFLOW FIELDS =====
    
    # Mark this BOM as a PIF (Product Information Form)
    # Default is True for finished products (not raw materials)
    is_pif = fields.Boolean(
        string='Is PIF',
        default=True,
        help='This BOM is a Product Information Form requiring approval',
    )
    
    @api.onchange('product_tmpl_id')
    def _onchange_product_tmpl_id_pif(self):
        """Auto-set is_pif based on product type"""
        if self.product_tmpl_id:
            # If product is a raw material, this is NOT a PIF
            if self.product_tmpl_id.x_is_raw_material:
                self.is_pif = False
            else:
                self.is_pif = True
    
    pif_state = fields.Selection([
        ('draft', 'Draft'),                         # Menu tạo
        ('sourcing', 'Sourcing Review'),            # Sourcing kiếm NCC & giá
        ('menu_final', 'Menu Final Confirm'),       # B15: Menu xác nhận final → tạo PIF
        ('menu_head', 'Menu Head Approval'),        # Menu Head duyệt
        ('approved', 'Approved'),                   # Final state
        ('rejected', 'Rejected'),
    ], string='PIF Status', default='draft', tracking=True)
    
    # Step 1: Menu inputs
    program_name = fields.Char(
        string='Program Name',
        help='Marketing program (e.g., TinyTAN Limited)',
    )
    
    launch_date = fields.Date(string='Launch Date')
    
    forecast_volume = fields.Integer(string='Forecast Volume')
    
    # Step 14: Link to supplier evaluation
    supplier_evaluation_id = fields.Many2one(
        'supplier.evaluation',
        string='Supplier Evaluation',
        domain="[('state', '=', 'approved')]",
    )
    
    # Approval tracking
    menu_approved_by = fields.Many2one('res.users', string='Menu Approved By', readonly=True)
    menu_approved_date = fields.Datetime(string='Menu Approved Date', readonly=True)
    
    sourcing_approved_by = fields.Many2one('res.users', string='Sourcing Approved By', readonly=True)
    sourcing_approved_date = fields.Datetime(string='Sourcing Approved Date', readonly=True)
    
    line_manager_approved_by = fields.Many2one('res.users', string='Line Manager Approved By', readonly=True)
    line_manager_approved_date = fields.Datetime(string='Line Manager Approved Date', readonly=True)
    
    ceo_approved_by = fields.Many2one('res.users', string='CEO Approved By', readonly=True)
    ceo_approved_date = fields.Datetime(string='CEO Approved Date', readonly=True)
    
    # WRIN creation status
    wrin_created = fields.Boolean(string='WRIN Created', default=False, copy=False)
    
    # Link to PIF Implementation (RSG_0801)
    pif_object_id = fields.Many2one(
        'pif.object',
        string='PIF Implementation',
        readonly=True,
        copy=False,
        help='PIF Implementation record created from B15',
    )
    pif_object_count = fields.Integer(compute='_compute_pif_object_count', string='PIF Count')
    
    def _compute_pif_object_count(self):
        for rec in self:
            rec.pif_object_count = 1 if rec.pif_object_id else 0
    
    def action_open_pif_implementation(self):
        """Smart button to open linked PIF Implementation."""
        self.ensure_one()
        if self.pif_object_id:
            return {
                'type': 'ir.actions.act_window',
                'name': 'PIF Implementation',
                'res_model': 'pif.object',
                'res_id': self.pif_object_id.id,
                'view_mode': 'form',
                'target': 'current',
            }
    
    # Field containing Finished Good WRIN (Saved to Product Template)
    finished_wrin = fields.Char(related='product_tmpl_id.default_code', string='WRIN Thành phẩm', readonly=True)
    
    # ===== B16-B17: PURCHASE REQUISITION & CONTRACT =====
    
    purchase_requisition_id = fields.Many2one(
        'purchase.requisition',
        string='Purchase Requisition',
        readonly=True,
        copy=False,
        help='PR created from this PIF (B16)',
    )
    
    purchase_agreement_id = fields.Many2one(
        'purchase.requisition',
        string='Purchase Agreement/Contract',
        readonly=True,
        copy=False,
        domain="[('type_id.exclusive', '=', 'exclusive')]",
        help='Blanket Order/Contract created from this PIF (B16)',
    )
    
    pr_created = fields.Boolean(string='PR Created', default=False, copy=False)
    contract_created = fields.Boolean(string='Contract Created', default=False, copy=False)
    
    # ===== WORKFLOW METHODS =====
    
    def action_submit_for_approval(self):
        """Menu submits PIF → goes directly to Sourcing."""
        self.ensure_one()
        if not self.is_pif:
            raise UserError(_('This BOM is not marked as a PIF.'))
        self.write({
            'pif_state': 'sourcing',
            'menu_approved_by': self.env.user.id,
            'menu_approved_date': fields.Datetime.now(),
        })
        self.message_post(
            body="Menu đã tạo PIF và chuyển cho Sourcing kiếm NCC.",
            message_type='notification',
        )
        return True
    
    def action_approve_sourcing(self):
        """
        B14: Sourcing approves after updating NCC & prices.
        
        Validation:
        - All BOM lines must have selected_supplierinfo_id (vendor đã được chọn)
        """
        self.ensure_one()
        
        # Validation: Check all lines have vendor selected
        lines_without_vendor = self.bom_line_ids.filtered(
            lambda l: not l.selected_supplierinfo_id
        )
        if lines_without_vendor:
            products = ', '.join(lines_without_vendor.mapped('product_id.name'))
            raise UserError(_(
                'Vui lòng chọn Vendor cho tất cả nguyên liệu trước khi hoàn tất.\n\n'
                'Các nguyên liệu chưa có Vendor:\n%s'
            ) % products)
        
        self.write({
            'pif_state': 'menu_final',  # B15: Go to Menu Final Confirm
            'sourcing_approved_by': self.env.user.id,
            'sourcing_approved_date': fields.Datetime.now(),
        })
        return True
    
    def action_approve_menu_final(self):
        """
        B15: Menu xác nhận lại PIF bản final sau khi Sourcing update.
        
        Validation:
        - All BOM lines must have selected_supplierinfo_id (vendor đã được chọn bởi Sourcing)
        
        This action:
        1. Creates a pif.object record linked to this BOM (for PIF Implementation workflow)
        2. Transitions BOM PIF state to menu_head for Menu Head approval
        
        The pif.object will go through its own workflow:
        RSG → IT → Master Data → Lab Test → Pilot → Approved
        When pif.object is approved, it will generate the Finished Good WRIN.
        """
        self.ensure_one()
        
        # Validation: Check all lines have vendor selected by Sourcing
        lines_without_vendor = self.bom_line_ids.filtered(
            lambda l: not l.selected_supplierinfo_id
        )
        if lines_without_vendor:
            products = ', '.join(lines_without_vendor.mapped('product_id.name'))
            raise UserError(_(
                'Không thể chuyển sang Menu Head Approval.\n\n'
                'Sourcing chưa chọn Vendor cho các nguyên liệu sau:\n%s\n\n'
                'Vui lòng quay lại bước Sourcing để chọn Vendor.'
            ) % products)
        
        # Create pif.object for PIF Implementation workflow
        pif_object = self._create_pif_object()
        
        self.write({
            'pif_state': 'menu_head',  # Chuyển sang Menu Head duyệt
            'pif_object_id': pif_object.id,  # Link PIF
            'menu_approved_by': self.env.user.id,
            'menu_approved_date': fields.Datetime.now(),
        })
        
        self.message_post(
            body=f"B15: Đã tạo PIF Implementation {pif_object.name} để triển khai sản phẩm.",
            message_type='notification',
        )
        
        return True
    
    def action_approve_menu_head(self):
        """
        Menu Head approves - FINAL APPROVAL for BOM.
        
        Validation:
        - All BOM lines must have selected_supplierinfo_id (vendor đã được chọn)
        - All BOM lines must have price_unit > 0 (có giá)
        - WRIN must be generated for all lines (via selected_supplierinfo_id.x_wrin)
        """
        self.ensure_one()
        
        # Validation 1: Check all lines have vendor selected
        lines_without_vendor = self.bom_line_ids.filtered(
            lambda l: not l.selected_supplierinfo_id
        )
        if lines_without_vendor:
            products = ', '.join(lines_without_vendor.mapped('product_id.name'))
            raise UserError(_(
                'Không thể phê duyệt BOM.\n\n'
                'Các nguyên liệu chưa có Vendor được chọn:\n%s'
            ) % products)
        
        # Validation 2: Check all lines have price
        lines_without_price = self.bom_line_ids.filtered(
            lambda l: l.selected_supplierinfo_id and not l.price_unit
        )
        if lines_without_price:
            products = ', '.join(lines_without_price.mapped('product_id.name'))
            raise UserError(_(
                'Không thể phê duyệt BOM.\n\n'
                'Các nguyên liệu chưa có Giá (Cost):\n%s\n\n'
                'Vui lòng cập nhật giá trong Product > Vendors trước khi duyệt.'
            ) % products)
        
        # Validation 3: Check WRIN generated (optional - only warn if missing)
        lines_without_wrin = self.bom_line_ids.filtered(
            lambda l: l.selected_supplierinfo_id and not l.wrin
        )
        if lines_without_wrin:
            products = ', '.join(lines_without_wrin.mapped('product_id.name'))
            raise UserError(_(
                'Không thể phê duyệt BOM.\n\n'
                'Các nguyên liệu chưa có WRIN:\n%s\n\n'
                'WRIN sẽ tự động tạo khi Vendor được approve. '
                'Vui lòng kiểm tra Vendor đã được duyệt chưa.'
            ) % products)
        
        self.write({
            'pif_state': 'approved',
        })
        # Generate Master Data (Finished Good WRIN)
        self._generate_master_data()
        self.message_post(
            body="Menu Head đã duyệt - BOM đã được phê duyệt.",
            message_type='notification',
        )
        return True
    
    def _create_pif_object(self):
        """
        Create pif.object record from this BOM for PIF Implementation workflow.
        Input: BOM (this record)
        Output: pif.object linked to this BOM
        """
        self.ensure_one()
        
        # Get product variant from template
        product = self.product_tmpl_id.product_variant_id
        
        pif_object = self.env['pif.object'].sudo().create({
            'pif_bom_id': self.id,
            'pif_product_id': product.id if product else False,
            'pif_request_type': 'menu',
            'formula_description': f"BOM: {self.display_name}",
            'supplier_info': ', '.join(
                line.selected_vendor_id.name for line in self.bom_line_ids 
                if line.selected_vendor_id
            ),
        })
        
        return pif_object
    
    def action_reject(self):
        """Reject PIF"""
        self.ensure_one()
        self.write({'pif_state': 'rejected'})
        return True
    
    # ===== B21-B22: VENDOR OPTIMIZATION & WRIN CHANGE =====
    
    def action_propose_vendor_change(self):
        """
        B21: Sourcing proposes vendor optimization.
        B22: When vendor changes, reset PIF for re-approval.
        
        This resets PIF state to 'sourcing' so Sourcing can:
        1. Change the selected vendor
        2. New WRIN will be generated
        3. PIF must be re-approved by LM and CEO
        """
        self.ensure_one()
        if self.pif_state != 'approved':
            return True  # Only works on approved PIFs
        
        # Clear selected vendors on all lines (allow Sourcing to re-select)
        for line in self.bom_line_ids:
            # Store old WRIN for history (optionally)
            old_wrin = line.wrin
            if old_wrin:
                # Log the change
                self.message_post(
                    body=f"Đề xuất thay đổi NCC: WRIN cũ của {line.product_id.name} = {old_wrin}",
                    message_type='notification',
                )
        
        # Reset PIF state to sourcing for re-approval
        self.write({
            'pif_state': 'sourcing',
            'wrin_created': False,  # Reset WRIN status
            # Clear old approval info (optional - keep for audit trail)
            # 'line_manager_approved_by': False,
            # 'ceo_approved_by': False,
        })
        
        self.message_post(
            body="B21: Đề xuất tối ưu NCC - PIF đã được reset để đánh giá lại.",
            message_type='notification',
        )
        return True
    
    # ===== MASTER DATA GENERATION =====
    
    def _generate_master_data(self):
        """
        Phase 4: Generate Master Data after CEO approval.
        
        1. Generate WRIN for Finished Good (Menu Item)
        2. Assign it to product internal reference (default_code)
        
        Note: Material WRINs are now generated immediately during Sourcing step.
        """
        self.ensure_one()
        
        # Generator code for Product (Parent)
        # Use existing code or generate new one if missing
        if not self.product_tmpl_id.default_code:
             # Logic to generate Finished Good WRIN (e.g. P-2024-001)
             # Using Odoo default sequence for product - or 'NEW-FG' fallback
             new_code = self.env['ir.sequence'].next_by_code('product.product') or 'NEW-FG'
             self.product_tmpl_id.write({'default_code': new_code})
        
        # Update product standard_price based on BOM cost
        # (Optional: can also be done by computing BOM cost)
        total_cost = sum(line.total_cost for line in self.bom_line_ids)
        if total_cost > 0:
            self.product_tmpl_id.write({'standard_price': total_cost})
        
        # Mark WRIN as created
        self.write({'wrin_created': True})

    # ===== B16-B17: PURCHASE REQUISITION & CONTRACT CREATION =====
    
    def action_create_purchase_requisition(self):
        """
        B16: Sourcing creates Purchase Requisition from approved PIF.
        
        - Creates PR with all BOM lines that have selected vendors
        - Pre-fills vendor, product, quantity, and price from BOM
        - Ready for SC_0401 integration
        """
        self.ensure_one()
        if self.pif_state != 'approved':
            raise UserError(_('PIF must be approved before creating PR.'))
        
        if self.pr_created:
            raise UserError(_('PR đã được tạo cho PIF này.'))
        
        # Collect lines with selected vendors
        pr_lines = []
        for line in self.bom_line_ids:
            if line.selected_supplierinfo_id and line.selected_vendor_id:
                pr_lines.append((0, 0, {
                    'product_id': line.product_id.id,
                    'product_qty': line.product_qty,
                    'product_uom_id': line.product_uom_id.id,
                    'price_unit': line.price_unit or 0.0,
                }))
        
        if not pr_lines:
            raise UserError(_('Không có nguyên liệu nào được chọn NCC.'))
        
        # Create Purchase Requisition
        pr = self.env['purchase.requisition'].create({
            'origin': f"PIF/{self.code or self.id}",
            'line_ids': pr_lines,
            # type_id: standard = PR, exclusive = Blanket Order
        })
        
        self.write({
            'purchase_requisition_id': pr.id,
            'pr_created': True,
        })
        
        self.message_post(
            body=f"B16: Đã tạo Purchase Requisition {pr.name}",
            message_type='notification',
        )
        
        # Return action to open the PR
        return {
            'type': 'ir.actions.act_window',
            'name': 'Purchase Requisition',
            'res_model': 'purchase.requisition',
            'res_id': pr.id,
            'view_mode': 'form',
            'target': 'current',
        }
    
    def action_create_contract(self):
        """
        B16: Sourcing creates Purchase Agreement/Contract (Blanket Order) from approved PIF.
        
        - Creates Blanket Order for long-term vendor agreements
        - Links vendor from selected_supplierinfo_id
        - Ready for SC_0401 integration
        """
        self.ensure_one()
        if self.pif_state != 'approved':
            raise UserError(_('PIF must be approved before creating Contract.'))
        
        if self.contract_created:
            raise UserError(_('Contract đã được tạo cho PIF này.'))
        
        # Get the exclusive (Blanket Order) type
        blanket_type = self.env['purchase.requisition.type'].search(
            [('exclusive', '=', 'exclusive')], limit=1
        )
        
        # Collect lines with selected vendors
        contract_lines = []
        vendors = set()
        for line in self.bom_line_ids:
            if line.selected_supplierinfo_id and line.selected_vendor_id:
                vendors.add(line.selected_vendor_id.id)
                contract_lines.append((0, 0, {
                    'product_id': line.product_id.id,
                    'product_qty': line.product_qty,
                    'product_uom_id': line.product_uom_id.id,
                    'price_unit': line.price_unit or 0.0,
                }))
        
        if not contract_lines:
            raise UserError(_('Không có nguyên liệu nào được chọn NCC.'))
        
        # Pick first vendor as main vendor (or can be customized)
        main_vendor_id = list(vendors)[0] if vendors else False
        
        # Create Blanket Order (Contract)
        contract = self.env['purchase.requisition'].create({
            'origin': f"PIF/{self.code or self.id}",
            'type_id': blanket_type.id if blanket_type else False,
            'vendor_id': main_vendor_id,
            'line_ids': contract_lines,
        })
        
        self.write({
            'purchase_agreement_id': contract.id,
            'contract_created': True,
        })
        
        self.message_post(
            body=f"B16: Đã tạo Purchase Agreement/Contract {contract.name}",
            message_type='notification',
        )
        
        # Return action to open the Contract
        return {
            'type': 'ir.actions.act_window',
            'name': 'Purchase Agreement',
            'res_model': 'purchase.requisition',
            'res_id': contract.id,
            'view_mode': 'form',
            'target': 'current',
        }
