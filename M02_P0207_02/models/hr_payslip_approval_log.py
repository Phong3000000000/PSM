# -*- coding: utf-8 -*-
from odoo import models, fields, api, _

class HrPayslipApprovalLog(models.Model):
    _name = 'hr.payslip.approval.log'
    _description = 'Payslip Approval / Refusal Log'
    _order = 'date desc'

    payslip_id = fields.Many2one('hr.payslip', string='Payslip', required=True, ondelete='cascade')
    employee_id = fields.Many2one(related='payslip_id.employee_id', store=True, string='Employee')
    action = fields.Selection([
        ('approved', 'Phê duyệt'),
        ('refused', 'Từ chối'),
    ], string='Action', required=True)
    reason = fields.Text(string='Reason')
    user_id = fields.Many2one('res.users', string='By', default=lambda self: self.env.user)
    date = fields.Datetime(string='Date', default=fields.Datetime.now)
    stage = fields.Char(string='Stage', help='HR or C-Level')

