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
    
    # ===== VLH ENGINE: KPI DASHBOARD =====
    store_config_id = fields.Many2one(
        'workforce.store.config',
        string='Cấu hình Workforce',
        help='Liên kết với cấu hình KPI của cửa hàng'
    )
    
    # Target KPIs (từ config hoặc manual)
    target_gcpch = fields.Float(
        string='Target GCPCH',
        compute='_compute_target_kpis',
        store=True,
        help='Mục tiêu năng suất: Guest Count Per Crew Hour'
    )
    target_labor_cost = fields.Float(
        string='Target L%',
        compute='_compute_target_kpis',
        store=True,
        help='Mục tiêu chi phí nhân sự (%)'
    )
    
    # Actual KPIs (computed)
    actual_gcpch = fields.Float(
        string='Actual GCPCH',
        compute='_compute_actual_kpis',
        help='Năng suất thực tế: Sum(Forecast GC) / Sum(Allocated Hours)'
    )
    actual_labor_cost = fields.Float(
        string='Actual L%',
        compute='_compute_actual_kpis',
        help='Chi phí nhân sự thực tế (%)'
    )
    
    # Total metrics
    total_forecast_gc = fields.Float(
        string='Tổng GC dự kiến',
        compute='_compute_actual_kpis'
    )
    total_allocated_hours = fields.Float(
        string='Tổng giờ phân bổ',
        compute='_compute_actual_kpis'
    )
    total_forecast_sales = fields.Float(
        string='Tổng doanh thu dự kiến',
        compute='_compute_actual_kpis'
    )
    total_labor_cost_amount = fields.Float(
        string='Tổng chi phí nhân sự',
        compute='_compute_actual_kpis'
    )
    
    # KPI Status
    gcpch_status = fields.Selection([
        ('ok', 'Đạt'),
        ('warning', 'Cảnh báo'),
    ], string='Trạng thái GCPCH', compute='_compute_kpi_status')
    
    labor_status = fields.Selection([
        ('ok', 'Đạt'),
        ('warning', 'Cảnh báo'),
    ], string='Trạng thái L%', compute='_compute_kpi_status')
    
    @api.depends('store_config_id', 'store_config_id.target_gcpch', 'store_config_id.target_labor_cost')
    def _compute_target_kpis(self):
        for rec in self:
            if rec.store_config_id:
                rec.target_gcpch = rec.store_config_id.target_gcpch
                rec.target_labor_cost = rec.store_config_id.target_labor_cost
            else:
                rec.target_gcpch = 10.0  # Default
                rec.target_labor_cost = 25.0  # Default
    
    @api.depends('slot_ids', 'slot_ids.allocated_hours', 'slot_ids.resource_id', 'forecast_ids')
    def _compute_actual_kpis(self):
        for rec in self:
            # Total Forecast GC
            rec.total_forecast_gc = sum(rec.forecast_ids.mapped('projected_gc'))
            
            # Total Forecast Sales
            rec.total_forecast_sales = sum(rec.forecast_ids.mapped('projected_sales'))
            
            # Total Allocated Hours (chỉ tính slot đã có người)
            filled_slots = rec.slot_ids.filtered(lambda s: s.resource_id)
            rec.total_allocated_hours = sum(filled_slots.mapped('allocated_hours'))
            
            # Total Labor Cost
            total_cost = 0.0
            for slot in filled_slots:
                # Lấy hourly_cost từ employee
                employee = slot.resource_id.employee_id if hasattr(slot.resource_id, 'employee_id') else None
                if employee and hasattr(employee, 'hourly_cost'):
                    hourly_cost = employee.hourly_cost or employee.hourly_rate or 0
                else:
                    hourly_cost = 0
                total_cost += (slot.allocated_hours or 0) * hourly_cost
            rec.total_labor_cost_amount = total_cost
            
            # GCPCH = Total GC / Total Hours
            if rec.total_allocated_hours > 0:
                rec.actual_gcpch = rec.total_forecast_gc / rec.total_allocated_hours
            else:
                rec.actual_gcpch = 0
            
            # L% = Total Labor Cost / Total Sales × 100
            if rec.total_forecast_sales > 0:
                rec.actual_labor_cost = (rec.total_labor_cost_amount / rec.total_forecast_sales) * 100
            else:
                rec.actual_labor_cost = 0
    
    @api.depends('actual_gcpch', 'target_gcpch', 'actual_labor_cost', 'target_labor_cost')
    def _compute_kpi_status(self):
        for rec in self:
            # GCPCH: Cao hơn = Tốt hơn
            if rec.target_gcpch > 0 and rec.actual_gcpch >= rec.target_gcpch:
                rec.gcpch_status = 'ok'
            else:
                rec.gcpch_status = 'warning'
            
            # L%: Thấp hơn = Tốt hơn
            if rec.target_labor_cost > 0 and rec.actual_labor_cost <= rec.target_labor_cost:
                rec.labor_status = 'ok'
            else:
                rec.labor_status = 'warning'
    
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

