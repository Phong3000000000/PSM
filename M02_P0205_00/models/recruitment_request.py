# -*- coding: utf-8 -*-
from odoo import models, fields, api, _, Command
from odoo.exceptions import UserError, ValidationError

class RecruitmentRequestApprover(models.Model):
    """Danh sách Manager duyệt Yêu Cầu Tuyển Dụng theo Phòng Ban"""
    _name = 'x_psm_recruitment_request_approver'
    _description = 'Manager Approver cho Yêu Cầu Tuyển Dụng'
    
    request_id = fields.Many2one('x_psm_recruitment_request', string='Yêu Cầu', ondelete='cascade', required=True)
    department_id = fields.Many2one('hr.department', string='Phòng Ban', required=True)
    manager_id = fields.Many2one('hr.employee', string='Manager/Trưởng Phòng', required=True)
    user_id = fields.Many2one('res.users', string='User', related='manager_id.user_id', store=True, readonly=True)
    status = fields.Selection([
        ('new', 'Chờ duyệt'),
        ('approved', 'Đã duyệt'),
        ('rejected', 'Từ chối')
    ], string='Trạng thái', default='new', tracking=True)
    
    approved_date = fields.Datetime(string='Ngày duyệt', readonly=True)
    notes = fields.Text(string='Ghi chú')


