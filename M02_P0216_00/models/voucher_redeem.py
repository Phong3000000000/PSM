from odoo import models, fields, api

class VoucherRedeem(models.Model):
    _name = 'voucher.redeem'
    _description = 'Voucher Redeem History'

    employee_id = fields.Many2one(
        'hr.employee',
        string='Nhân viên',
        required=True
    )
    voucher_id = fields.Many2one(
        'voucher.voucher',  
        string='Voucher',
        required=True
    )
    point_used = fields.Integer(
        string='Điểm đã dùng'
    )
    redeem_date = fields.Datetime(
        string='Ngày đổi',
        default=fields.Datetime.now
    )
