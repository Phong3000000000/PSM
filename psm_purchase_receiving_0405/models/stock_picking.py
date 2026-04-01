# -*- coding: utf-8 -*-
from odoo import models, api, fields

class StockPicking(models.Model):
    _inherit = 'stock.picking'

    # SỬA LẠI: Thêm compute để tránh lỗi ORM read field store=False
    scan_filter_product_id = fields.Many2one(
        'product.product', 
        string="Filtered Product", 
        store=False, 
        compute='_compute_scan_filter_product_id'
    )

    def _compute_scan_filter_product_id(self):
        for record in self:
            # Luôn set False vì giá trị này chỉ tồn tại tạm thời trên giao diện (JS)
            record.scan_filter_product_id = False


    # ============================================================
    # METHODS FOR RECEIPT BARCODE SCANNING (from purchase_barcode_scanner)
    # ============================================================
    
    @api.model
    def search_picking_by_barcode(self, barcode):
        """
        Search for a stock picking by its name (barcode).
        Only search for pickings in 'assigned' (Ready) state.
        Returns an action to open the picking form if found.
        """
        # 1. Tìm phiếu đã Sẵn sàng (Ready)
        domain = [('state', '=', 'assigned')]
        
        # Ưu tiên tìm chính xác
        picking = self.search([('name', '=', barcode)] + domain, limit=1)
        
        # Nếu không thấy, tìm gần đúng (ilike)
        if not picking:
            picking = self.search([('name', 'ilike', barcode)] + domain, limit=1)
        
        # Nếu vẫn không thấy, mở rộng phạm vi sang các trạng thái khác
        if not picking:
            picking = self.search([
                ('name', 'ilike', barcode),
                ('state', 'in', ['confirmed', 'waiting', 'assigned']),
            ], limit=1)
        
        if picking:
            return {
                'type': 'ir.actions.act_window',
                'name': picking.name,
                'res_model': 'stock.picking',
                'res_id': picking.id,
                'view_mode': 'form',
                'views': [[False, 'form']], 
                'target': 'current',
                'context': {
                    'create': False, 
                    'edit': True
                },
            }
        else:
            return {
                'warning': True,
                'message': f"No ready receipt found with barcode: {barcode}",
            }

    # ============================================================
    # METHODS FOR PRODUCT FILTER (from stock_picking_product_filter)
    # ============================================================
    
    def btn_scan_barcode_js(self):
        """ 
        Hàm dummy: Cần phải tồn tại để XML validation không báo lỗi.
        Thực tế JS sẽ chặn sự kiện click và chạy code client-side.
        """
        return True

    def action_clear_filter(self):
        self.ensure_one()
        self.scan_filter_product_id = False
        return True