# -*- coding: utf-8 -*-
from odoo import models, fields, api, _


class ApprovalRequestPosition(models.Model):
    """Standalone position lines on an approval.request (not linked to referral request)."""
    _name = 'approval.request.position'
    _description = 'Approval Request Position Line'

    approval_id = fields.Many2one(
        'approval.request', string='Yêu cầu phê duyệt', ondelete='cascade')
    job_id = fields.Many2one('hr.job', string='Vị trí', required=True)
    job_type = fields.Selection([
        ('fulltime', 'Full-time'),
        ('parttime', 'Part-time'),
    ], string='Loại', default='fulltime')
    quantity = fields.Integer(string='Cần GT', default=1)
    bonus_amount = fields.Float(string='Thưởng (VNĐ)', default=0)
    wage = fields.Float(string='Lương/giờ', default=0)
    note = fields.Char(string='Ghi chú')
