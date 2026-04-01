# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError

class HrPayslip(models.Model):
    _inherit = 'hr.payslip'

    attendance_sheet_id = fields.Many2one('hr.attendance.sheet', string='Attendance Sheet', readonly=True)
    payment_order_id = fields.Many2one('payment.authorization', string='Payment Order', readonly=True)
    
    # Requirement: Marketing Leave Hours (mentioned in analysis plan, though extracted text was messy)
    # Adding field for completeness if analysis implied it
    marketing_leave_hours = fields.Float(string='Marketing Leave Hours') 
    leave_hours = fields.Float(string='Leave Hours')
    
    # Requirement 1.4: "Lý do từ chối dòng"
    x_payment_rejection_reason = fields.Text(string='Payment Rejection Reason', help="Reason if payment/payslip is rejected by C-Level")

    # Hold lương (từ hr_payroll_custom)
    is_hold_salary = fields.Boolean(string='Giữ lương (Hold)', default=False, tracking=True)
    hold_reason = fields.Char(string='Lý do giữ lương', tracking=True)

    # Receiver bank info (computed from employee bank account for payment order)
    x_receiver_name = fields.Char(string='Receiver Name', compute='_compute_receiver_bank_info', store=True)
    x_receiver_bank_account = fields.Char(string='Bank Account', compute='_compute_receiver_bank_info', store=True)
    x_receiver_bank_name = fields.Char(string='Bank Name', compute='_compute_receiver_bank_info', store=True)

    # ── Cột UNC – Bảng chi tiết thanh toán (Section V) ─────────────────────
    x_hoa_don_so    = fields.Char(string='Hóa đơn Số')
    x_hoa_don_ngay  = fields.Char(string='Hóa đơn Ngày')
    x_chung_tu_so   = fields.Char(string='Chứng từ Số')
    x_chung_tu_ngay = fields.Char(string='Chứng từ Ngày')
    x_ma_nguon_ns   = fields.Char(string='Mã nguồn ngân sách')
    x_nien_do_ns    = fields.Char(string='Niên độ ngân sách',
                                  default=lambda self: str(fields.Date.today().year))

    # ── Trạng thái phân loại (Step B6 Kiểm tra điều kiện) ───────────────────
    x_is_payable  = fields.Boolean(string='Payable', default=True,
                                   help='True: đủ điều kiện UNC cuối tháng.')
    x_is_mid_month = fields.Boolean(string='Giữa tháng', default=False,
                                    help='True: đang offboarding/onboarding — gửi lương giữa tháng.')

    # ── Approval / refusal ───────────────────────────────────────────────────
    x_approval_state = fields.Selection([
        ('pending',  'Chờ duyệt'),
        ('approved', 'Đã duyệt'),
        ('refused',  'Từ chối'),
    ], string='HR Approval', default='pending')
    x_refusal_reason = fields.Text(string='Lý do từ chối')

    @api.depends('employee_id', 'employee_id.primary_bank_account_id')
    def _compute_receiver_bank_info(self):
        for slip in self:
            emp = slip.employee_id
            # Odoo 19: primary_bank_account_id is computed from bank_account_ids
            bank_acc = emp.sudo().primary_bank_account_id if emp else False
            slip.x_receiver_name = emp.name if emp else ''
            slip.x_receiver_bank_account = bank_acc.acc_number if bank_acc else ''
            slip.x_receiver_bank_name = bank_acc.bank_id.name if bank_acc and bank_acc.bank_id else ''

    # Approval / Refusal history log
    approval_log_ids = fields.One2many('hr.payslip.approval.log', 'payslip_id', string='Approval History')
    approval_log_count = fields.Integer(compute='_compute_approval_log_count', string='Log Count')

    @api.depends('approval_log_ids')
    def _compute_approval_log_count(self):
        for slip in self:
            slip.approval_log_count = len(slip.approval_log_ids)

    def action_create_approval_log(self, action, reason='', stage=''):
        """Called from OWL or Python when approving/refusing a payslip."""
        self.ensure_one()
        self.env['hr.payslip.approval.log'].create({
            'payslip_id': self.id,
            'action': action,
            'reason': reason,
            'user_id': self.env.user.id,
            'stage': stage,
        })

    def action_view_approval_logs(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Approval / Refusal History'),
            'res_model': 'hr.payslip.approval.log',
            'view_mode': 'list,form',
            'domain': [('payslip_id', '=', self.id)],
            'context': {'default_payslip_id': self.id},
        }
    def action_payslip_done(self):
        res = super(HrPayslip, self).action_payslip_done()
        # Logic to "Link attendance_sheet with payslip (smart button 2 ways)" is handled by the Many2one field
        # We might need to ensure the attendance sheet knows about this payslip if we want a strict 2-way link 
        return res

    # _get_worked_day_lines_values override removed to use standard Work Entry architecture
    # The system now generates hr.work.entry records from Attendance Sheets, 
    # so standard Odoo Payroll rules will automatically pick them up.


    def compute_payslip_from_attendance(self, structure_id=False):
        """
        Automate Step:
        - Input: List of confirmed attendance_sheet
        - Logic: Create payslip for each sheet
        """
        # Find confirmed attendance sheets not yet paid
        sheets = self.env['hr.attendance.sheet'].search([
            ('state', '=', 'confirmed'),
            ('id', 'not in', self.search([]).mapped('attendance_sheet_id').ids) 
        ])
        
        payslips = self.env['hr.payslip']
        for sheet in sheets:
            # Basic validation
            if sheet.employee_id.offboarding_status == 'in_progress':
                # Check specifics? For now, we process everyone, and Step B6 filters payment.
                pass 

            # Create Payslip
            vals = {
                'employee_id': sheet.employee_id.id,
                'date_from': sheet.start_date,
                'date_to': sheet.end_date,
                'attendance_sheet_id': sheet.id,
                'struct_id': structure_id or sheet.employee_id.contract_id.structure_type_id.default_struct_id.id,
                'name': _('Payslip %s') % sheet.name,
                # Link to existing run? Or create new run?
                # Usually triggered from a Run context.
            }
            payslip = self.create(vals)
            payslips += payslip
            
            payslip.compute_sheet()
            
        return payslips

    def _get_base_local_dict(self):
        res = super(HrPayslip, self)._get_base_local_dict()
        if 'contract' not in res or not res.get('contract'):
            # Fallback: Use Employee as Contract
            # Reason: hr.contract might be missing/deprecated, but hr.employee inherits hr.version
            # containing wage, structure_type_id, etc.
            res['contract'] = self.employee_id
        return res


