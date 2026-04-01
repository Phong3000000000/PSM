# -*- coding: utf-8 -*-
from odoo import models, fields


class StockPicking(models.Model):
    _inherit = 'stock.picking'
    
    complaint_id = fields.Many2one(
        'food.safety.complaint',
        string='Food Safety Complaint',
        readonly=True,
        help='Related food safety complaint if this is a compensation or quarantine picking'
    )
    
    def action_view_complaint(self):
        """Smart button to view related complaint"""
        self.ensure_one()
        if not self.complaint_id:
            return
        
        return {
            'type': 'ir.actions.act_window',
            'name': 'Food Safety Complaint',
            'res_model': 'food.safety.complaint',
            'res_id': self.complaint_id.id,
            'view_mode': 'form',
            'target': 'current',
        }
