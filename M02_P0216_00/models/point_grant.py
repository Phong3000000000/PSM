# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class PointGrant(models.Model):
    _name = 'point.grant'
    _description = 'Cấp điểm cho nhân viên'
    _order = 'date desc, id desc'

    name = fields.Char(
        string='Mã phiếu',
        readonly=True,
        default='New'
    )
    date = fields.Date(
        string='Ngày',
        required=True,
        default=fields.Date.context_today
    )
    granter_id = fields.Many2one(
        'hr.employee',
        string='Người cấp điểm',
        required=True,
        default=lambda self: self.env['hr.employee'].search([('user_id', '=', self.env.uid)], limit=1)
    )
    employee_id = fields.Many2one(
        'hr.employee',
        string='Nhân viên nhận điểm',
        required=True
    )
    points = fields.Float(
        string='Số điểm',
        required=True,
        default=10.0
    )
    fund_id = fields.Many2one(
        'shift.point.fund',
        string='Kho điểm',
        required=True,
        domain="[('fund_type', 'in', ['department', 'EOTM', 'EOTQ'])]"
    )
    fund_type = fields.Selection(
        related='fund_id.fund_type',
        string='Loại kho',
        store=True,
        readonly=True
    )
    reason = fields.Text(string='Lý do')
    state = fields.Selection([
        ('draft', 'Nháp'),
        ('confirmed', 'Đã xác nhận'),
    ], string='Trạng thái', default='draft', tracking=True)
    
    company_id = fields.Many2one(
        'res.company',
        string='Chi nhánh',
        related='granter_id.company_id',
        store=True
    )
    department_id = fields.Many2one(
        'hr.department',
        string='Phòng ban',
        related='granter_id.department_id',
        store=True
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('point.grant') or 'PG-0001'
        return super().create(vals_list)

    def action_confirm(self):
        for record in self:
            if record.state == 'confirmed':
                raise UserError(_("Phiếu này đã được xác nhận."))
            
            if record.points <= 0:
                raise UserError(_("Số điểm phải lớn hơn 0."))
            
            # Check fund balance
            if record.fund_id.score < record.points:
                raise UserError(_("Kho điểm '%s' không đủ số dư. Số dư hiện tại: %s") % (record.fund_id.name, record.fund_id.score))
            
            # Deduct from fund
            record.fund_id.score -= record.points
            
            # Add points to employee
            record.employee_id.total_points += record.points
            
            record.write({'state': 'confirmed'})

    def action_draft(self):
        for record in self:
            if record.state == 'confirmed':
                # Refund to the fund
                record.fund_id.score += record.points
            record.write({'state': 'draft'})
