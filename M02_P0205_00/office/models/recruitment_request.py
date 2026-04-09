# -*- coding: utf-8 -*-
from odoo import models, fields, api, _

class RecruitmentRequestApprover(models.Model):
    """Danh sách Manager duyệt Yêu Cầu Tuyển Dụng theo Phòng Ban"""
    _name = 'recruitment.request.approver'
    _description = 'Manager Approver cho Yêu Cầu Tuyển Dụng'
    
    request_id = fields.Many2one('recruitment.request', string='Yêu Cầu', ondelete='cascade', required=True)
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
    _name = 'recruitment.request'
    _description = 'Yêu Cầu Tuyển Dụng'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'id desc'

    name = fields.Char(string='Mã Yêu Cầu', required=True, copy=False, readonly=True, index=True, default=lambda self: 'New')

    # Đợt tuyển dụng (chọn từ danh sách đợt)
    batch_id = fields.Many2one(
        'recruitment.batch', string='Đợt tuyển dụng',
        tracking=True,
        domain="[('state', '=', 'open')]",
        help='Chọn đợt tuyển dụng')

    # Step 1: Lập nhu cầu
    request_type = fields.Selection([
        ('unplanned', 'Đột xuất'),
        ('planned', 'Theo kế hoạch')
    ], string='Loại yêu cầu', default='unplanned', required=True, tracking=True)

    job_id = fields.Many2one('hr.job', string='Vị trí tuyển dụng', tracking=True)
    department_id = fields.Many2one('hr.department', string='Phòng ban', tracking=True)
    quantity = fields.Integer(string='Số lượng', default=1, tracking=True)
    date_start = fields.Date(string='Ngày bắt đầu', tracking=True)
    date_end = fields.Date(string='Ngày kết thúc', tracking=True)
    reason = fields.Text(string='Lý do tuyển dụng', required=True)

    line_ids = fields.One2many('recruitment.request.line', 'request_id', string='Chi tiết vị trí')
    approver_ids = fields.One2many('recruitment.request.approver', 'request_id', string='Manager duyệt')

    user_id = fields.Many2one('res.users', string='Người yêu cầu', default=lambda self: self.env.user, tracking=True)
    company_id = fields.Many2one('res.company', string='Công ty', default=lambda self: self.env.company)
    recruitment_plan_id = fields.Many2one('recruitment.plan', string='Kế hoạch tuyển dụng', readonly=True, tracking=True)

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
                 vals['name'] = self.env['ir.sequence'].next_by_code('recruitment.request') or 'New'
        return super(RecruitmentRequest, self).create(vals_list)

    def action_submit(self):
        """Gửi yêu cầu trực tiếp cho HR để kiểm tra"""
        self.write({'state': 'hr_validation'})
        self._send_activity_to_hr()
        self.message_post(
            body=_("Yêu cầu đã gửi đến HR để kiểm tra."),
            message_type='notification'
        )

    def _send_activity_to_hr(self):
        """Gửi Activity cho HR group khi tất cả managers duyệt xong"""
        self.ensure_one()
        hr_group = self.env.ref('M02_P0205_00.group_gdh_rst_hr_recruitment_m', raise_if_not_found=False)
        if not hr_group:
            hr_group = self.env.ref('hr.group_hr_manager', raise_if_not_found=False)
        self._schedule_activity_for_group(
            hr_group,
            _("Kiểm tra Yêu cầu tuyển dụng: %s") % self.name,
            _("Yêu cầu '%s' vừa được tạo và cần HR kiểm tra.") % self.name,
        )

    def _send_activity_to_ceo(self):
        """Gửi Activity cho CEO group khi HR Validate"""
        self.ensure_one()
        ceo_group = self.env.ref('M02_P0205_00.group_gdh_rst_all_ceo_recruitment_m', raise_if_not_found=False)
        self._schedule_activity_for_group(
            ceo_group,
            _("Phê duyệt yêu cầu tuyển dụng: %s") % self.name,
            _("Vui lòng duyệt yêu cầu '%s' đã được HR xác nhận.") % self.name,
        )

    def _schedule_activity_for_group(self, group, summary, note):
        if not group:
            return
        activity_type = self.env.ref('mail.mail_activity_data_todo', raise_if_not_found=False)
        if not activity_type:
            return
        users = group.user_ids.filtered(lambda user: not user.share)
        if not users:
            return
        for user in users:
            exists = self.env['mail.activity'].search_count([
                ('res_model', '=', 'recruitment.request'),
                ('res_id', '=', self.id),
                ('user_id', '=', user.id),
                ('activity_type_id', '=', activity_type.id),
                ('summary', '=', summary),
            ])
            if exists:
                continue
            self.activity_schedule(
                activity_type_id=activity_type.id,
                date_deadline=fields.Date.today(),
                user_id=user.id,
                summary=summary,
                note=note,
            )

    # Step 3: HR Validate
    def action_hr_validate(self):
        self.write({'state': 'ceo_approval'})
        self._send_activity_to_ceo()

    # Step 4: CEO Duyệt
    def action_ceo_approve(self):
        self.write({'state': 'in_progress'})
        lines = self.line_ids if self.line_ids else []
        if self.request_type == 'unplanned' and self.job_id:
            lines = lines or [self]

        for line in lines:
            job = line.job_id if isinstance(line, models.Model) else self.job_id
            qty = line.quantity if hasattr(line, 'quantity') else self.quantity
            if job and qty:
                job.no_of_recruitment += qty
        
        self.action_publish_jobs()

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
        self.write({'state': 'cancel'})

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
        self.write({'state': 'draft'})

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
    _name = 'recruitment.request.line'
    _description = 'Chi tiết yêu cầu tuyển dụng'

    request_id = fields.Many2one('recruitment.request', string='Yêu cầu', ondelete='cascade')
    department_id = fields.Many2one('hr.department', string='Phòng ban', required=True)
    job_id = fields.Many2one('hr.job', string='Vị trí tuyển dụng', required=True)
    quantity = fields.Integer(string='Số lượng', default=1, required=True)
    planned_date = fields.Date(string='Thời gian dự kiến')
    date_start = fields.Date(string='Ngày bắt đầu')
    date_end = fields.Date(string='Ngày kết thúc')
    reason = fields.Text(string='Ghi chú/Mô tả')

    @api.model
    def default_get(self, fields):
        res = super().default_get(fields)
        dept_id = self.env.context.get('default_department_id')
        if dept_id:
            res.setdefault('department_id', dept_id)
        req_id = self.env.context.get('default_request_id')
        if req_id:
            request = self.env['recruitment.request'].browse(req_id)
            if request.user_department_id:
                res.setdefault('department_id', request.user_department_id.id)
        return res
