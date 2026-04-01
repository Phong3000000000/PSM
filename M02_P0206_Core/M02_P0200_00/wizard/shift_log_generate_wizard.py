# -*- coding: utf-8 -*-
import calendar
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class ShiftLogGenerateWizard(models.TransientModel):
    _name = 'shift.log.generate.wizard'
    _description = 'Wizard Tạo Shift Log Cả Tháng'

    pos_config_ids = fields.Many2many(
        'pos.config',
        string='Cửa Hàng',
        required=True,
        domain="[('id', 'in', available_pos_config_ids)]",
        help='Chọn cửa hàng OPS để tạo shift log',
    )
    available_pos_config_ids = fields.Many2many(
        'pos.config',
        compute='_compute_available_pos_config_ids',
        string='Available POS Configs',
    )
    month = fields.Selection([
        ('1', 'Tháng 1'), ('2', 'Tháng 2'), ('3', 'Tháng 3'),
        ('4', 'Tháng 4'), ('5', 'Tháng 5'), ('6', 'Tháng 6'),
        ('7', 'Tháng 7'), ('8', 'Tháng 8'), ('9', 'Tháng 9'),
        ('10', 'Tháng 10'), ('11', 'Tháng 11'), ('12', 'Tháng 12'),
    ], string='Tháng', required=True,
       default=lambda self: str(fields.Date.context_today(self).month))
    year = fields.Integer(
        string='Năm', required=True,
        default=lambda self: fields.Date.context_today(self).year,
    )

    @api.depends()
    def _compute_available_pos_config_ids(self):
        """Chỉ hiển thị các POS thuộc phòng ban khối OPS."""
        ops_departments = self.env['hr.department'].search([
            ('block_id.code', '=', 'OPS'),
            ('pos_config_id', '!=', False),
        ])
        pos_ids = ops_departments.mapped('pos_config_id').ids
        for rec in self:
            rec.available_pos_config_ids = [(6, 0, pos_ids)]

    def action_generate(self):
        """Tạo shift.log cho tất cả ngày × tất cả ca × tất cả cửa hàng đã chọn.
        Bỏ qua bản ghi đã tồn tại (trùng pos_config_id + date + shift_id)."""
        self.ensure_one()

        month = int(self.month)
        year = self.year
        num_days = calendar.monthrange(year, month)[1]

        # Tạo danh sách ngày
        from datetime import date
        dates = [date(year, month, day) for day in range(1, num_days + 1)]

        # Lấy tất cả shift logs đã tồn tại cho các cửa hàng + tháng này
        date_start = date(year, month, 1)
        date_end = date(year, month, num_days)
        existing_logs = self.env['shift.log'].search([
            ('pos_config_id', 'in', self.pos_config_ids.ids),
            ('date', '>=', date_start),
            ('date', '<=', date_end),
        ])

        # Tạo set các (pos_config_id, date, shift_id) đã tồn tại
        existing_keys = set()
        for log in existing_logs:
            existing_keys.add((log.pos_config_id.id, log.date, log.shift_id.id))

        # Tạo batch records
        vals_list = []
        total_expected = 0
        for pos_config in self.pos_config_ids:
            # Lấy các ca được thiết lập cho POS này
            config_shifts = pos_config.main_shift_ids + pos_config.secondary_shift_ids
            if not config_shifts:
                continue
            
            total_expected += len(dates) * len(config_shifts)
            
            for d in dates:
                for shift in config_shifts:
                    key = (pos_config.id, d, shift.id)
                    if key not in existing_keys:
                        vals_list.append({
                            'pos_config_id': pos_config.id,
                            'date': d,
                            'shift_id': shift.id,
                            'state': 'draft',
                        })

        created_count = 0
        skipped_count = total_expected - len(vals_list)

        if vals_list:
            self.env['shift.log'].create(vals_list)
            created_count = len(vals_list)

        message_parts = []
        if created_count:
            message_parts.append(
                _('Đã tạo %d shift log.', created_count)
            )
        if skipped_count:
            message_parts.append(
                _('Bỏ qua %d shift log đã tồn tại.', skipped_count)
            )
        if not created_count and skipped_count:
            msg_type = 'warning'
        else:
            msg_type = 'success'

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Generate Shift Log - Tháng %s/%s', self.month, self.year),
                'message': ' '.join(message_parts) if message_parts else _('Không có gì để tạo.'),
                'type': msg_type,
                'sticky': False,
                'next': {'type': 'ir.actions.act_window_close'},
            },
        }
