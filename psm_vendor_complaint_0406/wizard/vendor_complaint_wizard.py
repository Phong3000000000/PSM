# -*- coding: utf-8 -*-
from odoo import models, fields, api, _

class VendorComplaintWizard(models.TransientModel):
    _name = 'vendor.complaint.wizard'
    _description = 'Vendor Complaint Wizard'

    picking_id = fields.Many2one('stock.picking', string='Stock Picking', required=True)
    partner_id = fields.Many2one('res.partner', related='picking_id.partner_id', string='Vendor')
    
    complaint_type = fields.Selection([
        ('excess', 'Hàng thừa (TH1) - Nhận và đóng'),
        ('shortage', 'Hàng thiếu (TH2) - FSC duyệt giao bù'),
        ('defect_province', 'Hàng lỗi Tỉnh (TH3) - QA review -> FSC duyệt'),
        ('defect_metro', 'Hàng lỗi HCM/HN (TH4) - Không nhận'),
    ], string='Complaint Type', required=True)
    
    line_ids = fields.One2many('vendor.complaint.wizard.line', 'wizard_id', string='Products with Variance')
    notes = fields.Text('Notes')

    @api.model
    def default_get(self, fields):
        res = super().default_get(fields)
        if self.env.context.get('default_picking_id'):
            picking = self.env['stock.picking'].browse(self.env.context['default_picking_id'])
            
            # --- AUTO DETECT COMPLAINT TYPE ---
            # Mặc định chưa chọn
            suggested_type = False
            
            # Check Lỗi QIP
            has_qip_failed = self.env.context.get('default_has_qip_failed')
            if has_qip_failed:
                # Lấy tỉnh thành của kho nhận hàng
                warehouse_state = picking.picking_type_id.warehouse_id.partner_id.state_id
                state_name = warehouse_state.name or ''
                
                # Logic phân loại TH3 vs TH4 dựa trên tỉnh thành
                # Đọc cấu hình Metro từ System Parameter (Settings > Technical > System Parameters)
                # Key: vendor_complaint.metro_state_keywords
                metro_config = self.env['ir.config_parameter'].sudo().get_param(
                    'vendor_complaint.metro_state_keywords',
                    'Hồ Chí Minh,Ho Chi Minh,Hà Nội,Ha Noi'  # Default fallback
                )
                metro_keywords = [k.strip() for k in str(metro_config).split(',') if k.strip()]
                
                # Check if warehouse state matches any metro keyword (case-insensitive)
                is_metro = any(k.lower() in state_name.lower() for k in metro_keywords)
                
                if is_metro:
                    suggested_type = 'defect_metro' # TH4
                else:
                    suggested_type = 'defect_province' # TH3
            
            # Check Thiếu hàng (nếu không lỗi QIP)
            elif self.env.context.get('default_has_shortage'):
                suggested_type = 'shortage' # TH2

            if suggested_type:
                res['complaint_type'] = suggested_type
            
            # --- AUTO CREATE LINES ---
            lines = []
            for move in picking.move_ids:
                has_qip_failed = move.qip_status == 'failed'
                has_variance = move.product_uom_qty != move.quantity
                
                if has_qip_failed or has_variance:
                    lines.append((0, 0, {
                        'product_id': move.product_id.id,
                        'ordered_qty': move.product_uom_qty,
                        'received_qty': move.quantity,
                        'uom_id': move.product_uom.id,
                        'reason': 'Lỗi QIP' if has_qip_failed else 'Chênh lệch số lượng'
                    }))
            
            if lines:
                res['line_ids'] = lines
        return res

    def action_create_complaint(self):
        """Tạo vendor complaint và tiếp tục validate"""
        self.ensure_one()
        
        # Tạo vendor complaint
        complaint = self.env['vendor.complaint'].create({
            'picking_id': self.picking_id.id,
            'complaint_type': self.complaint_type,
            'line_ids': [(0, 0, {
                'product_id': line.product_id.id,
                'ordered_qty': line.ordered_qty,
                'received_qty': line.received_qty,
                'reason': line.reason,
            }) for line in self.line_ids],
            'qa_notes': self.notes if self.complaint_type == 'defect_province' else False,
        })
        
        # Submit complaint ngay
        complaint.action_submit()
        
        picking = self.picking_id
        
        # DEBUG: Log picking info
        import logging
        _logger = logging.getLogger(__name__)
        _logger.info('=== VENDOR COMPLAINT WIZARD DEBUG ===')
        _logger.info('Picking: %s (ID: %s)', picking.name, picking.id)
        _logger.info('Picking Type create_backorder setting: %s', picking.picking_type_id.create_backorder)
        
        # Store backorder_ids BEFORE validation to find new ones after
        existing_backorder_ids = self.env['stock.picking'].search([
            ('backorder_id', '=', picking.id)
        ]).ids
        _logger.info('Existing backorders before validation: %s', existing_backorder_ids)
        
        # Log move quantities
        for move in picking.move_ids:
            _logger.info('Move %s: Demand=%s, Quantity=%s, State=%s', 
                        move.product_id.name, move.product_uom_qty, move.quantity, move.state)
        
        # IMPORTANT: Force the picking type to allow backorder for this validation
        # This ensures backorder is created even if picking_type.create_backorder = 'never'
        original_backorder_setting = picking.picking_type_id.create_backorder
        if original_backorder_setting == 'never':
            _logger.info('Temporarily changing create_backorder from "never" to "always"')
            picking.picking_type_id.create_backorder = 'always'
        
        try:
            # Validate picking
            # - skip_backorder=True → bypasses the BackorderConfirmation wizard popup
            # - skip_vendor_complaint=True → avoid triggering our complaint wizard again
            picking.with_context(
                skip_vendor_complaint=True,
                skip_backorder=True,
            ).button_validate()
        finally:
            # Restore original setting
            if original_backorder_setting == 'never':
                picking.picking_type_id.create_backorder = original_backorder_setting
                _logger.info('Restored create_backorder to "never"')
        
        # Find the newly created backorder
        new_backorders = self.env['stock.picking'].search([
            ('backorder_id', '=', picking.id),
            ('id', 'not in', existing_backorder_ids)
        ])
        _logger.info('New backorders found: %s', new_backorders.mapped('name'))
        
        if new_backorders:
            backorder = new_backorders[0]
            
            # RENAME BACKORDER: WH/IN/00001 → WH/IN/00001-BO001
            # If this is a backorder of a backorder, extract root name
            original_name = picking.name  # e.g. WH/IN/00001 or WH/IN/00001-BO001
            
            # Find root picking name (remove existing -BOxxx suffix if any)
            import re
            root_match = re.match(r'^(.+?)-BO\d*$', original_name)
            if root_match:
                root_name = root_match.group(1)  # e.g. WH/IN/00001
            else:
                root_name = original_name  # e.g. WH/IN/00001
            
            # Count existing backorders with same root name
            existing_bos = self.env['stock.picking'].search([
                ('name', 'like', root_name + '-BO%')
            ])
            next_bo_number = len(existing_bos) + 1
            
            # Format: WH/IN/00001-BO001, WH/IN/00001-BO002, etc.
            new_backorder_name = '%s-BO%03d' % (root_name, next_bo_number)
            backorder.name = new_backorder_name
            _logger.info('Renamed backorder to %s (BO #%d)', new_backorder_name, next_bo_number)
            
            # Link the backorder to the complaint
            complaint.backorder_id = backorder.id
            complaint.message_post(
                body=_('Phiếu Giao Bù %s đã được tạo tự động với số lượng còn thiếu. Chờ FSC duyệt.') % new_backorder_name
            )
            _logger.info('Linked backorder %s to complaint %s', new_backorder_name, complaint.name)
        else:
            _logger.warning('NO BACKORDER CREATED! Check if quantities were properly set.')
        
        # Return to close wizard
        return {'type': 'ir.actions.act_window_close'}


    def action_skip_and_validate(self):
        self.ensure_one()
        return self.picking_id.with_context(skip_vendor_complaint=True).button_validate()


class VendorComplaintWizardLine(models.TransientModel):
    _name = 'vendor.complaint.wizard.line'
    _description = 'Vendor Complaint Wizard Line'

    wizard_id = fields.Many2one('vendor.complaint.wizard', string='Wizard', required=True, ondelete='cascade')
    product_id = fields.Many2one('product.product', string='Product', required=True)
    ordered_qty = fields.Float('Ordered', required=True)
    received_qty = fields.Float('Received', required=True)
    variance_qty = fields.Float('Variance', compute='_compute_variance')
    uom_id = fields.Many2one('uom.uom', string='UoM')
    reason = fields.Text('Reason')

    @api.depends('ordered_qty', 'received_qty')
    def _compute_variance(self):
        for line in self:
            line.variance_qty = line.received_qty - line.ordered_qty