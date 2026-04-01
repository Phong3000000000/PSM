# -*- coding: utf-8 -*-
"""
Model: Interview Schedule
Mô tả: Lịch phỏng vấn theo Brand/Company
"""

from odoo import models, fields, api, exceptions
from datetime import datetime, timedelta, date
from pytz import timezone
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
        compute='_compute_company_id',
        store=True,
        readonly=False,
        tracking=True,
        help="Brand/Cửa hàng (tự động theo Phòng ban)"
    )
    
    department_id = fields.Many2one(
        'hr.department',
        string="Phòng ban",
        required=True,
        tracking=True,
        help="Phòng ban / Cửa hàng cụ thể"
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

    week_end_date = fields.Date(
        string="Tuần kết thúc",
        compute='_compute_week_end_date',
        store=True,
        help="Ngày Chủ Nhật của tuần"
    )

    is_current_week = fields.Boolean(
        string="Tuần hiện tại",
        compute='_compute_is_current_week',
        search='_search_is_current_week',
        help="Dùng cho bộ lọc Tuần này trong search view"
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

    interview_date_1_vn = fields.Char(string="Ngày PV 1 (VN)", compute="_compute_interview_dates_vn")
    interview_date_2_vn = fields.Char(string="Ngày PV 2 (VN)", compute="_compute_interview_dates_vn")
    interview_date_3_vn = fields.Char(string="Ngày PV 3 (VN)", compute="_compute_interview_dates_vn")

    def _compute_interview_dates_vn(self):
        for rec in self:
            rec.interview_date_1_vn = rec.format_datetime_vn(rec.interview_date_1)
            rec.interview_date_2_vn = rec.format_datetime_vn(rec.interview_date_2)
            rec.interview_date_3_vn = rec.format_datetime_vn(rec.interview_date_3)

    def format_datetime_vn(self, dt):
        """Format datetime to dd/MM/YYYY hh:mm AM/PM"""
        if not dt:
            return ""
        import pytz
        from odoo.fields import Datetime
        
        if isinstance(dt, str):
            dt = Datetime.from_string(dt)
            
        tz = pytz.timezone('Asia/Ho_Chi_Minh')
        if not dt.tzinfo:
            # Odoo Datetime fields are naive UTC
            dt = pytz.utc.localize(dt).astimezone(tz)
        else:
            dt = dt.astimezone(tz)
            
        return dt.strftime('%d/%m/%Y %I:%M %p')

    max_candidates_slot_1 = fields.Integer(
        string="Tối đa ứng viên - Ngày PV 1",
        default=1,
        tracking=True,
        help="Số ứng viên tối đa cho lựa chọn Ngày PV 1.",
    )

    max_candidates_slot_2 = fields.Integer(
        string="Tối đa ứng viên - Ngày PV 2",
        default=1,
        tracking=True,
        help="Số ứng viên tối đa cho lựa chọn Ngày PV 2.",
    )

    max_candidates_slot_3 = fields.Integer(
        string="Tối đa ứng viên - Ngày PV 3",
        default=1,
        tracking=True,
        help="Số ứng viên tối đa cho lựa chọn Ngày PV 3.",
    )

    slot_1_remaining = fields.Integer(
        string="Slot 1 còn lại",
        compute="_compute_slot_remaining",
        store=False,
    )

    slot_2_remaining = fields.Integer(
        string="Slot 2 còn lại",
        compute="_compute_slot_remaining",
        store=False,
    )

    slot_3_remaining = fields.Integer(
        string="Slot 3 còn lại",
        compute="_compute_slot_remaining",
        store=False,
    )

    def get_slot_availability(self):
        """Trả về object chứa số slot còn lại để gửi qua Bus Bus"""
        self.ensure_one()
        return {
            'schedule_id': self.id,
            'slot_1_remaining': self.slot_1_remaining,
            'slot_2_remaining': self.slot_2_remaining,
            'slot_3_remaining': self.slot_3_remaining,
        }
    
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
    
    @api.depends('department_id')
    def _compute_company_id(self):
        """Tự động gán Company theo Department"""
        for rec in self:
            if rec.department_id and rec.department_id.company_id:
                rec.company_id = rec.department_id.company_id
            elif not rec.company_id:
                rec.company_id = self.env.company

    @api.depends('department_id', 'week_start_date')
    def _compute_display_name(self):
        """Tên hiển thị: Department - Week"""
        for rec in self:
            if rec.department_id and rec.week_start_date:
                week_end = rec.week_start_date + timedelta(days=6)
                rec.display_name = f"{rec.department_id.name} - {rec.week_start_date.strftime('%d/%m')} đến {week_end.strftime('%d/%m')}"
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

    @api.depends('week_start_date')
    def _compute_week_end_date(self):
        """Ngày kết thúc tuần (Chủ Nhật) để filter nhanh trên search view."""
        for rec in self:
            rec.week_end_date = rec.week_start_date + timedelta(days=6) if rec.week_start_date else False

    @api.depends('week_start_date', 'week_end_date')
    def _compute_is_current_week(self):
        """Đánh dấu bản ghi thuộc tuần hiện tại theo ngày hệ thống."""
        today = fields.Date.context_today(self)
        for rec in self:
            rec.is_current_week = bool(
                rec.week_start_date and rec.week_end_date and
                rec.week_start_date <= today <= rec.week_end_date
            )

    def _search_is_current_week(self, operator, value):
        """Cho phép filter tuần hiện tại mà không cần expression động trong XML."""
        if operator not in ('=', '!='):
            return []

        bool_value = bool(value)
        if operator == '!=':
            bool_value = not bool_value

        today = fields.Date.context_today(self)
        if bool_value:
            return [('week_start_date', '<=', today), ('week_end_date', '>=', today)]
        return ['|', ('week_start_date', '>', today), ('week_end_date', '<', today)]
    
    @api.model
    def web_search_read(self, domain=None, specification=None, offset=0, limit=None, order=None, count_limit=None, **kwargs):
        """Override web_search_read to ensure company schedules exist before displaying"""
        # Auto-create missing schedules when loading kanban view
        self._ensure_company_schedules()
        return super(InterviewSchedule, self).web_search_read(
            domain=domain, specification=specification, offset=offset, 
            limit=limit, order=order, count_limit=count_limit, **kwargs
        )
    
    def _ensure_company_schedules(self):
        """Auto-create interview schedules for all departments that don't have one"""
        Department = self.env['hr.department']
        
        # Get all departments that could have schedules
        departments = Department.search([])
        
        # Get next Monday
        today = datetime.today()
        days_until_monday = (7 - today.weekday()) % 7
        if days_until_monday == 0:
            days_until_monday = 7
        next_monday = today + timedelta(days=days_until_monday)
        
        for dept in departments:
            # Check if schedule exists for this department
            existing = self.sudo().search([('department_id', '=', dept.id)], limit=1)
            if not existing:
                # Create new schedule
                self.sudo().create({
                    'department_id': dept.id,
                    'company_id': dept.company_id.id or self.env.company.id,
                    'week_start_date': next_monday.date(),
                    'state': 'draft',
                })
                _logger.info(f"Auto-created interview schedule for department {dept.name}")
    
    def _compute_applicant_count(self):
        """Đếm số ứng viên được gán schedule này"""
        for rec in self:
            rec.applicant_count = self.env['hr.applicant'].search_count([
                ('interview_schedule_id', '=', rec.id)
            ])

    @api.depends('max_candidates_slot_1', 'max_candidates_slot_2', 'max_candidates_slot_3')
    def _compute_slot_remaining(self):
        for rec in self:
            remaining_map = rec._get_slot_remaining_map()
            rec.slot_1_remaining = remaining_map.get(1, 0)
            rec.slot_2_remaining = remaining_map.get(2, 0)
            rec.slot_3_remaining = remaining_map.get(3, 0)

    def _get_capacity_for_slot(self, slot_index):
        self.ensure_one()
        capacities = {
            1: max(0, int(self.max_candidates_slot_1 or 0)),
            2: max(0, int(self.max_candidates_slot_2 or 0)),
            3: max(0, int(self.max_candidates_slot_3 or 0)),
        }
        return capacities.get(int(slot_index), 0)

    def _get_booked_count_for_slot(self, slot_index):
        self.ensure_one()
        slot_value = str(slot_index)
        return self.env['hr.applicant'].sudo().search_count([
            ('interview_schedule_id', '=', self.id),
            ('interview_booked_slot', '=', slot_value),
            ('interview_booking_status', '=', 'booked'),
            ('interview_event_id', '!=', False),
        ])

    def _get_slot_remaining_map(self):
        self.ensure_one()
        result = {}
        for slot_idx in (1, 2, 3):
            capacity = self._get_capacity_for_slot(slot_idx)
            booked = self._get_booked_count_for_slot(slot_idx)
            result[slot_idx] = max(0, capacity - booked)
        return result

    def has_remaining_for_slot(self, slot_index):
        self.ensure_one()
        return self._get_slot_remaining_map().get(int(slot_index), 0) > 0
    
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
    
    @api.onchange('department_id')
    def _onchange_department_id(self):
        """Khi chọn phòng ban → tự động fill manager"""
        if self.department_id:
            # Tìm Store Manager cho brand của department này
            company_id = self.department_id.company_id.id or self.env.company.id
            job_sm = self.env['hr.job'].search([
                ('name', 'ilike', 'Store Manager'),
                ('company_id', '=', company_id)
            ], limit=1)
            
            if job_sm:
                employee_sm = self.env['hr.employee'].search([
                    ('job_id', '=', job_sm.id),
                    ('company_id', '=', company_id)
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
    
    @api.model
    def _cron_auto_create_next_week_schedules(self):
        """
        Cron job chạy vào Chủ Nhật 23:00 hàng tuần
        Tự động tạo lịch cho tuần mới từ các lịch đã xác nhận của tuần hiện tại
        """
        today = fields.Date.today()
        # Xác định ngày Thứ Hai của tuần hiện tại
        days_since_monday = today.weekday()
        current_monday = today - timedelta(days=days_since_monday)
        next_monday = current_monday + timedelta(days=7)
        
        # 1. Tìm tất cả interview.schedule của tuần hiện tại với state = 'confirmed'
        confirmed_schedules = self.search([
            ('week_start_date', '=', current_monday),
            ('state', '=', 'confirmed')
        ])
        
        created_count = 0
        for schedule in confirmed_schedules:
            # 4. Tránh tạo trùng: kiểm tra nếu đã có lịch cho department ở tuần mới thì skip
            existing_next_week = self.search([
                ('department_id', '=', schedule.department_id.id),
                ('week_start_date', '=', next_monday)
            ], limit=1)
            
            if existing_next_week:
                continue
            
            # 2. Tạo bản copy mới cho tuần tới (state = 'draft')
            vals = {
                'department_id': schedule.department_id.id,
                'company_id': schedule.company_id.id,
                'week_start_date': next_monday,
                'state': 'draft',
                'max_candidates_slot_1': schedule.max_candidates_slot_1,
                'max_candidates_slot_2': schedule.max_candidates_slot_2,
                'max_candidates_slot_3': schedule.max_candidates_slot_3,
                'store_address': schedule.store_address,
            }
            
            # Cập nhật 3 mốc thời gian (+7 ngày)
            if schedule.interview_date_1:
                vals['interview_date_1'] = schedule.interview_date_1 + timedelta(days=7)
            if schedule.interview_date_2:
                vals['interview_date_2'] = schedule.interview_date_2 + timedelta(days=7)
            if schedule.interview_date_3:
                vals['interview_date_3'] = schedule.interview_date_3 + timedelta(days=7)
            
            self.create(vals)
            created_count += 1
            
        _logger.info(f"Cron: Đã tự động tạo {created_count} lịch phỏng vấn cho tuần mới ({next_monday})")
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

    @api.constrains('max_candidates_slot_1', 'max_candidates_slot_2', 'max_candidates_slot_3')
    def _check_max_candidates_per_slot(self):
        for rec in self:
            if rec.max_candidates_slot_1 < 0 or rec.max_candidates_slot_2 < 0 or rec.max_candidates_slot_3 < 0:
                raise exceptions.ValidationError("Số ứng viên tối đa cho từng lựa chọn không được âm.")
    
    @api.model
    def create(self, vals):
        """Override create để log"""
        record = super().create(vals)
        _logger.info(f"Tạo lịch PV mới cho department {record.department_id.name}")
        return record

    def _sync_survey_q14_answers(self):
        """
        Cập nhật đáp án Q14 trong 3 survey theo ngày PV của lịch NÀY (self là 1 record).
        Gọi từ action_send_interview_invitation() ngay trước khi gửi email.
        Format: "Ngày PV 1: Thứ X, DD/MM/YYYY HH:MM"
        """
        self.ensure_one()
        # Mapping XML ID → (ans1, ans2, ans3)
        Q14_MAP = [
            (
                'M02_P0204_00.ft_q14_ans1',
                'M02_P0204_00.ft_q14_ans2',
                'M02_P0204_00.ft_q14_ans3',
            ),
            (
                'M02_P0204_00.pt_q14_ans1',
                'M02_P0204_00.pt_q14_ans2',
                'M02_P0204_00.pt_q14_ans3',
            ),
            (
                'M02_P0204_00.mg_q14_ans1',
                'M02_P0204_00.mg_q14_ans2',
                'M02_P0204_00.mg_q14_ans3',
            ),
        ]
        VN_TZ = timezone('Asia/Ho_Chi_Minh')
        WEEKDAY_VN = ['Thứ Hai', 'Thứ Ba', 'Thứ Tư', 'Thứ Năm', 'Thứ Sáu', 'Thứ Bảy', 'Chủ Nhật']

        def _fmt_date(dt):
            if not dt:
                return '(chưa có ngày)'
            # Convert từ UTC sang VN timezone
            dt_vn = dt.replace(tzinfo=timezone('UTC')).astimezone(VN_TZ)
            weekday = WEEKDAY_VN[dt_vn.weekday()]
            return f"{weekday}, {dt_vn.strftime('%d/%m/%Y %H:%M')}"

        dates = [
            _fmt_date(self.interview_date_1),
            _fmt_date(self.interview_date_2),
            _fmt_date(self.interview_date_3),
        ]
        labels = [
            f"Ngày PV 1: {dates[0]}",
            f"Ngày PV 2: {dates[1]}",
            f"Ngày PV 3: {dates[2]}",
        ]

        for ans_ids in Q14_MAP:
            for xml_id, label in zip(ans_ids, labels):
                try:
                    ans = self.env.ref(xml_id, raise_if_not_found=False)
                    if ans:
                        ans.sudo().write({'value': label})
                except Exception as e:
                    _logger.warning(f"[Q14 SYNC] Không thể cập nhật {xml_id}: {e}")

        _logger.info(
            f"[Q14 SYNC] Đã sync đáp án Q14 theo lịch '{self.display_name}' ({self.company_id.name}): "
            f"{dates[0]} | {dates[1]} | {dates[2]}"
        )

