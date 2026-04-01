# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from datetime import date, timedelta, datetime
import random

# ─────────────────────────────────────────────────────────────────────────────
#  TẤT CẢ WORK ENTRY TYPES từ M02_P0207_data  (xml_id → code)
#  Leave types (is_leave=True) → tạo hr.work.entry ngày nghỉ
#  OT types   (is_leave=False) → tạo giờ OT trong hr.work.entry
# ─────────────────────────────────────────────────────────────────────────────
LEAVE_XMLIDS = {
    # xmlid (module.record_id)                       : code
    'M02_P0207_data.work_entry_type_AL':              'AL',        # Annual Leave 12
    'M02_P0207_data.work_entry_type_AL14':            'AL14',      # Annual Leave 14
    'M02_P0207_data.work_entry_type_AL18':            'AL18',      # Annual Leave 18
    'M02_P0207_data.work_entry_type_BT':              'BT',        # Business Trip
    'M02_P0207_data.work_entry_type_C':               'C',         # Compensation
    'M02_P0207_data.work_entry_type_MA':              'MA',        # Maternity Leave
    'M02_P0207_data.work_entry_type_NS':              'NS',        # No Show
    'M02_P0207_data.work_entry_type_PL':              'PL',        # Paid Leave
    'M02_P0207_data.work_entry_type_SAL':             'SAL',       # Sabbatical
    'M02_P0207_data.work_entry_type_SD':              'SD',        # Sick – Doctor Certificate
    'M02_P0207_data.work_entry_type_SI':              'SI',        # Sick – Social Insurance
    'M02_P0207_data.work_entry_type_SN':              'SN',        # Sick – No Certificate
    'M02_P0207_data.work_entry_type_TR':              'TR',        # Training
    'M02_P0207_data.work_entry_type_UEL':             'UEL',       # Unexpected Leave
    'M02_P0207_data.work_entry_type_UL':              'UL',        # Unpaid Leave
    'M02_P0207_data.work_entry_type_OPS_LEAVE_AL':    'OPS_LEAVE_AL',   # Annual Leave (OPS)
    'M02_P0207_data.work_entry_type_OPS_NS_NO_SHOW':  'OPS_NS_NO_SHOW', # No Show (Unjustified)
}

OT_XMLIDS = {
    'M02_P0207_data.work_entry_type_OTH':    'OTH',    # Holiday OT
    'M02_P0207_data.work_entry_type_OTN':    'OTN',    # Weekday Night OT
    'M02_P0207_data.work_entry_type_OTTET':  'OTTET',  # TET OT
    'M02_P0207_data.work_entry_type_OTW':    'OTW',    # Weekend OT
}

NORMAL_XMLID = 'M02_P0207_data.work_entry_type_NORMAL'   # Normal Working

# Profile: list of (xml_id, avg_days_per_month)
LEAVE_PROFILES = {
    'normal': [
        ('M02_P0207_data.work_entry_type_AL', 1),
    ],
    'with_sick': [
        ('M02_P0207_data.work_entry_type_AL', 1),
        ('M02_P0207_data.work_entry_type_SD', 1),
    ],
    'with_no_show': [
        ('M02_P0207_data.work_entry_type_AL',  1),
        ('M02_P0207_data.work_entry_type_OPS_NS_NO_SHOW', 1),
    ],
    'full_mix': [
        ('M02_P0207_data.work_entry_type_AL',  1),
        ('M02_P0207_data.work_entry_type_SD',  1),
        ('M02_P0207_data.work_entry_type_PL',  1),
        ('M02_P0207_data.work_entry_type_BT',  2),
        ('M02_P0207_data.work_entry_type_TR',  1),
    ],
}


