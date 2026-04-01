# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
import pytz
from datetime import datetime, time

class HrPayslipRun(models.Model):
    _inherit = 'hr.payslip.run'
    _description = 'McDonalds Payslip Batch (OPS)'

    # --- Step B3: Compute Payroll & State Management ---
    state = fields.Selection(selection_add=[
        ('draft', 'Draft'),
        ('verifying', 'Verifying'),
        ('validated', 'Validated'),
        ('waiting_approval', 'Waiting for HR Approval'),
        ('approved', 'HR Approved'),
        ('unc_verifying', 'Verifying UNC'), 
        ('unc_validated', 'Validated UNC'), 
        ('waiting_c_level', 'Waiting C-Level Approval'),
        ('completed', 'Completed'),
        ('cancel', 'Cancelled')
    ], ondelete={
        'verifying': 'set default',
        'waiting_approval': 'set default',
        'approved': 'set default',
        'payment_ready': 'set default',
        'validated': 'set null',
        'unc_verifying': 'set null',
        'unc_validated': 'set null',
        'waiting_c_level': 'set null',
        'completed': 'set null',
    })

    def unlink(self):
        """ Force Delete: Cascade delete Payslips, Work Entries, and Attendance Sheets """
        for run in self:
            # 1. Get linked Payslips
            payslips = run.slip_ids
            if not payslips:
                continue

            # 2. Get linked Attendance Sheets
            # valid_versions = payslips.mapped('version_id') # Not directly linked to sheets
            # attendance_sheets = self.env['hr.attendance.sheet'].search([
            #    ('employee_id', 'in', payslips.employee_id.ids),
            #    ('date_from', '>=', run.date_start),
            #    ('date_to', '<=', run.date_end)
            # ])
            # Better way: if attendance_sheet_id is on payslip
            attendance_sheets = payslips.mapped('attendance_sheet_id')

            # 3. Get Work Entries
            # We must be careful not to delete work entries that are not related to this run/generation
            # But the user request says "Work entries... lien quan"
            # We identify work entries by the version_ids and date range likely.
            # Or from `payslip.work_entry_ids` if available? No, standard is computed.
            # We'll search by employee and date range.
            work_entries = self.env['hr.work.entry'].search([
                ('employee_id', 'in', payslips.employee_id.ids),
                ('date', '>=', run.date_start),
                ('date', '<=', run.date_end),
                ('state', '!=', 'validated') # Validated entries might be locked? But user said "Force".
            ])
            
            # --- EXECUTE DELETE ---
            # To bypass 'Done' state errors, we might need to set to Draft first or use simple SQL for speed/bypass if ORM blocks.
            # Try ORM first with sudo()
            
            # 3.1 Attendance Sheets
            if attendance_sheets:
                # Force state to draft to allow unlink
                attendance_sheets.sudo().write({'state': 'draft'}) 
                attendance_sheets.sudo().unlink()

            # 3.2 Work Entries
            if work_entries:
                work_entries.sudo().write({'state': 'draft'})
                work_entries.sudo().unlink()

            # 3.3 Payslips
            if payslips:
                payslips.sudo().write({'state': 'draft'})
                payslips.sudo().unlink()
                
            # 3.4 Approval Requests (Cleanup)
            if run.approval_request_id:
                run.approval_request_id.sudo().unlink()

        return super(HrPayslipRun, self).unlink()

    # --- Color Management ---
    color = fields.Integer(compute='_compute_color')
    
    @api.depends('state')
    def _compute_color(self):
        for run in self:
            if run.state in ['draft', 'verifying', 'validated', 'unc_verifying', 'unc_validated']:
                run.color = 4 # Blue/Info
            elif run.state in ['waiting_approval', 'waiting_c_level']:
                run.color = 2 # Orange/Warning
            elif run.state in ['approved', 'completed']:
                run.color = 10 # Green/Success
            elif run.state == 'cancel':
                run.color = 1 # Red/Danger
            else:
                run.color = 0

    # ... (Keep existing methods) ...

    # --- Step B6: Condition Check (Auto) -> Verifying UNC ---
    def check_payment_conditions(self):
        """ B6: System Check -> Move to Verifying UNC """
        self.ensure_one()
        # ... (Existing Check Logic) ...
        # Category for Resignation (Offboarding)
        offboarding_cat = self.env.ref('M02_P0213_00.approval_category_resignation', raise_if_not_found=False)

        for slip in self.slip_ids:
            is_eligible = True
            employee = slip.employee_id
            if offboarding_cat:
                pending_resignation = self.env['approval.request'].search_count([
                    ('category_id', '=', offboarding_cat.id),
                    ('request_owner_id', '=', employee.user_id.id),
                    ('request_status', 'in', ['pending', 'submitted', 'new']),
                ])
                if pending_resignation > 0:
                    is_eligible = False
            slip.x_is_payable = is_eligible
        
        self.write({'state': 'unc_verifying'}) # Move to UNC Verifying
        
        if self.payslip_waitlist_ids:
            self.message_post(body=_("Some employees are in Waitlist due to pending processes."))

    # --- Step B7: UNC Validation → Auto-create Payment Authorization for C-Level ---
    def action_validate_unc(self):
        """
        B7: Validate UNC → tự động tạo Payment Authorization (draft) để C-Level duyệt.
        C-Level KHÔNG duyệt qua Payslip Approval, mà duyệt trực tiếp trên Payment Authorization.
        """
        self.ensure_one()

        # Xác định payslips đủ điều kiện (payable, chưa có payment order)
        payable_slips = self.slip_ids.filtered(
            lambda s: s.x_is_payable and not s.payment_order_id and s.state != 'cancel'
        )
        if not payable_slips:
            payable_slips = self.slip_ids.filtered(lambda s: s.state != 'cancel' and not s.payment_order_id)

        # Tạo Payment Authorization draft cho C-Level duyệt
        if payable_slips:
            pa = self.env['payment.authorization'].create({
                'name': _('UNC %s') % self.name,
                'period': self.name,
                'payslip_run_id': self.id,
                'payslip_ids': [(6, 0, payable_slips.ids)],
                'state': 'draft',
            })

            # Tạo approval.request liên kết để C-Level thấy trong Approvals dashboard
            self._create_clevel_approval_request(pa)

        self.write({'state': 'unc_validated'})
        self.message_post(body=_('UNC đã tạo và gửi C-Level. Vui lòng vào Payment Orders để duyệt.'))

        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }

    def _create_clevel_approval_request(self, pa):
        """
        Tạo approval.request cho C-Level duyệt Payment Authorization.
        Request sẽ xuất hiện trong Approvals → My Approvals của C-Level.
        """
        # Tìm approval category cho C-Level (phải được config trong data)
        cat = self.env.ref('M02_P0207_02.approval_category_clevel_payment', raise_if_not_found=False)
        if not cat:
            cat = self.env['approval.category'].search([('name', 'ilike', 'C-Level')], limit=1)
        if not cat:
            # Không có category phù hợp → bỏ qua
            return

        req = self.env['approval.request'].sudo().create({
            'name': _('C-Level Duyệt UNC %s') % self.name,
            'category_id': cat.id,
            'request_owner_id': self.env.user.id,
            'request_status': 'new',
            'date_confirmed': fields.Datetime.now(),
            'payslip_run_id': self.id,  # link ngược lại Pay Run để smart button hoạt động
        })
        # Link request vào PA
        pa.write({'approval_request_id': req.id})
        # Post link vào chatter PA
        pa.message_post(
            body=_('Approval Request <a href="#" data-oe-model="approval.request" data-oe-id="%d">%s</a> đã được tạo cho C-Level duyệt.') % (req.id, req.name)
        )

    def action_approve_clevel(self):
        """ Deprecated - C-Level now approves via Payment Authorization directly """
        self.ensure_one()
        self.write({'state': 'completed'})

    # --- Override generate_payslips ...

    def _compute_state(self):
        # Override to prevent standard state computation as we use manual workflow
        pass

    # --- Lists for Step B6 (Condition Check) ---
    payslip_payable_ids = fields.One2many('hr.payslip', 'payslip_run_id', string='Payable Payslips',
        domain=[('x_is_payable', '=', True)],
        help="Payslips đã qua kiểm tra điều kiện và sẵn sàng đưa vào UNC.")

    payslip_waitlist_ids = fields.One2many('hr.payslip', 'payslip_run_id', string='Waitlist (Giữa tháng)',
        domain=[('x_is_mid_month', '=', True)],
        help="Nhân viên đang trong quy trình offboarding/onboarding – gửi lương giữa tháng.")

    mid_month_count = fields.Integer(
        compute='_compute_mid_month_count', string='Giữa tháng')

    def _compute_mid_month_count(self):
        for run in self:
            run.mid_month_count = len(run.payslip_waitlist_ids)

    def action_view_mid_month_list(self):
        """Smart button: mở danh sách nhân viên nhận lương giữa tháng."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Danh sách Giữa tháng - %s') % self.name,
            'res_model': 'hr.payslip',
            'view_mode': 'list,form',
            'domain': [('payslip_run_id', '=', self.id), ('x_is_mid_month', '=', True)],
            'context': {'default_payslip_run_id': self.id},
        }

    payment_order_ids = fields.One2many('payment.authorization', 'payslip_run_id', string='Payment Orders')
    payment_order_count = fields.Integer(compute='_compute_payment_order_count')
    
    # Approval Integration
    approval_request_id = fields.Many2one('approval.request', string='Approval Request', readonly=True)

    def _compute_payment_order_count(self):
        for rec in self:
            rec.payment_order_count = len(rec.payment_order_ids)
            
    # --- Step B3: Compute ---
    # Inherits action_validate from standard? No, standard is action_validate.
    # We override or use our own buttons.
    
    # --- Step B3: Compute ---
    def action_compute_sheet(self):
        """ B3: Compute Payroll """
        for sheet in self.slip_ids:
            sheet.compute_sheet()
        self.write({'state': 'verifying'})

    # --- Step B4: C&B Validate (Confirm) ---
    def action_validate_cb(self):
        """ B4.1: Confirm -> Validated """
        self.ensure_one()
        self.write({'state': 'validated'})

    def action_create_approval_request_cb(self):
        """ B4.2: Create Approval Request -> Waiting Approval """
        self.ensure_one()
        
        # 1. Create Approval Request
        category = self.env.ref('M02_P0207_02.approval_category_payroll', raise_if_not_found=False)
        if not category:
            self.write({'state': 'waiting_approval'})
            return

        request = self.env['approval.request'].create({
            'name': _('Approval for %s') % self.name,
            'category_id': category.id,
            'request_owner_id': self.env.user.id,
            'request_status': 'new',
            'payslip_run_id': self.id,
        })
        # Submit the request without checking manager (category uses specific approvers)
        request.sudo().write({'date_confirmed': fields.Datetime.now()})
        request.sudo().approver_ids.filtered(lambda a: a.status == 'new').write({'status': 'pending'})
        
        # 2. Update Run State & set payslips to pending
        self.write({
            'state': 'waiting_approval',
            'approval_request_id': request.id
        })
        self.action_set_payslips_pending()
        
        # 3. Reload
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }

    # --- Step B5: HR Manager Approve/Reject ---
    def action_approve_hr(self):
        """ B5: HR Approve → dừng ở state 'approved'. User sẽ click 'Kiểm tra & Phân loại' tiếp theo """
        self.ensure_one()
        # Auto-approve every payslip that's still pending
        pending_slips = self.slip_ids.filtered(lambda s: s.x_approval_state == 'pending')
        pending_slips.write({'x_approval_state': 'approved'})
        # Only advance if no refused payslips remain
        refused_slips = self.slip_ids.filtered(lambda s: s.x_approval_state == 'refused')
        if not refused_slips:
            self.write({'state': 'approved'})
            # Tự động mark approval.request thành Approved
            req = self.approval_request_id
            if req and req.request_status not in ('approved', 'refused', 'cancel'):
                req = req.sudo()
                if not req.approver_ids:
                    self.env['approval.approver'].sudo().create({
                        'request_id': req.id,
                        'user_id': self.env.user.id,
                        'status': 'approved',
                    })
                else:
                    req.approver_ids.write({'status': 'approved'})
                req._cancel_activities()
            self.message_post(
                body=_('✅ HR đã duyệt toàn bộ phiếu lương. Nhấn <b>"Kiểm tra điều kiện"</b> để Odoo phân loại danh sách trước khi tạo UNC.')
            )
        # If refused remain, stay in waiting_approval so they can be fixed and re-approved

    def action_approve_clevel(self):
        """ C-Level Approve -> auto-approve PENDING, advance ONLY if no refused remain.
        When all approved: validate payslips, create payment order, send email to employees, mark completed.
        """
        self.ensure_one()
        pending_slips = self.slip_ids.filtered(lambda s: s.x_approval_state == 'pending')
        pending_slips.write({'x_approval_state': 'approved'})
        refused_slips = self.slip_ids.filtered(lambda s: s.x_approval_state == 'refused')
        if refused_slips:
            return  # Stay in waiting_c_level; refused rows need to be re-processed

        # All approved at C-Level — complete the run
        self._complete_payroll_run()

    def _complete_payroll_run(self):
        """Final step: validate payslips, auto-create payment order, send emails, mark completed."""
        self.ensure_one()

        # 1. Validate all draft payslips (required before generating PDF/email)
        draft_slips = self.slip_ids.filtered(lambda s: s.state == 'draft')
        if draft_slips:
            draft_slips.action_payslip_done()

        # 2. Auto-create Payment Order (Ủy nhiệm chi) for approved, payable payslips
        payable_slips = self.slip_ids.filtered(
            lambda s: s.state != 'cancel' and s.x_approval_state == 'approved' and not s.payment_order_id
        )
        if not payable_slips:
            payable_slips = self.slip_ids.filtered(
                lambda s: s.state != 'cancel' and not s.payment_order_id
            )
        if payable_slips:
            self.env['payment.authorization'].create({
                'name': _('UNC %s') % self.name,
                'period': self.name,
                'payslip_run_id': self.id,
                'payslip_ids': [(6, 0, payable_slips.ids)],
                'state': 'approved',  # Auto-approved: C-Level has already approved the payslip run
            })

        # 3. Generate payslip PDFs and send email to each employee
        try:
            self.slip_ids._generate_pdf()
        except Exception as e:
            # Log but don't block completion if email fails
            self.message_post(body=_('Payslip emails could not be sent: %s') % str(e))

        # 4. Mark run as completed
        self.write({'state': 'completed'})
        self.message_post(body=_('Payroll run completed. Payment order created and payslip emails sent to employees.'))

    def action_finalize_approval(self):
        """
        Called by OWL HR Approval UI when ALL payslips are decided by HR.
        C-Level approval happens separately on Payment Authorization.
        """
        self.ensure_one()
        if self.state != 'waiting_approval':
            return

        # Only finalize when no payslips remain in pending
        pending_slips = self.slip_ids.filtered(lambda s: s.x_approval_state == 'pending')
        if pending_slips:
            return

        # Cancel refused payslips and revert their attendance sheets
        refused_slips = self.slip_ids.filtered(lambda s: s.x_approval_state == 'refused')
        if refused_slips:
            for slip in refused_slips:
                if slip.attendance_sheet_id:
                    try:
                        slip.attendance_sheet_id.sudo().write({'state': 'confirmed'})
                    except Exception:
                        pass
            try:
                refused_slips.action_payslip_cancel()
            except Exception:
                refused_slips.write({'state': 'cancel'})
            self.message_post(
                body=_('%d phiếu lương bị từ chối — đã gửi về bước xác nhận bảng công.') % len(refused_slips)
            )

        # HR Approval done — advance to approved then check UNC conditions
        self.action_approve_hr()

    def action_set_payslips_pending(self):
        """Set all payslips in this run to pending approval state."""
        self.ensure_one()
        self.slip_ids.write({'x_approval_state': 'pending', 'x_refusal_reason': False})

    def action_reject_hr(self):
        """ B5: Loopback: Reject -> Return to Draft """
        self.write({'state': 'draft'})
        
    def action_view_approval_request(self):
        self.ensure_one()
        if not self.approval_request_id:
            return
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'approval.request',
            'res_id': self.approval_request_id.id,
            'view_mode': 'form',
            'target': 'current',
        }

    # --- Step B6: Kiểm tra Điều kiện (Manual trigger sau khi HR duyệt) ---
    def check_payment_conditions(self):
        """
        B6: Kiểm tra từng phiếu lương trong danh sách đã HR duyệt.
        Phân loại:
          - Không có quy trình offboarding/onboarding → payable (vào UNC)
          - Có quy trình offboarding/onboarding → waitlist (gửi lương giữa tháng)
        """
        self.ensure_one()

        # Danh mục offboarding (nghỉ việc)
        offboarding_cat = self.env.ref('M02_P0213_00.approval_category_resignation', raise_if_not_found=False)
        # Danh mục onboarding (thử việc/mới vào)
        onboarding_cat = self.env.ref('M02_P0213_00.approval_category_onboarding', raise_if_not_found=False)

        payable_names = []
        waitlist_names = []

        for slip in self.slip_ids.filtered(lambda s: s.x_approval_state == 'approved'):
            is_eligible = True
            employee = slip.employee_id

            # Kiểm tra offboarding (Nghỉ việc đang chờ duyệt)
            if offboarding_cat and employee.user_id:
                pending_offboard = self.env['approval.request'].search_count([
                    ('category_id', '=', offboarding_cat.id),
                    ('request_owner_id', '=', employee.user_id.id),
                    ('request_status', 'in', ['pending', 'submitted', 'new']),
                ])
                if pending_offboard > 0:
                    is_eligible = False

            # Kiểm tra onboarding (Thử việc/quy trình mới vào đang chờ duyệt)
            if is_eligible and onboarding_cat and employee.user_id:
                pending_onboard = self.env['approval.request'].search_count([
                    ('category_id', '=', onboarding_cat.id),
                    ('request_owner_id', '=', employee.user_id.id),
                    ('request_status', 'in', ['pending', 'submitted', 'new']),
                ])
                if pending_onboard > 0:
                    is_eligible = False

            slip.x_is_payable = is_eligible
            slip.x_is_mid_month = not is_eligible

            if is_eligible:
                payable_names.append(employee.name)
            else:
                waitlist_names.append(employee.name)

        self.write({'state': 'unc_verifying'})

        # Post kết quả phân loại vào chatter
        payable_html = ''.join(f'<li>{n}</li>' for n in payable_names) or '<li><em>Không có</em></li>'
        waitlist_html = ''.join(f'<li>{n}</li>' for n in waitlist_names) or '<li><em>Không có</em></li>'
        self.message_post(body=_(
            '<p><b>Kết quả kiểm tra điều kiện:</b></p>'
            '<p>✅ <b>Danh sách dư vào UNC (%(payable)d người):</b></p><ul>%(payable_list)s</ul>'
            '<p>⏳ <b>Danh sách gửi lương giữa tháng (%(waitlist)d người):</b></p><ul>%(waitlist_list)s</ul>'
        ) % {
            'payable': len(payable_names),
            'payable_list': payable_html,
            'waitlist': len(waitlist_names),
            'waitlist_list': waitlist_html,
        })

    # --- Step B7: Create Payment Order ---
    def action_create_payment_order(self):
        """ B7: Create UNC for Payable Payslips """
        self.ensure_one()
        payable_slips = self.payslip_payable_ids.filtered(lambda s: not s.payment_order_id)
        
        if not payable_slips:
            raise UserError(_("No payable payslips found (or all already added to orders)."))
            
        payment_order = self.env['payment.authorization'].create({
            'name': _('UNC %s') % self.name,
            'payslip_run_id': self.id,
            'payslip_ids': [(6, 0, payable_slips.ids)],
            'state': 'draft'
        })
        
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'payment.authorization',
            'view_mode': 'form',
            'res_id': payment_order.id,
            'target': 'current',
        }

    def action_view_payment_orders(self):
        self.ensure_one()
        action = self.env['ir.actions.act_window']._for_xml_id('payment.action_payment_authorization')
        action['domain'] = [('payslip_run_id', '=', self.id)]
        action['context'] = {'default_payslip_run_id': self.id}
        return action

    # --- Override generate_payslips to fix RPC Error with hr.work.entry ---
    def generate_payslips(self, version_ids=None, employee_ids=None):
        self.ensure_one()

        if employee_ids and not version_ids:
            version_ids = self._get_valid_version_ids(employee_ids=employee_ids)

        if not version_ids:
            raise UserError(self.env._("You must select employee(s) version(s) to generate payslip(s)."))

        valid_versions = self.env["hr.version"].browse(version_ids)
        Payslip = self.env['hr.payslip']

        if self.structure_id:
            valid_versions = valid_versions.filtered(lambda c: c.structure_type_id.id == self.structure_id.type_id.id)
        valid_versions.generate_work_entries(self.date_start, self.date_end)

        all_work_entries = dict(self.env['hr.work.entry']._read_group(
            domain=[
                ('employee_id', 'in', valid_versions.employee_id.ids),
                ('date', '<=', self.date_end),
                ('date', '>=', self.date_start),
            ],
            groupby=['version_id'],
            aggregates=['id:recordset'],
        ))

        utc = pytz.utc
        for tz, slips_per_tz in self.slip_ids.grouped(lambda s: s.version_id.tz).items():
            slip_tz = pytz.timezone(tz or utc)
            for slip in slips_per_tz:
                date_from = slip_tz.localize(datetime.combine(slip.date_from, time.min)).astimezone(utc).replace(tzinfo=None)
                date_to = slip_tz.localize(datetime.combine(slip.date_to, time.max)).astimezone(utc).replace(tzinfo=None)
                if version_work_entries := all_work_entries.get(slip.version_id):
                    # OPS FIX: Use date instead of date_stop/date_start
                    version_work_entries.filtered_domain([
                        ('date', '<=', date_to.date()),
                        ('date', '>=', date_from.date()),
                    ])
                    version_work_entries._check_undefined_slots(slip.date_from, slip.date_to)

        for work_entries in all_work_entries.values():
            work_entries = work_entries.filtered(lambda we: we.state != 'validated')
            if work_entries._check_if_error():
                work_entries = work_entries.filtered(lambda we: we.state == 'conflict')
                conflicts = work_entries._to_intervals()
                time_intervals_str = "".join(
                    f"\n - {start} -> {end} ({entry.employee_id.name})" for start, end, entry in conflicts._items)
                raise UserError(self.env._("Some work entries could not be validated. Time intervals to look for:%s", time_intervals_str))

        default_values = Payslip.default_get(Payslip.fields_get())
        payslips_vals = []
        for version in valid_versions[::-1]:
            values = default_values | {
                'name': self.env._('New Payslip'),
                'employee_id': version.employee_id.id,
                'payslip_run_id': self.id,
                'date_from': self.date_start,
                'date_to': self.date_end,
                'version_id': version.id,
                'company_id': self.company_id.id,
                'struct_id': self.structure_id.id or version.structure_type_id.default_struct_id.id,
            }
            payslips_vals.append(values)
        self.slip_ids |= Payslip.with_context(tracking_disable=True).create(payslips_vals)
        self.slip_ids.compute_sheet()
        self.state = 'verifying'

        return 1

class HrPayslip(models.Model):
    _inherit = 'hr.payslip'
    
    x_is_payable = fields.Boolean(string='Is Payable', default=True, help="Flag determined by Step B6")
    x_is_mid_month = fields.Boolean(string='Giữa tháng', default=False,
                                    help='True nếu nhân viên có quy trình offboarding/onboarding – gửi lương giữa tháng.')
    x_approval_state = fields.Selection([
        ('pending',  'Pending'),
        ('approved', 'Approved'),
        ('refused',  'Refused'),
    ], string='Approval State', default='pending')
    x_refusal_reason = fields.Text(string='Refusal Reason')

    def action_approve_payslip(self):
        """Approve this individual payslip. If all payslips in the run are done, complete the approval."""
        self.ensure_one()
        self.write({'x_approval_state': 'approved'})
        self._check_all_payslips_done()

    def action_send_for_hr(self):
        """
        'Gửi cho HR' button: resets a refused payslip back to 'pending'
        so it reappears in the OWL approval UI with Phê duyệt/Từ chối buttons.
        """
        self.ensure_one()
        self.write({
            'x_approval_state': 'pending',
            'x_refusal_reason': False,
        })
        self.message_post(body=_('Đã gửi lại cho HR phê duyệt sau khi tính lương lại.'))

    def _check_all_payslips_done(self):
        """Advance the HR approval run when ALL payslips are approved by HR."""
        run = self.payslip_run_id
        if not run or run.state != 'waiting_approval':
            return
        # Must have zero pending AND zero refused to advance
        not_approved = run.slip_ids.filtered(lambda s: s.x_approval_state != 'approved')
        if not_approved:
            return  # Stay in waiting_approval
        # All approved by HR — advance run
        run.action_approve_hr()
        # Mark the HR approval.request as completed
        req = run.approval_request_id
        if req and req.request_status not in ('approved', 'refused', 'cancel'):
            req.sudo().approver_ids.write({'status': 'approved'})
            req.sudo()._cancel_activities()

    def action_refuse_payslip_popup(self):
        """Open the refuse reason wizard."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'payslip.refuse.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_payslip_id': self.id},
        }

    def action_refuse_hr_approval(self, reason):
        """
        Được gọi từ OWL Payslip Approval UI khi HR từ chối một payslip.
        1. Cập nhật state → refused
        2. Log vào chatter
        3. Gửi thông báo cho nhóm C&B để xử lý lại
        """
        self.ensure_one()
        self.write({
            'x_approval_state': 'refused',
            'x_refusal_reason': reason,
            'state': 'draft',
        })

        # Log hành động từ chối
        self.message_post(
            body=_('HR từ chối. Lý do: %s') % reason,
            message_type='notification',
        )

        # Gửi thông báo cho C&B (hr.group_hr_user)
        self._notify_cb_refused(reason)

    def _notify_cb_refused(self, reason):
        """Gửi email thông báo cho nhóm C&B (theo cấu hình) khi payslip bị từ chối."""
        config = self.env['payroll.ops.config'].sudo().get_config()
        cb_users = config.cb_notify_ids
        if not cb_users:
            return

        cb_partners = cb_users.mapped('partner_id')
        employee_name = self.employee_id.name or 'N/A'
        run_name = self.payslip_run_id.name or 'N/A'

        body = _(
            '<p>Xin chào,</p>'
            '<p>Phiếu lương của nhân viên <b>%(emp)s</b> '
            '(Pay Run: <b>%(run)s</b>) đã bị HR <b>từ chối</b> và cần C&amp;B xử lý lại.</p>'
            '<p><b>Lý do:</b> %(reason)s</p>'
            '<p>Vui lòng kiểm tra lại dữ liệu công và tính toán lại phiếu lương, '
            'sau đó nhấn <b>"Gửi cho HR"</b> để gửi lại phê duyệt.</p>'
        ) % {
            'emp': employee_name,
            'run': run_name,
            'reason': reason,
        }

        self.message_post(
            body=body,
            partner_ids=cb_partners.ids,
            subject=_('[Lương] Phiếu lương %s bị từ chối - cần xử lý lại') % employee_name,
            message_type='comment',
            subtype_xmlid='mail.mt_comment',
        )

    def compute_sheet(self):
        """Override: reset refused payslip to pending when recomputed (after attendance fix)."""
        result = super().compute_sheet()
        # If the payslip was refused and is now being recomputed by HR, reset to pending for re-approval
        for slip in self:
            if slip.x_approval_state == 'refused' and slip.payslip_run_id and \
                    slip.payslip_run_id.state == 'waiting_approval':
                slip.write({'x_approval_state': 'pending', 'x_refusal_reason': False})
        return result


