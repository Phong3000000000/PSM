# -*- coding: utf-8 -*-

import logging
from odoo import api, fields, models, _

_logger = logging.getLogger(__name__)


class PsmDbSyncLog(models.Model):
    _name = 'psm.db.sync.log'
    _description = 'Database Synchronization Log'
    _order = 'start_time desc, id desc'
    _rec_name = 'display_name'

    # Thông tin nhiệm vụ đồng bộ
    sync_id = fields.Many2one('psm.db.sync', string='Nhiệm vụ đồng bộ',
                              ondelete='cascade', index=True)
    mapping_model_id = fields.Many2one('psm.db.mapping.model', string='Ánh xạ mô hình',
                                       readonly=True, index=True)
    display_name = fields.Char(compute='_compute_display_name', string='Tên hiển thị', store=True)

    # Thời gian
    start_time = fields.Datetime(string='Thời gian bắt đầu', required=True, index=True)
    end_time = fields.Datetime(string='Thời gian kết thúc', index=True)
    duration = fields.Float(string='Thời gian thực thi (giây)', compute='_compute_duration', store=True)

    # Trạng thái
    status = fields.Selection([
        ('running', 'Đang chạy'),
        ('completed', 'Hoàn thành'),
        ('failed', 'Lỗi'),
        ('cancelled', 'Đã hủy')
    ], string='Trạng thái', default='running', required=True, index=True)

    # Thống kê
    records_found = fields.Integer(string='Số bản ghi tìm thấy', default=0)
    records_created = fields.Integer(string='Số bản ghi tạo mới', default=0)
    records_updated = fields.Integer(string='Số bản ghi cập nhật', default=0)
    records_failed = fields.Integer(string='Số bản ghi lỗi', default=0)
    records_skipped = fields.Integer(string='Số bản ghi bỏ qua', default=0)

    # Chi tiết
    message = fields.Text(string='Thông báo')
    error_details = fields.Text(string='Chi tiết lỗi')

    # Quan hệ
    mapped_record_ids = fields.One2many('psm.db.mapping.data', 'log_id', string='Bản ghi đã ánh xạ')
    mapped_record_count = fields.Integer(compute='_compute_mapped_record_count',
                                         string='Số lượng bản ghi')

    # System fields
    company_id = fields.Many2one('res.company', string='Công ty',
                                 required=True, default=lambda self: self.env.company)
    user_id = fields.Many2one('res.users', string='Người dùng',
                              default=lambda self: self.env.user, readonly=True)

    @api.depends('sync_id', 'start_time', 'status')
    def _compute_display_name(self):
        for record in self:
            if record.sync_id:
                status_emoji = '🔄'
                if record.status == 'completed':
                    status_emoji = '✅'
                elif record.status == 'failed':
                    status_emoji = '❌'
                elif record.status == 'cancelled':
                    status_emoji = '⚠️'

                record.display_name = f"{status_emoji} {record.sync_id.name} ({record.start_time.strftime('%Y-%m-%d %H:%M:%S')})"
            else:
                record.display_name = record.start_time.strftime('%Y-%m-%d %H:%M:%S')

    @api.depends('start_time', 'end_time')
    def _compute_duration(self):
        for record in self:
            if record.start_time and record.end_time:
                delta = record.end_time - record.start_time
                record.duration = delta.total_seconds()
            else:
                record.duration = 0.0

    @api.depends('mapped_record_ids')
    def _compute_mapped_record_count(self):
        for record in self:
            record.mapped_record_count = len(record.mapped_record_ids)

    def action_view_mapped_records(self):
        """Xem bản ghi đã ánh xạ"""
        self.ensure_one()

        return {
            'name': _('Bản ghi đã ánh xạ'),
            'type': 'ir.actions.act_window',
            'res_model': 'psm.db.mapping.data',
            'view_mode': 'tree,form',
            'domain': [('log_id', '=', self.id)],
            'context': {'default_log_id': self.id},
        }

    def action_cancel(self):
        """Hủy nhiệm vụ đồng bộ đang chạy"""
        for record in self:
            if record.status == 'running':
                record.write({
                    'status': 'cancelled',
                    'end_time': fields.Datetime.now(),
                    'message': (record.message or '') + '\n' + _('Đã hủy bởi người dùng.')
                })

                # Cập nhật trạng thái của nhiệm vụ đồng bộ
                if record.sync_id:
                    record.sync_id.write({
                        'state': 'ready'
                    })

    def action_rerun(self):
        """Chạy lại nhiệm vụ đồng bộ"""
        self.ensure_one()

        if not self.sync_id:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Lỗi'),
                    'message': _('Không thể chạy lại nhiệm vụ đồng bộ vì không tìm thấy tham chiếu.'),
                    'sticky': False,
                    'type': 'danger'
                }
            }

        return self.sync_id.action_sync_now()

    def name_get(self):
        result = []
        for record in self:
            name = record.display_name
            result.append((record.id, name))
        return result