class RecruitmentRequest(models.Model):
    _name = 'x_psm_recruitment_request'
    _description = 'Yêu Cầu Tuyển Dụng'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'id desc'

    name = fields.Char(string='Mã Yêu Cầu', required=True, copy=False, readonly=True, index=True, default=lambda self: 'New')

    # Đợt tuyển dụng (chọn từ danh sách đợt)
    batch_id = fields.Many2one(
        'x_psm_recruitment_batch', string='Đợt tuyển dụng',
        tracking=True,
        domain="[('state', '=', 'open')]",
        help='Chọn đợt tuyển dụng')

    # Step 1: Lập nhu cầu
    request_type = fields.Selection([
        ('unplanned', 'Đột xuất'),
        ('planned', 'Theo kế hoạch')
    ], string='Loại yêu cầu', default='unplanned', required=True, tracking=True)

    recruitment_block = fields.Selection([
        ('store', 'Khối Cửa Hàng'),
        ('office', 'Khối Văn Phòng'),
    ], string='Khối tuyển dụng', default='office', required=True, tracking=True)

    job_id = fields.Many2one('hr.job', string='Vị trí tuyển dụng', tracking=True)
    department_id = fields.Many2one('hr.department', string='Phòng ban', tracking=True)
    quantity = fields.Integer(string='Số lượng', default=1, tracking=True)
    date_start = fields.Date(string='Ngày bắt đầu', tracking=True)
    date_end = fields.Date(string='Ngày kết thúc', tracking=True)
    reason = fields.Text(string='Lý do tuyển dụng', required=True)

    line_ids = fields.One2many('x_psm_recruitment_request_line', 'request_id', string='Chi tiết vị trí')
    approver_ids = fields.One2many('x_psm_recruitment_request_approver', 'request_id', string='Manager duyệt')

    user_id = fields.Many2one('res.users', string='Người yêu cầu', default=lambda self: self.env.user, tracking=True)
    company_id = fields.Many2one('res.company', string='Công ty', default=lambda self: self.env.company)
    recruitment_plan_id = fields.Many2one('x_psm_recruitment_plan', string='Kế hoạch tuyển dụng', readonly=True, tracking=True)
    x_psm_approval_request_id = fields.Many2one(
        'approval.request',
        string='Phê duyệt',
        copy=False,
        readonly=True,
        tracking=True,
    )
    x_psm_approval_status = fields.Selection(
        related='x_psm_approval_request_id.request_status',
        string='Trạng thái phê duyệt',
        readonly=True,
    )

    user_department_id = fields.Many2one(
        'hr.department',
        string='Phòng ban (người yêu cầu)',
        compute='_compute_user_department',
        store=True,
    )

    state = fields.Selection([
        ('draft', 'Nháp'),
        ('hr_validation', 'HR Validate'),
        ('ceo_approval', 'CEO Duyệt'),
        ('in_progress', 'Đang tuyển'),
        ('done', 'Hoàn thành'),
        ('cancel', 'Từ chối')
    ], string='Trạng thái', default='draft', tracking=True)

    is_published = fields.Boolean(string='Đã đăng Portal', default=False, copy=False)
    
    @api.depends('user_id')
    def _compute_user_department(self):
        for rec in self:
            employee = rec.user_id.employee_id
            rec.user_department_id = employee.department_id if employee else False

    @api.onchange('user_id')
    def _onchange_user_department(self):
        if self.user_id:
            employee = self.user_id.employee_id
            self.user_department_id = employee.department_id if employee else False
            self.department_id = self.user_department_id

    @api.model
    def default_get(self, fields):
        res = super().default_get(fields)
        if 'user_department_id' in fields or 'user_department_id' in res:
            employee = self.env.user.employee_id
            if employee:
                res['user_department_id'] = employee.department_id.id
                res['department_id'] = employee.department_id.id
        return res
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
             if vals.get('name', 'New') == 'New':
                 vals['name'] = self.env['ir.sequence'].next_by_code('x_psm_recruitment_request') or 'New'
        return super(RecruitmentRequest, self).create(vals_list)

    def _get_recruitment_workflow_group_xmlids(self):
        """Single source of truth for recruitment request workflow groups."""
        return ['M02_P0200_00.GDH_RST_HR_RECRUITMENT_M']

    def _get_recruitment_workflow_groups(self):
        groups = self.env['res.groups']
        for xmlid in self._get_recruitment_workflow_group_xmlids():
            group = self.env.ref(xmlid, raise_if_not_found=False)
            if group:
                groups |= group
        return groups

    def _get_recruitment_workflow_users(self):
        self.ensure_one()
        groups = self._get_recruitment_workflow_groups()
        if not groups:
            return self.env['res.users'].browse()
        return groups.mapped('user_ids').filtered(lambda user: not user.share)

    def _get_ceo_approval_user(self):
        """Pick one CEO approver: company CEO first, then CEO group fallback."""
        self.ensure_one()
        excluded_user_ids = {self.user_id.id} if self.user_id else set()
        users = self.env['res.users'].browse()

        ceo_employee = self.company_id.x_psm_0205_ceo_id if self.company_id else False
        if ceo_employee and ceo_employee.user_id:
            users |= ceo_employee.user_id

        users = users.filtered(
            lambda user: user.active and not user.share and user.id not in excluded_user_ids
        )
        if users:
            return users[:1]

        ceo_group = self.env.ref(
            'M02_P0205_00.group_gdh_rst_office_recruitment_mgr_ceo',
            raise_if_not_found=False,
        )
        if not ceo_group:
            return self.env['res.users'].browse()

        fallback_users = ceo_group.user_ids.filtered(
            lambda user: user.active and not user.share and user.id not in excluded_user_ids
        ).sorted('id')
        return fallback_users[:1]

    def _get_hr_approval_user(self):
        """Pick one HR approver: job owner first, then HR group fallback."""
        self.ensure_one()
        ceo_user = self._get_ceo_approval_user()
        excluded_user_ids = {self.user_id.id} if self.user_id else set()
        if ceo_user:
            excluded_user_ids.add(ceo_user.id)

        users = self.env['res.users'].browse()
        if self.job_id and self.job_id.user_id:
            users |= self.job_id.user_id

        users = users.filtered(
            lambda user: user.active and not user.share and user.id not in excluded_user_ids
        )
        if users:
            return users[:1]

        hr_group = self.env.ref('M02_P0200_00.GDH_RST_HR_RECRUITMENT_M', raise_if_not_found=False)
        if not hr_group:
            return self.env['res.users'].browse()

        fallback_users = hr_group.user_ids.filtered(
            lambda user: user.active and not user.share and user.id not in excluded_user_ids
        ).sorted('id')
        return fallback_users[:1]

    def _get_approval_category(self):
        return self.env.ref('M02_P0205_00.approval_category_recruitment_request', raise_if_not_found=False)

    def _prepare_dynamic_approvers(self):
        self.ensure_one()
        approver_commands = []
        used_user_ids = set()

        hr_user = self._get_hr_approval_user()
        if hr_user and hr_user.id not in used_user_ids:
            approver_commands.append(Command.create({
                'user_id': hr_user.id,
                'required': True,
                'sequence': 10,
            }))
            used_user_ids.add(hr_user.id)

        # Store requests created from portal only need recruitment admin approval.
        if self.recruitment_block != 'store':
            ceo_user = self._get_ceo_approval_user()
            if ceo_user and ceo_user.id not in used_user_ids:
                approver_commands.append(Command.create({
                    'user_id': ceo_user.id,
                    'required': True,
                    'sequence': 20,
                }))
                used_user_ids.add(ceo_user.id)

        if not approver_commands:
            raise UserError(_(
                "Không tìm thấy người duyệt hợp lệ cho Yêu Cầu Tuyển Dụng. "
                "Vui lòng cấu hình HR (phụ trách job hoặc group HR Recruitment) "
                "hoặc CEO (CEO công ty hoặc group CEO Recruitment)."
            ))

        return approver_commands

    def _prepare_approval_request_vals(self):
        self.ensure_one()
        category = self._get_approval_category()
        if not category:
            raise UserError(_("Chưa cấu hình Approval Category cho Yêu Cầu Tuyển Dụng."))

        approver_commands = self._prepare_dynamic_approvers()
        reason_text = (self.reason or '').strip() or '-'
        return {
            'name': self.name,
            'category_id': category.id,
            'request_owner_id': self.user_id.id,
            'reference': self.name,
            'reason': reason_text,
            'approver_ids': approver_commands,
            'x_psm_0205_recruitment_request_id': self.id,
        }

    def _sync_state_from_approval_requests(self):
        for rec in self:
            approval = rec.x_psm_approval_request_id
            if not approval:
                continue

            status = approval.request_status

            if status == 'new':
                if rec.state not in ('draft', 'done', 'cancel'):
                    rec.write({'state': 'draft'})
                continue

            if status == 'cancel':
                if rec.state not in ('draft', 'done', 'cancel'):
                    rec.write({'state': 'cancel'})
                    rec._cleanup_open_activities()
                continue

            if status == 'refused':
                if rec.state != 'cancel':
                    rec.write({'state': 'cancel'})
                    rec._cleanup_open_activities()
                    rec.message_post(body=_("Yêu cầu bị từ chối trên luồng Approval."))
                continue

            if status == 'approved':
                if rec.state not in ('in_progress', 'done'):
                    rec.action_ceo_approve()
                    rec.message_post(body=_("Yêu cầu đã được phê duyệt hoàn tất qua Approval."))
                continue

            if status != 'pending':
                continue

            pending_approver = approval.approver_ids.filtered(
                lambda approver: approver.status == 'pending'
            ).sorted(lambda approver: (approver.sequence, approver.id))[:1]
            if not pending_approver:
                pending_approver = approval.approver_ids.filtered(
                    lambda approver: approver.status in ('waiting', 'new')
                ).sorted(lambda approver: (approver.sequence, approver.id))[:1]

            if rec.recruitment_block == 'store':
                target_state = 'draft'
            elif pending_approver and (pending_approver.sequence or 0) >= 20:
                target_state = 'ceo_approval'
            else:
                target_state = 'hr_validation'

            if rec.state != target_state:
                rec.write({'state': target_state})

            if rec.recruitment_block == 'store':
                rec._send_activity_to_hr()
            elif target_state == 'ceo_approval':
                rec._send_activity_to_ceo()
            else:
                rec._send_activity_to_hr()

    def _validate_before_submit(self):
        for rec in self:
            if not rec.line_ids and not rec.job_id:
                raise UserError(_("Vui lòng thêm ít nhất một dòng vị trí tuyển dụng."))

            for line in rec.line_ids:
                if (line.quantity or 0) <= 0:
                    raise UserError(_("Số lượng trên từng dòng phải lớn hơn 0."))
                if line.recruitment_block and line.recruitment_block != rec.recruitment_block:
                    line.recruitment_block = rec.recruitment_block
                if rec.recruitment_block == 'office' and not line.job_id:
                    raise UserError(_("Khối Văn Phòng yêu cầu chọn vị trí tuyển dụng có sẵn cho từng dòng."))
                if not line.job_id and not (line.position_name or '').strip():
                    raise UserError(_("Dòng tuyển dụng chưa có vị trí. Vui lòng chọn vị trí hoặc nhập tên vị trí."))

            if rec.request_type == 'unplanned' and rec.job_id and (rec.quantity or 0) <= 0:
                raise UserError(_("Số lượng tuyển dụng phải lớn hơn 0."))

    def action_submit(self):
        """Tạo approval request và submit luồng duyệt."""
        for rec in self:
            rec._validate_before_submit()
            if rec.x_psm_approval_request_id and rec.x_psm_approval_request_id.request_status == 'pending':
                raise UserError(_("Yêu cầu này đang chờ duyệt trên Approval."))
            approval_vals = rec._prepare_approval_request_vals()
            approval_request = rec.env['approval.request'].sudo().create(approval_vals)
            approval_request.action_confirm()
            rec.write({'x_psm_approval_request_id': approval_request.id})

            rec._sync_state_from_approval_requests()
            if rec.recruitment_block == 'store':
                rec.message_post(
                    body=_(
                        "Khối Cửa Hàng đã gửi yêu cầu duyệt. "
                        "Quản lý tuyển dụng cần phê duyệt trước khi cập nhật nhu cầu tuyển dụng."
                    )
                )

            rec.message_post(
                body=_("Đã tạo Approval Request %s và gửi duyệt.") % approval_request.name,
                message_type='notification'
            )

    def _send_activity_to_hr(self):
        """Gửi Activity cho HR group khi tất cả managers duyệt xong"""
        self.ensure_one()
        users = self.env['res.users'].browse()
        approval = self.x_psm_approval_request_id
        if approval:
            hr_approver = approval.approver_ids.filtered(
                lambda approver: approver.status == 'pending' and approver.sequence == 10
            )[:1]
            if hr_approver:
                users = hr_approver.user_id
        if not users:
            users = self._get_hr_approval_user()
        if self.recruitment_block == 'store':
            summary = _("Phê duyệt yêu cầu tuyển dụng: %s") % self.name
            note = _("Yêu cầu '%s' được tạo từ Portal và đang chờ Quản lý tuyển dụng phê duyệt.") % self.name
        else:
            summary = _("Kiểm tra Yêu cầu tuyển dụng: %s") % self.name
            note = _("Yêu cầu '%s' vừa được tạo và cần HR kiểm tra.") % self.name
        self._schedule_activity_for_users(
            users,
            summary,
            note,
        )

    def _send_activity_to_ceo(self):
        """Gửi Activity cho CEO group khi HR Validate"""
        self.ensure_one()
        users = self.env['res.users'].browse()
        approval = self.x_psm_approval_request_id
        if approval:
            ceo_approver = approval.approver_ids.filtered(
                lambda approver: approver.status == 'pending' and approver.sequence == 20
            )[:1]
            if ceo_approver:
                users = ceo_approver.user_id
        if not users:
            users = self._get_ceo_approval_user()
        self._schedule_activity_for_users(
            users,
            _("Phê duyệt yêu cầu tuyển dụng: %s") % self.name,
            _("Vui lòng duyệt yêu cầu '%s' đã được HR xác nhận.") % self.name,
        )

    def _schedule_activity_for_users(self, users, summary, note):
        self.ensure_one()
        if not users:
            return
        activity_type = self.env.ref('mail.mail_activity_data_todo', raise_if_not_found=False)
        if not activity_type:
            return
        model_name = self._name
        existing_activities = self.env['mail.activity'].search([
            ('res_model', '=', model_name),
            ('res_id', '=', self.id),
            ('user_id', 'in', users.ids),
            ('activity_type_id', '=', activity_type.id),
            ('summary', '=', summary),
        ])
        existing_user_ids = set(existing_activities.mapped('user_id').ids)
        for user in users:
            if user.id in existing_user_ids:
                continue
            self.activity_schedule(
                activity_type_id=activity_type.id,
                date_deadline=fields.Date.today(),
                user_id=user.id,
                summary=summary,
                note=note,
            )

    def _cleanup_open_activities(self):
        for rec in self:
            rec.activity_ids.unlink()

    def write(self, vals):
        res = super().write(vals)
        if vals.get('state') in ('done', 'cancel'):
            self._cleanup_open_activities()
        return res

    # Step 3: HR Validate
    def action_hr_validate(self):
        for rec in self:
            if rec.recruitment_block == 'store':
                rec._sync_state_from_approval_requests()
                continue
            if rec.x_psm_approval_request_id and rec.x_psm_approval_request_id.request_status == 'pending':
                rec._sync_state_from_approval_requests()
                continue
            rec.write({'state': 'ceo_approval'})
            rec._send_activity_to_ceo()

    def _find_existing_job_for_line(self, line):
        self.ensure_one()
        line_name = (line.position_name or '').strip()
        if not line_name or not line.department_id:
            return self.env['hr.job']

        domain = [
            ('department_id', '=', line.department_id.id),
            ('name', '=ilike', line_name),
        ]
        if line.recruitment_block:
            domain.append(('recruitment_type', '=', line.recruitment_block))
        if line.position_level:
            domain.append(('position_level', '=', line.position_level))
        return self.env['hr.job'].sudo().search(domain, order='id desc', limit=1)

    def _create_job_for_line(self, line):
        self.ensure_one()
        line_name = (line.position_name or '').strip()
        if not line_name:
            raise UserError(_("Không thể tạo vị trí tuyển dụng do thiếu tên vị trí."))

        department = line.department_id or self.department_id
        if not department:
            raise UserError(_("Không thể tạo vị trí tuyển dụng do thiếu phòng ban."))

        job_model = self.env['hr.job']
        line_block = line.recruitment_block or self.recruitment_block
        vals = {
            'name': line_name,
            'department_id': department.id,
            'company_id': department.company_id.id or self.company_id.id or self.env.company.id,
            'no_of_recruitment': 0,
            'active': True,
        }
        if 'recruitment_type' in job_model._fields and line_block:
            vals['recruitment_type'] = line_block
        if 'position_level' in job_model._fields and line.position_level:
            vals['position_level'] = line.position_level
        if 'work_location_id' in job_model._fields and line.work_location_id:
            vals['work_location_id'] = line.work_location_id.id
        if 'user_id' in job_model._fields and self.user_id:
            vals['user_id'] = self.user_id.id
        if 'oje_evaluator_user_id' in job_model._fields and self.user_id:
            vals['oje_evaluator_user_id'] = self.user_id.id

        job = job_model.sudo().create(vals)
        line.sudo().write({'job_id': job.id})
        return job

    def _resolve_job_for_line(self, line):
        self.ensure_one()
        if line.job_id:
            return line.job_id
        existing_job = self._find_existing_job_for_line(line)
        if existing_job:
            line.sudo().write({'job_id': existing_job.id})
            return existing_job
        return self._create_job_for_line(line)

    def _apply_approved_jobs(self):
        self.ensure_one()
        job_summary = {}

        if self.line_ids:
            for line in self.line_ids:
                qty = max(line.quantity or 0, 0)
                if not qty:
                    continue
                job = self._resolve_job_for_line(line)
                if not job:
                    continue
                job.sudo().write({
                    'no_of_recruitment': (job.no_of_recruitment or 0) + qty,
                    'active': True,
                })
                if job.id not in job_summary:
                    job_summary[job.id] = {'name': job.display_name, 'qty': 0}
                job_summary[job.id]['qty'] += qty
        elif self.request_type == 'unplanned' and self.job_id:
            qty = max(self.quantity or 0, 0)
            if qty:
                self.job_id.sudo().write({
                    'no_of_recruitment': (self.job_id.no_of_recruitment or 0) + qty,
                    'active': True,
                })
                job_summary[self.job_id.id] = {
                    'name': self.job_id.display_name,
                    'qty': qty,
                }

        if job_summary:
            body = ", ".join(
                "%s (+%s)" % (item['name'], item['qty'])
                for item in job_summary.values()
            )
            self.message_post(body=_("Đã cập nhật nhu cầu tuyển dụng cho: %s") % body)

    # Step 4: CEO Duyệt
    def action_ceo_approve(self):
        for rec in self:
            rec.write({'state': 'in_progress'})
            rec._apply_approved_jobs()
            rec.action_publish_jobs()

    def action_publish_jobs(self):
        """Update Job Positions and Publish them for unplanned requests"""
        self.ensure_one()
        published = False
        job_ids = self.line_ids.mapped('job_id')
        if self.job_id:
            job_ids |= self.job_id

        published_jobs = []
        for job in job_ids.filtered(lambda j: j):
            job.sudo().write({'website_published': True, 'active': True})
            published = True
            qty = sum(self.line_ids.filtered(lambda l: l.job_id == job).mapped('quantity')) or (self.quantity if self.job_id == job else 0)
            published_jobs.append((job.name, qty))
        if published:
            self.is_published = True
            if published_jobs:
                body = ", ".join(f"{name} ({qty})" for name, qty in published_jobs)
                self.message_post(body=_("Đã đăng tin %s lên Job Page.") % body)

    def action_done(self):
        self.write({'state': 'done'})

    def action_reject(self):
        for rec in self:
            if rec.x_psm_approval_request_id and rec.x_psm_approval_request_id.request_status in ('new', 'pending'):
                rec.x_psm_approval_request_id.sudo().action_cancel()
            rec.write({'state': 'cancel'})

    def action_view_job(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'hr.job',
            'view_mode': 'form',
            'res_id': self.job_id.id,
            'target': 'current',
        }

    def action_reset_draft(self):
        for rec in self:
            if rec.x_psm_approval_request_id and rec.x_psm_approval_request_id.request_status == 'pending':
                rec.x_psm_approval_request_id.sudo().action_cancel()
            rec.write({'state': 'draft'})

    def action_open_approval_request(self):
        self.ensure_one()
        if not self.x_psm_approval_request_id:
            return False
        return {
            'type': 'ir.actions.act_window',
            'name': _('Approval Request'),
            'res_model': 'approval.request',
            'view_mode': 'form',
            'res_id': self.x_psm_approval_request_id.id,
            'target': 'current',
        }

    def action_open_job_page(self):
        """Open the standard Odoo job page on website"""
        self.ensure_one()
        url = '/jobs'
        if self.request_type == 'unplanned' and self.job_id:
            job_url = self.job_id.website_url if hasattr(self.job_id, 'website_url') else False
            if job_url:
                url = job_url
        return {
            'type': 'ir.actions.act_url',
            'url': url,
            'target': 'new',
        }