class M02P0207DataLoader(models.TransientModel):
    _name = 'm02.p0207.data.loader'
    _description = 'M02_P0207 Data Loader Wizard'

    # ── Thông tin cơ bản ────────────────────────────────────────────────────
    employee_ids = fields.Many2many('hr.employee', string='Employees')
    start_date = fields.Date(
        string='Start Date',
        default=lambda self: date.today().replace(day=1),
    )
    end_date = fields.Date(
        string='End Date',
        default=lambda self: (
            date.today().replace(day=28) + timedelta(days=4)
        ).replace(day=1) - timedelta(days=1),
    )

    # ── Tạo nhân viên test ──────────────────────────────────────────────────
    create_employees = fields.Boolean(string='Create Test Employees', default=False)
    employee_count   = fields.Integer(string='Number of Employees', default=5)

    # ── Cấu hình bảng công ─────────────────────────────────────────────────
    leave_profile = fields.Selection([
        ('normal',       'Bình thường (chỉ nghỉ phép AL)'),
        ('with_sick',    'Có nghỉ bệnh (AL + SD)'),
        ('with_no_show', 'Có vắng không phép (AL + NS unjustified)'),
        ('full_mix',     'Mix đầy đủ (AL + SD + PL + BT + TR)'),
        ('none',         'Không tạo ngày nghỉ (toàn ngày làm)'),
    ], string='Cấu hình ngày nghỉ', default='normal')

    include_overtime = fields.Boolean(string='Có giờ OT (OTN/OTW)', default=False)

    # ── Tạo dữ liệu nhân viên giữa tháng ────────────────────────────────────
    create_mid_month = fields.Boolean(
        string='Tạo nhân viên giữa tháng',
        default=False,
        help='Một số nhân viên sẽ được gắn quy trình offboarding/onboarding đang chờ duyệt, '
             'để khi chạy "Kiểm tra điều kiện" họ tự động vào danh sách giữa tháng.',
    )
    mid_month_count = fields.Integer(
        string='Số nhân viên giữa tháng',
        default=1,
        help='Số nhân viên (trong danh sách đã chọn/tạo) sẽ có approval request offboarding pending.',
    )
    mid_month_type = fields.Selection([
        ('offboarding', 'Offboarding (Nghỉ việc)'),
        ('onboarding',  'Onboarding (Thử việc)'),
    ], string='Loại quy trình', default='offboarding')

    # ════════════════════════════════════════════════════════════════════════
    #  HELPERS
    # ════════════════════════════════════════════════════════════════════════

    def _get_ops_structure(self):
        structure_type = (
            self.env.ref('M02_P0207_data.structure_type_ops_payroll', raise_if_not_found=False)
            or self.env.ref('hr_payroll.structure_type_employee', raise_if_not_found=False)
        )
        if not structure_type:
            structure_type = self.env['hr.payroll.structure.type'].create({
                'name': 'Công thức tính lương OPS', 'wage_type': 'monthly',
            })
        struct = (
            self.env.ref('M02_P0207_data.structure_ops_payroll', raise_if_not_found=False)
            or self.env['hr.payroll.structure'].search(
                [('type_id', '=', structure_type.id)], limit=1)
        )
        if not struct:
            struct = self.env['hr.payroll.structure'].create({
                'name': 'OPS Payroll', 'code': 'OPS_PAYROLL',
                'type_id': structure_type.id, 'active': True,
            })
        if not structure_type.default_struct_id:
            structure_type.write({'default_struct_id': struct.id})
        return structure_type, struct

    def _resolve_wet(self, xml_id):
        """Lấy hr.work.entry.type theo xml_id từ M02_P0207_data."""
        return self.env.ref(xml_id, raise_if_not_found=False)

    def _pick_leave_days(self, all_days):
        """
        Chọn ngẫu nhiên ngày nghỉ từ bảng ngày trong kỳ.
        Trả về: dict {date: hr.work.entry.type}
        """
        if self.leave_profile == 'none':
            return {}
        profile = LEAVE_PROFILES.get(self.leave_profile, [])
        available = list(all_days)
        leave_days = {}
        for xml_id, avg in profile:
            wet = self._resolve_wet(xml_id)
            if not wet:
                continue
            count = max(0, avg + random.randint(-1, 1))
            count = min(count, len(available))
            chosen = random.sample(available, count)
            for d in chosen:
                leave_days[d] = wet
                available.remove(d)
        return leave_days

    def _date_to_utc(self, d, hour_local):
        """Chuyển giờ địa phương VN (UTC+7) sang UTC datetime string."""
        dt_local = datetime(d.year, d.month, d.day) + timedelta(hours=hour_local)
        dt_utc   = dt_local - timedelta(hours=7)
        return fields.Datetime.to_string(dt_utc)

    # ════════════════════════════════════════════════════════════════════════
    #  TẠO NHÂN VIÊN
    # ════════════════════════════════════════════════════════════════════════

    def _create_test_employees(self, structure_type):
        Employee = self.env['hr.employee']
        result   = self.env['hr.employee']
        for i in range(self.employee_count):
            emp = Employee.create({
                'name':                'Test Employee %d' % (i + 1),
                'work_email':          'test.emp02.%d@example.com' % (i + 1),
                'wage':                round(random.uniform(8_000_000, 35_000_000), -3),
                'structure_type_id':   structure_type.id,
                'contract_date_start': self.start_date,
                'date_version':        self.start_date,
            })
            if not emp.work_contact_id:
                partner = self.env['res.partner'].create({
                    'name': emp.name, 'email': emp.work_email,
                    'company_id': self.env.company.id,
                })
                emp.work_contact_id = partner.id
            if emp.work_contact_id:
                bank = self.env['res.partner.bank'].create({
                    'acc_number':       '190%07d' % random.randint(1_000_000, 9_999_999),
                    'partner_id':       emp.work_contact_id.id,
                    'allow_out_payment': True,
                })
                emp.write({'bank_account_ids': [fields.Command.link(bank.id)]})
            result += emp
        return result

    # ════════════════════════════════════════════════════════════════════════
    #  TẠO ATTENDANCE (ngày làm) + WORK ENTRY (ngày nghỉ)
    # ════════════════════════════════════════════════════════════════════════

    def _gen_work_data_for_employee(self, employee, leave_days):
        """
        Với mỗi ngày trong kỳ (trừ Chủ Nhật):
          - Nếu là ngày nghỉ (leave_days) → tạo hr.work.entry với work_entry_type tương ứng
          - Nếu là ngày làm → tạo hr.attendance (Odoo tự sinh NORMAL work entry)
        """
        Attendance  = self.env['hr.attendance']
        WorkEntry   = self.env['hr.work.entry']
        normal_wet  = self._resolve_wet(NORMAL_XMLID)

        cur = self.start_date
        while cur <= self.end_date:
            is_sunday = (cur.weekday() == 6)
            if is_sunday:
                cur += timedelta(days=1)
                continue

            if cur in leave_days:
                # ── Tạo hr.work.entry cho ngày nghỉ ──
                wet = leave_days[cur]
                date_start_utc = self._date_to_utc(cur, 8.0)   # 8h sáng VN
                date_stop_utc  = self._date_to_utc(cur, 17.0)  # 5h chiều VN
                try:
                    WorkEntry.create({
                        'name':               '%s – %s' % (wet.name, employee.name),
                        'employee_id':        employee.id,
                        'work_entry_type_id': wet.id,
                        'date_start':         date_start_utc,
                        'date_stop':          date_stop_utc,
                        'company_id':         self.env.company.id,
                    })
                except Exception:
                    pass  # bỏ qua nếu lỗi xung đột
            else:
                # ── Tạo hr.attendance cho ngày làm ──
                check_in_local  = 7 + random.uniform(0, 1)          # 7:00–8:00 VN
                worked_hours    = 8 + random.uniform(0, 1)           # 8–9h
                if self.include_overtime:
                    worked_hours += random.uniform(0, 2)
                check_out_local = check_in_local + worked_hours

                Attendance.create({
                    'employee_id': employee.id,
                    'check_in':   self._date_to_utc(cur, check_in_local),
                    'check_out':  self._date_to_utc(cur, check_out_local),
                })

            cur += timedelta(days=1)

    # ════════════════════════════════════════════════════════════════════════
    #  TẠO APPROVAL REQUEST GIẢ CHO NHÂN VIÊN GIỮA THÁNG
    # ════════════════════════════════════════════════════════════════════════

    def _create_mid_month_approvals(self, employees):
        """
        Tạo approval.request với state 'pending' cho một số nhân viên.
        Khi check_payment_conditions() chạy sẽ thấy request này và đánh dấu giữa tháng.
        """
        if not employees or not self.create_mid_month:
            return

        # Lấy category tương ứng
        if self.mid_month_type == 'offboarding':
            cat_xmlid = 'M02_P0213_00.approval_category_resignation'
        else:
            cat_xmlid = 'M02_P0213_00.approval_category_onboarding'

        category = self.env.ref(cat_xmlid, raise_if_not_found=False)
        if not category:
            # Tìm category bất kỳ có sẵn trong hệ thống làm placeholder
            category = self.env['approval.category'].search([], limit=1)
        if not category:
            # Không có category nào → bỏ qua (không tạo được approval request)
            return

        count = min(self.mid_month_count, len(employees))
        mid_month_emps = employees[:count]

        for emp in mid_month_emps:
            # Đảm bảo nhân viên có user để làm request_owner_id
            if not emp.user_id:
                continue
            # Tạo approval request pending
            req = self.env['approval.request'].create({
                'name': '[TEST] %s - %s' % (
                    'Offboarding' if self.mid_month_type == 'offboarding' else 'Onboarding',
                    emp.name,
                ),
                'category_id': category.id,
                'request_owner_id': emp.user_id.id,
                'request_status': 'new',
                'date_confirmed': fields.Datetime.now(),
            })
            # Đẩy sang pending để check_payment_conditions() nhận diện
            req.sudo().write({'request_status': 'pending'})

    # ════════════════════════════════════════════════════════════════════════
    #  ACTION CHÍNH
    # ════════════════════════════════════════════════════════════════════════

    def action_generate_data(self):
        self.ensure_one()
        AttendanceSheet = self.env['hr.attendance.sheet']

        structure_type, _struct = self._get_ops_structure()

        target_employees = self.employee_ids
        if self.create_employees:
            target_employees = self._create_test_employees(structure_type)

        # Danh sách tất cả ngày trong kỳ (trừ CN được lọc sau)
        all_days = []
        cur = self.start_date
        while cur <= self.end_date:
            if cur.weekday() != 6:          # bỏ CN
                all_days.append(cur)
            cur += timedelta(days=1)

        for employee in target_employees:
            leave_days = self._pick_leave_days(all_days)
            self._gen_work_data_for_employee(employee, leave_days)

            existing = AttendanceSheet.search([
                ('employee_id', '=', employee.id),
                ('start_date',  '=', self.start_date),
                ('end_date',    '=', self.end_date),
            ], limit=1)
            if not existing:
                sheet = AttendanceSheet.create({
                    'employee_id': employee.id,
                    'start_date':  self.start_date,
                    'end_date':    self.end_date,
                    'name': _('Sheet %s - %s') % (
                        employee.name, self.start_date.strftime('%m/%Y')),
                })
            else:
                sheet = existing

            sheet.compute_sheet_hours()

        # Tạo approval requests giữa tháng (nếu có)
        if self.create_mid_month:
            self._create_mid_month_approvals(target_employees)

        return {'type': 'ir.actions.act_window_close'}
