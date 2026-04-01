# -*- coding: utf-8 -*-
from odoo import models, fields, api

class StockPicking(models.Model):
    _inherit = 'stock.picking'

    vendor_complaint_ids = fields.One2many('vendor.complaint', 'picking_id', string='Vendor Complaints')
    vendor_complaint_count = fields.Integer('Complaint Count', compute='_compute_vendor_complaint_count')

    @api.depends('vendor_complaint_ids')
    def _compute_vendor_complaint_count(self):
        for picking in self:
            picking.vendor_complaint_count = len(picking.vendor_complaint_ids)

    def button_validate(self):
        """
        Intercept Validate để mở Wizard Complaint
        """
        self.ensure_one()
        
        if self.env.context.get('skip_vendor_complaint'):
            return super().button_validate()
        
        if self.picking_type_code != 'incoming':
            return super().button_validate()
        
        has_qip_failed = any(m.qip_status == 'failed' for m in self.move_ids)
        has_shortage = any(m.quantity < m.product_uom_qty for m in self.move_ids)
        
        if has_qip_failed or has_shortage:
            return {
                'name': 'Phiếu hàng thiếu/thừa - Chờ xử lý (Bước 1)',
                'type': 'ir.actions.act_window',
                'res_model': 'vendor.complaint.wizard',
                'view_mode': 'form',
                'target': 'new',
                'context': {
                    'default_picking_id': self.id,
                    'default_has_qip_failed': has_qip_failed,
                    'default_has_shortage': has_shortage,
                },
            }
        
        return super().button_validate()

    def action_view_vendor_complaints(self):
        self.ensure_one()
        return {
            'name': 'Vendor Complaints',
            'type': 'ir.actions.act_window',
            'res_model': 'vendor.complaint',
            'view_mode': 'list,form',
            'domain': [('picking_id', '=', self.id)],
        }