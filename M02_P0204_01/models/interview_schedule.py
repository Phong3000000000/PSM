# -*- coding: utf-8 -*-
"""
Model: Interview Schedule
Mô tả: Lịch phỏng vấn theo Brand/Company
"""

from odoo import models, fields, api, exceptions
from datetime import datetime, timedelta
import logging

_logger = logging.getLogger(__name__)

class InterviewSchedule(models.Model):
    """
    Lịch phỏng vấn cho từng Brand
    Store Manager tạo, Operations Manager duyệt
    """
    _name = 'interview.schedule'
    _description = 'Lịch Phỏng Vấn Brand'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'week_start_date desc, company_id'
    _rec_name = 'display_name'

    # ==================== BRAND/COMPANY ====================
    
    company_id = fields.Many2one(
        'res.company',
        string="Brand",
        required=True,
        default=lambda self: self._default_company(),
        tracking=True,
        help="Brand/Cửa hàng"
    )
    
    store_address = fields.Char(
        string="Địa Chỉ Cửa Hàng",
        help="Địa chỉ cụ thể nếu brand có nhiều điểm"
    )
    
    # ==================== MANAGERS ====================
    
    manager_id = fields.Many2one(
        'hr.employee',
        string="Store Manager",
        compute='_compute_manager_id',
        store=True,
        help="Employee có Job Position 'Store Manager' của brand"
    )
    
    # ==================== TUẦN ====================
    
    week_start_date = fields.Date(
        string="Tuần bắt đầu (Thứ Hai)",
        required=True,
        default=lambda self: self._default_week_start(),
        help="Ngày Thứ Hai đầu tuần"
    )
    
    week_display = fields.Char(
        string="Tuần",
        compute='_compute_week_display',
        store=True
    )
    
    # ==================== 3 NGÀY PHỎNG VẤN ====================
    
    interview_date_1 = fields.Datetime(
        string="Ngày PV 1",
        help="Thời gian phỏng vấn đầu tiên trong tuần"
    )
    
    interview_date_2 = fields.Datetime(
        string="Ngày PV 2",
        help="Thời gian phỏng vấn thứ hai trong tuần"
    )
    
    interview_date_3 = fields.Datetime(
        string="Ngày PV 3",
        help="Thời gian phỏng vấn thứ ba trong tuần"
    )
    
    # ==================== TRẠNG THÁI ====================
    
    state = fields.Selection([
        ('draft', 'Nháp'),
        ('confirmed', 'Đã Xác Nhận'),
    ], string="Trạng thái", default='draft', tracking=True)
    
    # ==================== THỐNG KÊ ====================
    
    applicant_count = fields.Integer(
        string="Số ứng viên",
        compute='_compute_applicant_count'
    )
    
    display_name = fields.Char(
        string="Tên hiển thị",
        compute='_compute_display_name'
    )
    
    # ==================== COMPUTED FIELDS ====================
    
    @api.depends('company_id')
    def _compute_manager_id(self):
        """Tự động tìm Store Manager của brand"""
        for rec in self:
            if rec.company_id:
                # Tìm job position "Store Manager" của company này
                job = self.env['hr.job'].search([
                    ('name', 'ilike', 'Store Manager'),
                    ('company_id', '=', rec.company_id.id)
                ], limit=1)
                
                if job:
                    # Tìm employee đang giữ vị trí này
                    employee = self.env['hr.employee'].search([
                        ('job_id', '=', job.id),
                        ('company_id', '=', rec.company_id.id)
                    ], limit=1)
                    rec.manager_id = employee
                else:
                    rec.manager_id = False
                    _logger.warning(f"Không tìm thấy Job Position 'Store Manager' cho {rec.company_id.name}")
            else:
                rec.manager_id = False
    
    @api.depends('company_id', 'week_start_date')
    def _compute_display_name(self):
        """Tên hiển thị: Brand - Week"""
        for rec in self:
            if rec.company_id and rec.week_start_date:
                week_end = rec.week_start_date + timedelta(days=6)
                rec.display_name = f"{rec.company_id.name} - {rec.week_start_date.strftime('%d/%m')} đến {week_end.strftime('%d/%m')}"
            else:
                rec.display_name = "Lịch phỏng vấn mới"
    
    @api.depends('week_start_date')
    def _compute_week_display(self):
        """Hiển thị tuần: 13/01 - 19/01"""
        for rec in self:
            if rec.week_start_date:
                week_end = rec.week_start_date + timedelta(days=6)
                rec.week_display = f"{rec.week_start_date.strftime('%d/%m')} - {week_end.strftime('%d/%m/%Y')}"
            else:
                rec.week_display = ""
    
    @api.model
    @api.model
    def web_search_read(self, domain=None, specification=None, offset=0, limit=None, order=None, count_limit=None):
        """Override web_search_read to ensure company schedules exist before displaying"""
        # Auto-create missing schedules when loading kanban view
        self._ensure_company_schedules()
        return super(InterviewSchedule, self).web_search_read(
            domain=domain, specification=specification, offset=offset, 
            limit=limit, order=order, count_limit=count_limit
        )
    
    def _ensure_company_schedules(self):
        """Auto-create interview schedules for all companies that don't have one"""
        Company = self.env['res.company']
        
        # Get all companies (including parent if no children)
        companies = Company.search([])
        
        # Get next Monday
        today = datetime.today()
        days_until_monday = (7 - today.weekday()) % 7
        if days_until_monday == 0:
            days_until_monday = 7
        next_monday = today + timedelta(days=days_until_monday)
        
        for company in companies:
            #  Skip main company if it has children  
            if company.child_ids:
                continue
                
            # Check if schedule exists for this company
            existing = self.sudo().search([('company_id', '=', company.id)], limit=1)
            if not existing:
                # Create new schedule
                self.sudo().create({
                    'company_id': company.id,
                    'week_start_date': next_monday.date(),
                    'state': 'draft',
                })
                _logger.info(f"Auto-created interview schedule for {company.name}")
    
    def _compute_applicant_count(self):
        """Đếm số ứng viên được gán schedule này"""
        for rec in self:
            rec.applicant_count = self.env['hr.applicant'].search_count([
                ('interview_schedule_id', '=', rec.id)
            ])
    
    # ==================== DEFAULT VALUES ====================
    
    def _default_company(self):
        """Mặc định là company của employee hiện tại (Store Manager)"""
        employee = self.env['hr.employee'].search([
            ('user_id', '=', self.env.user.id)
        ], limit=1)
        
        if employee and employee.company_id:
            return employee.company_id
        else:
            return self.env.company
    
    def _default_week_start(self):
        """Mặc định là Thứ Hai tuần này"""
        today = fields.Date.today()
        days_since_monday = today.weekday()
        monday = today - timedelta(days=days_since_monday)
        return monday
    
    # ==================== ONCHANGE ====================
    
    @api.onchange('company_id')
    def _onchange_company_id(self):
        """Khi chọn brand → tự động fill manager"""
        if self.company_id:
            # Tìm Store Manager
            job_sm = self.env['hr.job'].search([
                ('name', 'ilike', 'Store Manager'),
                ('company_id', '=', self.company_id.id)
            ], limit=1)
            
            if job_sm:
                employee_sm = self.env['hr.employee'].search([
                    ('job_id', '=', job_sm.id),
                    ('company_id', '=', self.company_id.id)
                ], limit=1)
                self.manager_id = employee_sm if employee_sm else False
            else:
                self.manager_id = False
    
    # ==================== ACTIONS ====================
    
    def action_confirm(self):
        """Xác nhận lịch phỏng vấn"""
        self.ensure_one()
        self.write({'state': 'confirmed'})
        _logger.info(f"Đã xác nhận lịch PV: {self.display_name}")
        
        # Reload form để refresh buttons và state bar
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }
    
    def action_set_draft(self):
        """Chuyển về nháp để sửa"""
        self.write({'state': 'draft'})
        _logger.info(f"Lịch {self.display_name} chuyển về nháp")
    
    # ==================== AUTO-CREATE SCHEDULES ====================
    
    @api.model
    def auto_create_weekly_schedules(self):
        """
        Tự động tạo lịch cho tuần hiện tại cho TẤT CẢ brands nếu chưa có
        Gọi khi mở menu "Lịch phỏng vấn dự kiến"
        """
        today = fields.Date.today()
        days_since_monday = today.weekday()
        monday = today - timedelta(days=days_since_monday)
        
        # Lấy tất cả child companies (brands)
        all_companies = self.env['res.company'].sudo().search([
            '|', 
            ('parent_id', '!=', False),
            ('id', '=', self.env.company.id)
        ])
        
        created_count = 0
        
        for company in all_companies:
            # Kiểm tra xem brand này đã có lịch cho tuần này chưa (dùng sudo để bypass record rules)
            existing = self.sudo().search([
                ('company_id', '=', company.id),
                ('week_start_date', '=', monday)
            ], limit=1)
            
            if not existing:
                # Tạo placeholder schedule với ngày mặc định
                default_time = datetime.combine(monday, datetime.min.time().replace(hour=9))
                
                self.sudo().create({
                    'company_id': company.id,
                    'week_start_date': monday,
                    'interview_date_1': default_time,
                    'interview_date_2': default_time + timedelta(days=1),
                    'interview_date_3': default_time + timedelta(days=2),
                    'state': 'draft'
                })
                created_count += 1
                _logger.info(f"Tạo lịch placeholder cho brand: {company.name}")
            else:
                _logger.info(f"Brand {company.name} đã có lịch cho tuần {monday.strftime('%d/%m')}")
        
        if created_count > 0:
            _logger.info(f"Đã tạo {created_count} lịch placeholder cho tuần {monday.strftime('%d/%m')}")
        
        return True
    
    # ==================== CONSTRAINTS ====================
    
    @api.constrains('interview_date_1', 'interview_date_2', 'interview_date_3', 'week_start_date')
    def _check_dates_in_week(self):
        """Kiểm tra 3 ngày phải nằm trong tuần được chọn"""
        for rec in self:
            week_end = rec.week_start_date + timedelta(days=6)
            
            for date_field in [rec.interview_date_1, rec.interview_date_2, rec.interview_date_3]:
                if date_field:
                    date_only = date_field.date()
                    if not (rec.week_start_date <= date_only <= week_end):
                        raise exceptions.ValidationError(
                            f"Ngày {date_field.strftime('%d/%m/%Y')} không nằm trong tuần "
                            f"{rec.week_start_date.strftime('%d/%m')} - {week_end.strftime('%d/%m')}"
                        )
    
    @api.model
    def create(self, vals):
        """Override create để log"""
        record = super().create(vals)
        _logger.info(f"Tạo lịch PV mới cho brand {record.company_id.name}")
        return record
