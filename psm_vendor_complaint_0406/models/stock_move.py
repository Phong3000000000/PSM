# -*- coding: utf-8 -*-
from odoo import models, fields, api


class StockMove(models.Model):
    _inherit = 'stock.move'

    # Store original PO quantity (never changes after creation)
    original_ordered_qty = fields.Float(
        'SL Đặt Gốc (Stored)',
        digits='Product Unit of Measure',
        copy=False,
        readonly=True,
        help="Số lượng đặt ban đầu từ PO, lưu lại tại thời điểm tạo move"
    )
    
    # Computed field: Fetch from PO line (works for OLD moves too)
    po_ordered_qty = fields.Float(
        'SL Đặt từ PO',
        compute='_compute_po_ordered_qty',
        digits='Product Unit of Measure',
        help="Số lượng đặt từ Purchase Order Line (computed)"
    )

    @api.depends('purchase_line_id', 'purchase_line_id.product_qty', 'original_ordered_qty', 
                 'picking_id', 'picking_id.backorder_id')
    def _compute_po_ordered_qty(self):
        for move in self:
            # If this is a BACKORDER, fetch from ORIGINAL picking's PO line
            if move.picking_id and move.picking_id.backorder_id:
                # Find corresponding move in original picking
                original_picking = move.picking_id.backorder_id
                original_move = original_picking.move_ids.filtered(
                    lambda m: m.product_id == move.product_id
                )
                if original_move:
                    # Get from original move's PO line
                    if original_move[0].purchase_line_id:
                        move.po_ordered_qty = original_move[0].purchase_line_id.product_qty
                    elif original_move[0].original_ordered_qty:
                        move.po_ordered_qty = original_move[0].original_ordered_qty
                    else:
                        move.po_ordered_qty = original_move[0].product_uom_qty
                else:
                    # Fallback to own PO line
                    move.po_ordered_qty = move.purchase_line_id.product_qty if move.purchase_line_id else move.product_uom_qty
            else:
                # Normal picking (not backorder)
                if move.original_ordered_qty:
                    move.po_ordered_qty = move.original_ordered_qty
                elif move.purchase_line_id:
                    move.po_ordered_qty = move.purchase_line_id.product_qty
                else:
                    move.po_ordered_qty = move.product_uom_qty

    @api.model_create_multi
    def create(self, vals_list):
        moves = super().create(vals_list)
        # Store original demand at creation time
        for move in moves:
            if not move.original_ordered_qty and move.product_uom_qty:
                move.original_ordered_qty = move.product_uom_qty
        return moves
