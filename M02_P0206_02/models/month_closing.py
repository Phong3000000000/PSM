# -*- coding: utf-8 -*-
from datetime import datetime
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class WorkforceMonthClosing(models.Model):
    """
    Model quản lý xác nhận công cuối tháng của nhân viên
    Bước 10-12: Quy trình xác nhận bảng công
    """
    _name = 'workforce.month.closing'
    _description = 'Xác nhận công cuối tháng'
    _order = 'period_year desc, period_month desc, employee_id'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    # =====================
    # BASIC FIELDS
    # =====================
    employee_id = fields.Many2one(
        'hr.employee',
        string='Nhân viên',
        required=True,
        index=True,
        ondelete='cascade'
    )
    
    period_month = fields.Selection([
        ('01', 'Tháng 01'), ('02', 'Tháng 02'), ('03', 'Tháng 03'),
        ('04', 'Tháng 04'), ('05', 'Tháng 05'), ('06', 'Tháng 06'),
        ('07', 'Tháng 07'), ('08', 'Tháng 08'), ('09', 'Tháng 09'),
        ('10', 'Tháng 10'), ('11', 'Tháng 11'), ('12', 'Tháng 12'),
    ], string='Tháng', required=True)
    
    period_year = fields.Integer(
        string='Năm',
        required=True,
        default=lambda self: fields.Date.today().year
    )

    name = fields.Char(
        string='Tên',
        compute='_compute_name',
        store=True
    )

    # =====================
    # SUMMARY FIELDS
    # =====================
    total_regular_hours = fields.Float(
        string='Tổng giờ thường',
        compute='_compute_hours_summary',
        store=True,
        help='Tổng giờ làm việc trong giờ hành chính (6h-22h)'
    )
    total_night_hours = fields.Float(
        string='Tổng giờ đêm',
        compute='_compute_hours_summary',
        store=True,
        help='Tổng giờ làm việc ban đêm (22h-6h)'
    )
    total_worked_hours = fields.Float(
        string='Tổng giờ công',
        compute='_compute_hours_summary',
        store=True
    )
    total_penalty_amount = fields.Float(
        string='Tổng phạt',
        default=0.0,
        help='Tổng số tiền phạt (đi muộn, về sớm, vv)'
    )
    total_amount = fields.Float(
        string='Tổng tiền lương',
        compute='_compute_total_amount',
        store=True
    )

    # =====================
    # CONFIRMATION FIELDS
    # =====================
    state = fields.Selection([
        ('draft', 'Chờ xác nhận'),
        ('confirmed', 'NV đã xác nhận'),
        ('disputed', 'Có khiếu nại'),
        ('locked', 'HR đã chốt'),
    ], default='draft', string='Trạng thái', tracking=True)
    
    employee_confirmed = fields.Boolean(
        string='Nhân viên xác nhận',
        default=False,
        tracking=True
    )
    confirmed_date = fields.Datetime(
        string='Ngày xác nhận',
        readonly=True
    )
    hr_locked = fields.Boolean(
        string='HR đã chốt',
        default=False,
        tracking=True
    )
    locked_date = fields.Datetime(
        string='Ngày chốt',
        readonly=True
    )
    locked_by = fields.Many2one(
        'res.users',
        string='Người chốt',
        readonly=True
    )

    # =====================
    # DISPUTE FIELDS
    # =====================
    dispute_reason = fields.Text(
        string='Lý do khiếu nại'
    )
    dispute_date = fields.Datetime(
        string='Ngày khiếu nại',
        readonly=True
    )
    dispute_resolved = fields.Boolean(
        string='Đã giải quyết',
        default=False
    )
    dispute_resolution = fields.Text(
        string='Kết quả giải quyết'
    )

    # =====================
    # CONSTRAINTS
    # =====================
    _sql_constraints = [
        (
            'employee_period_unique',
            'UNIQUE(employee_id, period_month, period_year)',
            'Mỗi nhân viên chỉ có 1 bản xác nhận công cho mỗi tháng!'
        ),
    ]

    # =====================
    # COMPUTE METHODS
    # =====================
    @api.depends('employee_id', 'period_month', 'period_year')
    def _compute_name(self):
        for rec in self:
            if rec.employee_id and rec.period_month and rec.period_year:
                rec.name = '%s - %s/%s' % (
                    rec.employee_id.name,
                    rec.period_month,
                    rec.period_year
                )
            else:
                rec.name = 'Mới'


    @api.depends('employee_id', 'period_month', 'period_year')
    def _compute_hours_summary(self):
        """Tính tổng giờ làm việc"""
        Attendance = self.env['hr.attendance']
        for rec in self:
            total_regular = 0.0
            total_night = 0.0
            
            if rec.employee_id and rec.period_month and rec.period_year:
                year = rec.period_year
                month = int(rec.period_month)
                first_day = datetime(year, month, 1)
                if month == 12:
                    last_day = datetime(year + 1, 1, 1)
                else:
                    last_day = datetime(year, month + 1, 1)
                
                attendances = Attendance.search([
                    ('employee_id', '=', rec.employee_id.id),
                    ('check_in', '>=', first_day),
                    ('check_in', '<', last_day),
                ])
                
                for att in attendances:
                    if att.check_in and att.check_out:
                        total_regular += att.worked_hours
            
            rec.total_regular_hours = round(total_regular, 2)
            rec.total_night_hours = round(total_night, 2)
            rec.total_worked_hours = round(total_regular + total_night, 2)

    @api.depends('total_worked_hours', 'total_penalty_amount', 'employee_id.hourly_rate')
    def _compute_total_amount(self):
        """Tính tổng tiền lương"""
        for rec in self:
            hourly_rate = rec.employee_id.hourly_rate if rec.employee_id else 0
            base_amount = rec.total_worked_hours * hourly_rate
            # Giờ đêm thường được tính 1.3x
            night_bonus = rec.total_night_hours * hourly_rate * 0.3
            rec.total_amount = round(base_amount + night_bonus - rec.total_penalty_amount, 0)

    # =====================
    # ACTIONS
    # =====================
    def action_employee_confirm(self):
        """Nhân viên bấm nút ĐÚNG - Xác nhận công"""
        self.ensure_one()
        if self.state not in ['draft', 'disputed']:
            raise UserError(_('Không thể xác nhận ở trạng thái này!'))
        
        self.write({
            'state': 'confirmed',
            'employee_confirmed': True,
            'confirmed_date': fields.Datetime.now(),
            'dispute_resolved': True if self.state == 'disputed' else False,
        })
        
        self.message_post(
            body=_('Nhân viên đã xác nhận bảng công tháng %s/%s.') % (
                self.period_month, self.period_year
            ),
            message_type='notification'
        )

    def action_employee_dispute(self):
        """Nhân viên bấm nút SAI - Khiếu nại"""
        self.ensure_one()
        if self.state not in ['draft']:
            raise UserError(_('Chỉ có thể khiếu nại ở trạng thái Chờ xác nhận!'))
        
        # Sẽ được xử lý qua wizard để nhập lý do
        return {
            'type': 'ir.actions.act_window',
            'name': 'Khiếu nại bảng công',
            'res_model': 'workforce.dispute.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_month_closing_id': self.id},
        }

    def action_hr_lock(self):
        """HR chốt lương - Không cho sửa nữa"""
        self.ensure_one()
        if not self.employee_confirmed:
            raise UserError(_('Nhân viên chưa xác nhận! Không thể chốt lương.'))
        
        self.write({
            'state': 'locked',
            'hr_locked': True,
            'locked_date': fields.Datetime.now(),
            'locked_by': self.env.uid,
        })
        
        self.message_post(
            body=_('HR đã chốt bảng công.'),
            message_type='notification'
        )

    def action_reset_to_draft(self):
        """Reset về draft (chỉ Admin)"""
        self.ensure_one()
        if not self.env.user.has_group('hr.group_hr_manager'):
            raise UserError(_('Chỉ HR Manager mới có quyền reset!'))
        
        self.write({
            'state': 'draft',
            'employee_confirmed': False,
            'confirmed_date': False,
            'hr_locked': False,
            'locked_date': False,
            'locked_by': False,
        })

    # =====================
    # HELPER METHODS
    # =====================
    @api.model
    def get_or_create_for_employee(self, employee_id, month=None, year=None):
        """Lấy hoặc tạo bản xác nhận công cho nhân viên"""
        if not month:
            month = '%02d' % fields.Date.today().month
        if not year:
            year = fields.Date.today().year
        
        closing = self.search([
            ('employee_id', '=', employee_id),
            ('period_month', '=', month),
            ('period_year', '=', year),
        ], limit=1)
        
        if not closing:
            closing = self.create({
                'employee_id': employee_id,
                'period_month': month,
                'period_year': year,
            })
        
        return closing

    @api.model
    def _cron_generate_monthly_closings(self):
        """Cron: Tự động tạo bản xác nhận công đầu tháng"""
        today = fields.Date.today()
        month = '%02d' % today.month
        year = today.year
        
        # Lấy tất cả nhân viên Part-time
        employees = self.env['hr.employee'].search([
            ('employment_type', '=', 'part_time'),
        ])
        
        for emp in employees:
            self.get_or_create_for_employee(emp.id, month, year)


class WorkforceDisputeWizard(models.TransientModel):
    """Wizard để nhập lý do khiếu nại"""
    _name = 'workforce.dispute.wizard'
    _description = 'Wizard khiếu nại bảng công'

    month_closing_id = fields.Many2one(
        'workforce.month.closing',
        string='Bảng công',
        required=True
    )
    dispute_reason = fields.Text(
        string='Lý do khiếu nại',
        required=True
    )

    def action_submit_dispute(self):
        """Submit khiếu nại"""
        self.ensure_one()
        self.month_closing_id.write({
            'state': 'disputed',
            'dispute_reason': self.dispute_reason,
            'dispute_date': fields.Datetime.now(),
            'dispute_resolved': False,
        })
        
        # Notify HR
        self.month_closing_id.message_post(
            body=_('Nhân viên khiếu nại bảng công: %s') % self.dispute_reason,
            message_type='comment',
            subtype_xmlid='mail.mt_comment',
        )
        
        return {'type': 'ir.actions.act_window_close'}