class ApprovalRequest(models.Model):
    _inherit = 'approval.request'

    payslip_run_id = fields.Many2one('hr.payslip.run', string='Payslip Run', readonly=True)
    payment_order_count = fields.Integer(
        string='Payment Orders',
        compute='_compute_payment_order_count',
    )

    # Link trực tiếp tới PA được gắn v́i request này
    direct_pa_id = fields.Many2one(
        'payment.authorization',
        string='Payment Authorization',
        compute='_compute_direct_pa_id',
    )

    def _compute_direct_pa_id(self):
        PA = self.env['payment.authorization']
        for rec in self:
            pa = PA.search([('approval_request_id', '=', rec.id)], limit=1)
            rec.direct_pa_id = pa

    def action_view_direct_pa(self):
        """Smart button: mở Payment Authorization gắn trực tiếp với request này."""
        self.ensure_one()
        if not self.direct_pa_id:
            return
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'payment.authorization',
            'res_id': self.direct_pa_id.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def _compute_payment_order_count(self):
        for rec in self:
            rec.payment_order_count = len(rec.payslip_run_id.payment_order_ids) if rec.payslip_run_id else 0

    def action_view_payment_order(self):
        """Smart button: open Payment Authorization(s) linked to this approval's Pay Run."""
        self.ensure_one()
        orders = self.payslip_run_id.payment_order_ids
        if not orders:
            return
        if len(orders) == 1:
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'payment.authorization',
                'res_id': orders[0].id,
                'view_mode': 'form',
                'target': 'current',
            }
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'payment.authorization',
            'domain': [('id', 'in', orders.ids)],
            'view_mode': 'list,form',
            'target': 'current',
        }

    def action_approve(self, approver=None):
        res = super().action_approve(approver=approver)
        # Sync: If this is a Payroll Approval and now fully approved,
        # auto-approve all pending payslips then advance the Pay Run
        for request in self:
            if request.request_status == 'approved' and request.payslip_run_id:
                run = request.payslip_run_id
                if run.state == 'waiting_approval':
                    run.action_approve_hr()   # will auto-approve pending + advance
                elif run.state == 'waiting_c_level':
                    run.action_approve_clevel()
        return res

    def action_approve_payslips(self):
        """Button on approval.request form: approve all pending payslips in the linked Pay Run."""
        self.ensure_one()
        if not self.payslip_run_id:
            return
        run = self.payslip_run_id
        if run.state == 'waiting_approval':
            run.action_approve_hr()
        elif run.state == 'waiting_c_level':
            run.action_approve_clevel()
        # H4: Force approval.request to 'approved' state
        # If approver_ids is empty (request was never submitted via action_confirm),
        # create one approved approver record so request_status computes to 'approved'
        if self.request_status not in ('approved', 'refused', 'cancel'):
            req = self.sudo()
            if not req.approver_ids:
                self.env['approval.approver'].sudo().create({
                    'request_id': self.id,
                    'user_id': self.env.user.id,
                    'status': 'approved',
                })
            else:
                req.approver_ids.write({'status': 'approved'})
            req._cancel_activities()
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }

    def action_view_payslip_run(self):
        """Open the custom OWL Payslip Approval UI filtered to this Pay Run."""
        self.ensure_one()
        # Return the OWL client action — the JS component will load and select
        # self.payslip_run_id automatically via context
        return {
            'type': 'ir.actions.client',
            'tag': 'payslip_approval_action',
            'context': {'default_run_id': self.payslip_run_id.id},
        }