class RecruitmentRequestLine(models.Model):
    _name = 'x_psm_recruitment_request_line'
    _description = 'Chi tiết yêu cầu tuyển dụng'

    request_id = fields.Many2one('x_psm_recruitment_request', string='Yêu cầu', ondelete='cascade')
    department_id = fields.Many2one('hr.department', string='Phòng ban', required=True)
    job_id = fields.Many2one('hr.job', string='Vị trí tuyển dụng')
    position_name = fields.Char(string='Tên vị trí')
    display_position_name = fields.Char(
        string='Vị trí tuyển dụng',
        compute='_compute_display_position_name',
    )
    recruitment_block = fields.Selection([
        ('store', 'Khối Cửa Hàng'),
        ('office', 'Khối Văn Phòng'),
    ], string='Khối tuyển dụng', default='office', required=True)
    position_level = fields.Selection([
        ('management', 'Quản Lý'),
        ('staff', 'Nhân Viên'),
    ], string='Cấp bậc')
    work_location_id = fields.Many2one('hr.work.location', string='Job Location')
    quantity = fields.Integer(string='Số lượng', default=1, required=True)
    planned_date = fields.Date(string='Thời gian dự kiến')
    date_start = fields.Date(string='Ngày bắt đầu')
    date_end = fields.Date(string='Ngày kết thúc')
    reason = fields.Text(string='Ghi chú/Mô tả')

    @api.depends('job_id', 'position_name')
    def _compute_display_position_name(self):
        for rec in self:
            rec.display_position_name = rec.job_id.display_name or (rec.position_name or '').strip() or '-'

    @api.onchange('job_id')
    def _onchange_job_id(self):
        for rec in self:
            if not rec.job_id:
                continue
            rec.position_name = rec.job_id.name
            if 'position_level' in rec.job_id._fields and rec.job_id.position_level:
                rec.position_level = rec.job_id.position_level
            if 'recruitment_type' in rec.job_id._fields and rec.job_id.recruitment_type:
                rec.recruitment_block = rec.job_id.recruitment_type
            if 'work_location_id' in rec.job_id._fields and rec.job_id.work_location_id:
                rec.work_location_id = rec.job_id.work_location_id

    @api.constrains('quantity')
    def _check_quantity(self):
        for rec in self:
            if (rec.quantity or 0) <= 0:
                raise ValidationError(_("Số lượng tuyển dụng phải lớn hơn 0."))

    @api.constrains('job_id', 'position_name')
    def _check_position_source(self):
        for rec in self:
            if not rec.job_id and not (rec.position_name or '').strip():
                raise ValidationError(_("Vui lòng chọn vị trí tuyển dụng hoặc nhập tên vị trí."))

    @api.constrains('request_id', 'job_id')
    def _check_office_line_has_job(self):
        for rec in self:
            if rec.request_id and rec.request_id.recruitment_block == 'office' and not rec.job_id:
                raise ValidationError(_("Khối Văn Phòng yêu cầu chọn vị trí tuyển dụng có sẵn cho từng dòng."))

    @api.model
    def default_get(self, fields):
        res = super().default_get(fields)
        dept_id = self.env.context.get('default_department_id')
        if dept_id:
            res.setdefault('department_id', dept_id)
        req_id = self.env.context.get('default_request_id')
        if req_id:
            request = self.env['x_psm_recruitment_request'].browse(req_id)
            if request.user_department_id:
                res.setdefault('department_id', request.user_department_id.id)
            if request.recruitment_block:
                res.setdefault('recruitment_block', request.recruitment_block)
        block = self.env.context.get('default_recruitment_block')
        if block in ('store', 'office'):
            res.setdefault('recruitment_block', block)
        return res

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('position_name') and vals.get('job_id'):
                job = self.env['hr.job'].browse(vals['job_id'])
                if job.exists():
                    vals['position_name'] = job.name
            if not vals.get('recruitment_block') and vals.get('request_id'):
                request = self.env['x_psm_recruitment_request'].browse(vals['request_id'])
                if request.exists() and request.recruitment_block:
                    vals['recruitment_block'] = request.recruitment_block
        return super().create(vals_list)
