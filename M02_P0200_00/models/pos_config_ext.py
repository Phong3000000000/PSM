# -*- coding: utf-8 -*-
from odoo import models, fields


class PosConfigExt(models.Model):
    _inherit = 'pos.config'

    store_code = fields.Char(string='Store Code', help='Mã cửa hàng')
    
    opening_hour = fields.Float(string='Opening Hour', help='Giờ mở cửa')
    closing_hour = fields.Float(string='Closing Hour', help='Giờ đóng cửa')
    
    main_shift_ids = fields.Many2many('restaurant.shift', 'pos_config_main_shift_rel', 'config_id', 'shift_id', string='Main Shifts', help='Các ca làm việc chính')
    secondary_shift_ids = fields.Many2many('restaurant.shift', 'pos_config_secondary_shift_rel', 'config_id', 'shift_id', string='Secondary Shifts', help='Các ca làm việc phụ')

    department_id = fields.Many2one(
        'hr.department',
        string='Phòng Ban',
        compute='_compute_department_id',
        store=True,
    )

    def _compute_department_id(self):
        for rec in self:
            # Tìm phòng ban có pos_config_id khớp với record này
            dept = self.env['hr.department'].search([('pos_config_id', '=', rec.id)], limit=1)
            rec.department_id = dept.id if dept else False
