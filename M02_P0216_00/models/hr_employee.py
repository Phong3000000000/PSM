# -*- coding: utf-8 -*-

from odoo import models, fields, api


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    total_points = fields.Float(
        string='Tổng điểm thưởng',
        default=0.0,
        help='Tổng số điểm nhân viên đã được nhận'
    )
    
    voucher_redeem_ids = fields.One2many(
        'voucher.redeem',
        'employee_id',
        string='Lịch sử đổi quà'
    )

    def action_grant_points_from_fund(self):
        """Mở form cấp điểm với nhân viên và kho điểm đã chọn sẵn"""
        self.ensure_one()
        # Get fund_id from context (passed from button)
        fund_id = self.env.context.get('fund_id')
        return {
            'type': 'ir.actions.act_window',
            'name': 'Cấp điểm cho %s' % self.name,
            'res_model': 'point.grant',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_fund_id': fund_id,
                'default_employee_id': self.id,
            }
        }
