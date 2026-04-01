from odoo import models, fields, api
import uuid

class VoucherGenerator(models.TransientModel):
    _name = 'voucher.generator'
    _description = 'Voucher Generator'

    denomination = fields.Selection([
        ('50000', '50.000'),
        ('100000', '100.000'),
        ('200000', '200.000'),
    ], string='Mệnh giá', required=True, default='50000')

    quantity = fields.Integer(
        string='Số lượng',
        required=True,
        default=1
    )

    point_required = fields.Integer(
        string='Điểm để đổi',
        required=True
    )
    
    state = fields.Selection([
        ('draft', 'Nháp'),
        ('active', 'Đang dùng'),
    ], string='Trạng thái', default='active', required=True)

    partner_id = fields.Many2one(
        'urbox.partner',
        string='Đối tác Urbox'
    )

    def action_generate(self):
        self.ensure_one()
        Voucher = self.env['voucher.voucher']
        vals_list = []
        for i in range(self.quantity):
            # Generate a unique code (dummy implementation with UUID for now, can be improved)
            code = str(uuid.uuid4())[:8].upper()
            
            vals = {
                'name': f'Voucher {dict(self._fields["denomination"].selection).get(self.denomination)}',
                'denomination': self.denomination,
                'value': float(self.denomination),
                'point_required': self.point_required,
                'quantity': 1, # Each voucher is unique, so quantity is 1
                'state': self.state,
                'code': code,
                'partner_id': self.partner_id.id if self.partner_id else False,
            }
            vals_list.append(vals)
        
        Voucher.create(vals_list)
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'type': 'success',
                'message': f'Đã tạo thành công {self.quantity} voucher!',
                'next': {'type': 'ir.actions.act_window_close'},
            }
        }
