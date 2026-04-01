# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class PlanningPeriod(models.Model):
    """
    Kỳ đăng ký ca làm việc
    Kiểm soát thời gian nhân viên được phép đăng ký
    """
    _name = 'planning.period'
    _description = 'Kỳ đăng ký ca'
    _order = 'date_from desc'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(
        string='Tên kỳ',
        required=True,
        tracking=True,
        help='VD: Tuần 42/2026, Tháng 01/2026'
    )
    date_from = fields.Date(
        string='Từ ngày',
        required=True,
        tracking=True
    )
    date_to = fields.Date(
        string='Đến ngày',
        required=True,
        tracking=True
    )
    state = fields.Selection([
        ('draft', 'Nháp'),
        ('open', 'Đang mở đăng ký'),
        ('closed', 'Đã đóng'),
    ], default='draft', string='Trạng thái', tracking=True)
    
    closing_datetime = fields.Datetime(
        string='Thời hạn đăng ký',
        help='Hệ thống sẽ tự động đóng kỳ đăng ký sau thời điểm này',
        tracking=True
    )
    
    # Relations
    slot_ids = fields.One2many(
        'planning.slot',
        'period_id',
        string='Các ca làm việc'
    )
    forecast_ids = fields.One2many(
        'workforce.forecast',
        'period_id',
        string='Dữ liệu Forecast'
    )
    
    # Stats
    slot_count = fields.Integer(
        string='Tổng số ca',
        compute='_compute_slot_stats'
    )
    slot_open_count = fields.Integer(
        string='Ca còn trống',
        compute='_compute_slot_stats'
    )
    slot_filled_count = fields.Integer(
        string='Ca đã có người',
        compute='_compute_slot_stats'
    )
    
    @api.depends('slot_ids', 'slot_ids.resource_id')
    def _compute_slot_stats(self):
        for rec in self:
            rec.slot_count = len(rec.slot_ids)
            rec.slot_open_count = len(rec.slot_ids.filtered(lambda s: not s.resource_id))
            rec.slot_filled_count = rec.slot_count - rec.slot_open_count
    
    @api.constrains('date_from', 'date_to')
    def _check_dates(self):
        for rec in self:
            if rec.date_from and rec.date_to and rec.date_from > rec.date_to:
                raise UserError(_('Ngày bắt đầu phải nhỏ hơn hoặc bằng ngày kết thúc!'))
    
    def action_open(self):
        """Mở kỳ đăng ký - Publish tất cả slot"""
        self.ensure_one()
        if not self.slot_ids:
            raise UserError(_('Chưa có ca làm việc nào trong kỳ này! Vui lòng sinh lịch trước.'))
        
        # Chuyển tất cả slot sang published
        self.slot_ids.write({'state': 'published'})
        self.state = 'open'
        
        # Log message
        self.message_post(
            body=_('Đã mở kỳ đăng ký với %s ca làm việc.') % len(self.slot_ids),
            message_type='notification'
        )
    
    def action_close(self):
        """Đóng kỳ đăng ký - Khóa nút đăng ký trên Portal"""
        self.ensure_one()
        self.state = 'closed'
        self.message_post(
            body=_('Đã đóng kỳ đăng ký.'),
            message_type='notification'
        )
    
    def action_reset_to_draft(self):
        """Mở lại để chỉnh sửa"""
        self.ensure_one()
        self.state = 'draft'
    
    def action_view_slots(self):
        """Xem danh sách ca trong kỳ"""
        self.ensure_one()
        return {
            'name': _('Ca làm việc - %s') % self.name,
            'type': 'ir.actions.act_window',
            'res_model': 'planning.slot',
            'view_mode': 'list,form,gantt',
            'domain': [('period_id', '=', self.id)],
            'context': {'default_period_id': self.id},
        }

    @api.model
    def _cron_auto_close_periods(self):
        """
        Cron Job: Tự động đóng kỳ đăng ký khi hết hạn
        Chạy mỗi 1 giờ (cấu hình trong data/cron_jobs.xml)
        """
        now = fields.Datetime.now()
        periods_to_close = self.search([
            ('state', '=', 'open'),
            ('closing_datetime', '!=', False),
            ('closing_datetime', '<=', now),
        ])
        
        for period in periods_to_close:
            period.state = 'closed'
            period.message_post(
                body=_('Kỳ đăng ký đã tự động đóng do hết hạn (Thời hạn: %s)') % period.closing_datetime,
                message_type='notification'
            )
        
        return True

