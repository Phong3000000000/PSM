# -*- coding: utf-8 -*-
from odoo import models, fields, api


class VendorComplaintLine(models.Model):
    _name = 'vendor.complaint.line'
    _description = 'Vendor Complaint Line'

    complaint_id = fields.Many2one('vendor.complaint', string='Complaint', required=True, ondelete='cascade')
    product_id = fields.Many2one('product.product', string='Product', required=True)
    
    ordered_qty = fields.Float('Ordered Qty', required=True)
    received_qty = fields.Float('Received Qty', required=True)
    variance_qty = fields.Float('Variance', compute='_compute_variance', store=True)
    
    uom_id = fields.Many2one('uom.uom', string='UoM', related='product_id.uom_id', store=True)
    
    reason = fields.Text('Reason / Notes')
    complaint_type = fields.Selection(related='complaint_id.complaint_type', store=True)
    
    @api.depends('ordered_qty', 'received_qty')
    def _compute_variance(self):
        for line in self:
            line.variance_qty = line.received_qty - line.ordered_qty
