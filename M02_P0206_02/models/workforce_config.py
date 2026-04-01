# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class WorkforceStoreConfig(models.Model):
    """
    Cấu hình Workforce cho Cửa hàng
    Lưu trữ các tham số mục tiêu của nhà hàng theo kỳ
    """
    _name = 'workforce.store.config'
    _description = 'Cấu hình Workforce Cửa hàng'
    _order = 'store_id, period_id desc'
    _rec_name = 'display_name'

    store_id = fields.Many2one(
        'hr.department',
        string='Cửa hàng',
        required=True,
        index=True,
        help='Cửa hàng (Phòng ban) áp dụng cấu hình này'
    )
    period_id = fields.Many2one(
        'planning.period',
        string='Kỳ áp dụng',
        index=True,
        help='Để trống nếu là cấu hình mặc định cho cửa hàng'
    )
    
    # KPI Targets
    target_gcpch = fields.Float(
        string='Target GCPCH',
        default=10.0,
        help='Mục tiêu năng suất: Guest Count Per Crew Hour. VD: 10 = mỗi nhân viên phục vụ 10 khách/giờ'
    )
    target_labor_cost = fields.Float(
        string='Target L%',
        default=25.0,
        help='Mục tiêu chi phí nhân sự tính theo % doanh thu. VD: 25 = chi phí nhân sự không quá 25% doanh thu'
    )
    
    # Trend Factor
    trend_factor = fields.Float(
        string='Trend Factor',
        default=1.0,
        help='Hệ số xu hướng điều chỉnh so với dữ liệu quá khứ. VD: 1.05 = dự báo tăng 5%, 0.95 = dự báo giảm 5%'
    )
    
    # Computed display name
    display_name = fields.Char(
        compute='_compute_display_name',
        store=True
    )
    
    # Active flag
    active = fields.Boolean(default=True)
    
    @api.depends('store_id', 'period_id')
    def _compute_display_name(self):
        for rec in self:
            if rec.period_id:
                rec.display_name = '%s - %s' % (rec.store_id.name or '', rec.period_id.name or '')
            else:
                rec.display_name = '%s - Mặc định' % (rec.store_id.name or '')
    
    @api.constrains('target_gcpch')
    def _check_target_gcpch(self):
        for rec in self:
            if rec.target_gcpch <= 0:
                raise ValidationError(_('Target GCPCH phải lớn hơn 0!'))
    
    @api.constrains('target_labor_cost')
    def _check_target_labor_cost(self):
        for rec in self:
            if rec.target_labor_cost < 0 or rec.target_labor_cost > 100:
                raise ValidationError(_('Target L% phải từ 0 đến 100!'))
    
    @api.constrains('trend_factor')
    def _check_trend_factor(self):
        for rec in self:
            if rec.trend_factor <= 0:
                raise ValidationError(_('Trend Factor phải lớn hơn 0!'))
    
    _sql_constraints = [
        (
            'store_period_unique',
            'UNIQUE(store_id, period_id)',
            'Đã tồn tại cấu hình cho cửa hàng và kỳ này!'
        ),
    ]
    
    @api.model
    def get_config_for_store(self, store_id, period_id=None):
        """
        Lấy cấu hình cho cửa hàng.
        Ưu tiên: Config theo Period > Config mặc định (period_id = False)
        """
        config = None
        if period_id:
            config = self.search([
                ('store_id', '=', store_id),
                ('period_id', '=', period_id),
                ('active', '=', True),
            ], limit=1)
        
        if not config:
            config = self.search([
                ('store_id', '=', store_id),
                ('period_id', '=', False),
                ('active', '=', True),
            ], limit=1)
        
        return config
