# -*- coding: utf-8 -*-
from datetime import datetime, timedelta
import pytz

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class ShiftLog(models.Model):
    _name = 'shift.log'
    _description = 'Nhật Ký Ca Làm Việc'
    _order = 'date desc, shift_id'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(
        string='Tên',
        compute='_compute_name',
        store=True,
    )
    pos_config_id = fields.Many2one(
        'pos.config',
        string='Cửa Hàng (POS)',
        required=True,
        tracking=True,
    )
    date = fields.Date(
        string='Ngày',
        required=True,
        default=fields.Date.context_today,
        tracking=True,
    )
    shift_id = fields.Many2one(
        'restaurant.shift',
        string='Ca',
        required=True,
        tracking=True,
    )
    mic_id = fields.Many2one(
        'hr.employee',
        string='MIC (Người Đứng Ca)',
        tracking=True,
    )
    department_id = fields.Many2one(
        'hr.department',
        string='Phòng Ban',
        related='pos_config_id.department_id',
        store=True,
        index=True,
    )
    start_datetime = fields.Datetime(
        string='Thời Gian Bắt Đầu',
        compute='_compute_datetimes',
        store=True,
    )
    end_datetime = fields.Datetime(
        string='Thời Gian Kết Thúc',
        compute='_compute_datetimes',
        store=True,
    )
    state = fields.Selection([
        ('draft', 'Nháp'),
        ('preparing', 'Chuẩn Bị'),
        ('running', 'Đang Chạy'),
        ('evaluating', 'Đánh Giá'),
        ('done', 'Hoàn Thành'),
    ], string='Trạng Thái', default='draft', tracking=True)

    @api.depends('date', 'shift_id')
    def _compute_datetimes(self):
        for rec in self:
            if not rec.date or not rec.shift_id:
                rec.start_datetime = False
                rec.end_datetime = False
                continue

            # Tính start/end datetime của ca (giờ địa phương → UTC)
            tz = self.env.user.tz or 'Asia/Ho_Chi_Minh'
            local_tz = pytz.timezone(tz)

            hour_from = rec.shift_id.hour_from
            hour_to = rec.shift_id.hour_to

            h_from = int(hour_from)
            m_from = int(round((hour_from - h_from) * 60))
            h_to = int(hour_to)
            m_to = int(round((hour_to - h_to) * 60))

            # Thời gian bắt đầu ca (local)
            start_naive = datetime.combine(rec.date, datetime.min.time()).replace(
                hour=h_from, minute=m_from
            )
            start_local = local_tz.localize(start_naive)

            # Xử lý ca qua đêm (ON: 22:00 - 6:45 → end_date = ngày hôm sau)
            if hour_to <= hour_from:
                end_date = rec.date + timedelta(days=1)
            else:
                end_date = rec.date

            end_naive = datetime.combine(end_date, datetime.min.time()).replace(
                hour=h_to, minute=m_to
            )
            end_local = local_tz.localize(end_naive)

            # Convert sang UTC
            rec.start_datetime = start_local.astimezone(pytz.utc).replace(tzinfo=None)
            rec.end_datetime = end_local.astimezone(pytz.utc).replace(tzinfo=None)

    # --- KPI Fields ---
    gc_projected = fields.Float(string="GC's Projected", help="Lượng khách dự kiến")
    gc_actual = fields.Float(string="GC's Actual", help="Lượng khách thực tế")
    sales_projected = fields.Float(string='Sales Projected', help='Doanh thu dự kiến')
    sales_actual = fields.Float(string='Sales Actual', help='Doanh thu thực tế')
    labor_hours = fields.Float(
        string='Labor Hours',
        compute='_compute_labor_hours',
        store=True,
        help='Tổng số giờ làm việc của nhân viên trong ca',
    )

    # --- Relational ---
    employee_line_ids = fields.One2many(
        'shift.log.employee', 'shift_log_id',
        string='Nhân Viên Trong Ca',
    )
    checklist_line_ids = fields.One2many(
        'shift.log.checklist.line', 'shift_log_id',
        string='Checklist',
    )

    # --- Post-shift ---
    best_employee_id = fields.Many2one(
        'hr.employee',
        string='Nhân Viên Xuất Sắc',
    )
    best_employee_reason = fields.Text(string='Lý Do Chọn NV Xuất Sắc')
    handover_notes = fields.Text(string='Ghi Chú Bàn Giao')

    _sql_constraints = [
        ('unique_shift_log', 'unique(pos_config_id, date, shift_id)',
         'Mỗi cửa hàng chỉ có 1 log cho mỗi ca trong ngày!'),
    ]

    @api.depends('pos_config_id', 'date', 'shift_id')
    def _compute_name(self):
        for rec in self:
            pos_name = rec.pos_config_id.name or ''
            shift_name = rec.shift_id.name or ''
            date_str = fields.Date.to_string(rec.date) if rec.date else ''
            rec.name = f"{pos_name} - {shift_name} - {date_str}"

    @api.depends('employee_line_ids', 'employee_line_ids.working_hours')
    def _compute_labor_hours(self):
        for rec in self:
            rec.labor_hours = sum(rec.employee_line_ids.mapped('working_hours'))

    # --- State transitions ---
    def action_prepare(self):
        self._generate_checklist_lines()
        self.write({'state': 'preparing'})

    def action_start(self):
        self.write({'state': 'running'})

    def action_evaluate(self):
        self.write({'state': 'evaluating'})

    def action_done(self):
        self.write({'state': 'done'})

    def action_reset_draft(self):
        self.write({'state': 'draft'})

    # --- Pull employees from planning ---
    def action_pull_employees(self):
        """Lấy danh sách nhân viên từ planning.slot trùng ngày + giờ ca.

        Ví dụ: Ca AM 6:00-14:30, nhân viên có lịch 8:00-15:00
        → overlap = 8:00 đến 14:30 = 6 tiếng 30 phút
        """
        self.ensure_one()
        if not self.date or not self.shift_id:
            raise ValidationError(_("Vui lòng chọn Ngày và Ca trước!"))

        # Tính start/end datetime của ca (giờ địa phương → UTC)
        tz = self.env.user.tz or 'Asia/Ho_Chi_Minh'
        local_tz = pytz.timezone(tz)

        hour_from = self.shift_id.hour_from
        hour_to = self.shift_id.hour_to

        h_from = int(hour_from)
        m_from = int(round((hour_from - h_from) * 60))
        h_to = int(hour_to)
        m_to = int(round((hour_to - h_to) * 60))

        # Thời gian bắt đầu ca (local)
        start_naive = datetime.combine(self.date, datetime.min.time()).replace(
            hour=h_from, minute=m_from
        )
        start_local = local_tz.localize(start_naive)

        # Xử lý ca qua đêm (ON: 22:00 - 6:45 → end_date = ngày hôm sau)
        if hour_to <= hour_from:
            end_date = self.date + timedelta(days=1)
        else:
            end_date = self.date

        end_naive = datetime.combine(end_date, datetime.min.time()).replace(
            hour=h_to, minute=m_to
        )
        end_local = local_tz.localize(end_naive)

        # Convert sang UTC (planning.slot lưu UTC)
        start_utc = start_local.astimezone(pytz.utc).replace(tzinfo=None)
        end_utc = end_local.astimezone(pytz.utc).replace(tzinfo=None)

        # Lấy department thuộc POS này
        departments = self.env['hr.department'].search([
            ('pos_config_id', '=', self.pos_config_id.id),
        ])

        if not departments:
            raise ValidationError(_(
                "Không tìm thấy phòng ban nào gắn với POS '%s'. "
                "Hãy gán POS cho phòng ban trong HR > Departments."
            ) % self.pos_config_id.name)

        # Tìm planning.slot có thời gian giao nhau với ca + thuộc department POS
        # Điều kiện giao nhau: slot.start < ca.end AND slot.end > ca.start
        slots = self.env['planning.slot'].search([
            ('employee_id', '!=', False),
            ('employee_id.department_id', 'in', departments.ids),
            ('start_datetime', '<', end_utc),
            ('end_datetime', '>', start_utc),
        ])

        existing_emp_ids = set(self.employee_line_ids.mapped('employee_id').ids)
        new_lines = []
        for slot in slots:
            emp = slot.employee_id
            if emp.id in existing_emp_ids:
                continue

            # Tính giờ làm = phần giao nhau giữa slot và ca
            overlap_start = max(slot.start_datetime, start_utc)
            overlap_end = min(slot.end_datetime, end_utc)
            hours = (overlap_end - overlap_start).total_seconds() / 3600.0

            if hours > 0:
                new_lines.append((0, 0, {
                    'employee_id': emp.id,
                    'working_hours': round(hours, 2),
                }))
                existing_emp_ids.add(emp.id)

        if new_lines:
            self.write({'employee_line_ids': new_lines})
        else:
            raise ValidationError(_(
                "Không tìm thấy nhân viên nào trong planning cho ca %s ngày %s.\n"
                "Kiểm tra: planning.slot phải có employee và thời gian giao nhau với ca (%s → %s UTC)."
            ) % (self.shift_id.name, self.date, start_utc, end_utc))

    # --- Generate checklist lines from master ---
    def _generate_checklist_lines(self):
        """Tạo dòng checklist từ master data nếu chưa có."""
        for rec in self:
            existing = rec.checklist_line_ids.mapped('checklist_id').ids
            checklists = self.env['shift.log.checklist'].search([
                ('id', 'not in', existing),
            ])
            lines = [(0, 0, {
                'checklist_id': cl.id,
                'shift_phase': cl.shift_phase,
            }) for cl in checklists]
            if lines:
                rec.write({'checklist_line_ids': lines})

    # --- Matrix UI RPC Methods ---
    @api.model
    def get_matrix_data(self, month, year, pos_config_id):
        """Trả về dữ liệu ma trận cho giao diện gán MIC."""
        month = int(month)
        year = int(year)
        pos_config_id = int(pos_config_id)

        # Lấy các ngày trong tháng
        import calendar as py_calendar
        _, last_day = py_calendar.monthrange(year, month)
        dates = [datetime(year, month, d).date() for d in range(1, last_day + 1)]

        # Tìm logs trong tháng của POS này
        logs = self.search([
            ('pos_config_id', '=', pos_config_id),
            ('date', '>=', dates[0]),
            ('date', '<=', dates[-1]),
        ])

        # Lấy tất cả các loại ca của POS này (từ cấu hình)
        pos_config = self.env['pos.config'].browse(pos_config_id)
        shift_ids = (pos_config.main_shift_ids | pos_config.secondary_shift_ids).sorted('hour_from')
        
        # Build matrix
        matrix = []
        for d in dates:
            row = {
                'date': fields.Date.to_string(d),
                'day_name': d.strftime('%a'),
                'shifts': {}
            }
            for s in shift_ids:
                log = logs.filtered(lambda l: l.date == d and l.shift_id == s)
                if log:
                    log = log[0]
                    conflict = False
                    if log.mic_id:
                        # 1. Check Leaves
                        leave = self.env['resource.calendar.leaves'].search([
                            ('resource_id', '=', log.mic_id.resource_id.id),
                            ('date_from', '<=', log.end_datetime),
                            ('date_to', '>=', log.start_datetime),
                        ], limit=1)
                        if leave:
                            conflict = 'leave'
                        
                        # 2. Check Planning Conflicts (Other slots for this MIC)
                        else:
                            planning_conflict = self.env['planning.slot'].search([
                                ('employee_id', '=', log.mic_id.id),
                                ('start_datetime', '<', log.end_datetime),
                                ('end_datetime', '>', log.start_datetime),
                            ], limit=1)
                            if planning_conflict:
                                conflict = 'planning'

                    row['shifts'][s.id] = {
                        'log_id': log.id,
                        'shift_name': s.name,
                        'mic_id': log.mic_id.id,
                        'mic_name': log.mic_id.name or 'Trống',
                        'state': log.state,
                        'conflict': conflict,
                    }
                else:
                    row['shifts'][s.id] = False
            matrix.append(row)

        return {
            'matrix': matrix,
            'shifts': [{'id': s.id, 'name': s.name} for s in shift_ids],
            'pos_name': pos_config.name,
        }

    def action_bulk_assign_mic(self, mic_id):
        """Gán MIC hàng loạt cho các logs đang chọn."""
        if not mic_id:
            return False
        self.write({'mic_id': mic_id})
        return True

    @api.model
    def action_copy_day_schedule(self, from_date, to_dates, pos_config_id):
        """Copy MIC assignment từ 1 ngày sang các ngày khác."""
        from_date = fields.Date.from_string(from_date)
        to_dates = [fields.Date.from_string(d) for d in to_dates]
        
        source_logs = self.search([
            ('pos_config_id', '=', pos_config_id),
            ('date', '=', from_date),
        ])
        if not source_logs:
            return False
            
        for d in to_dates:
            target_logs = self.search([
                ('pos_config_id', '=', pos_config_id),
                ('date', '=', d),
            ])
            for s_log in source_logs:
                t_log = target_logs.filtered(lambda l: l.shift_id == s_log.shift_id)
                if t_log:
                    t_log.write({'mic_id': s_log.mic_id.id})
        return True
