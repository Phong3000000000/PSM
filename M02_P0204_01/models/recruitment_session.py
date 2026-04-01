# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError

class RecruitmentSession(models.Model):
    _name = 'mcd.recruitment.session'
    _description = 'MCD Recruitment Session'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Tên đợt tuyển dụng', required=True, tracking=True)
    store_id = fields.Many2one('hr.department', string='Cửa hàng / Phòng ban',
                              tracking=True)
    
    date_start = fields.Date(string='Ngày bắt đầu', tracking=True)
    date_end = fields.Date(string='Ngày kết thúc', tracking=True)
    
    state = fields.Selection([
        ('draft', 'Nháp'),
        ('ongoing', 'Đang diễn ra'),
        ('expired', 'Đã kết thúc'),
        ('closed', 'Đã đóng')
    ], string='Trạng thái', default='draft', tracking=True)
    
    line_ids = fields.One2many('mcd.recruitment.session.line', 'session_id', string='Chi tiết tuyển dụng')

    target = fields.Integer(
        string='Target',
        compute='_compute_target',
        store=True,
        help="Tổng số nhân viên cần tuyển trong đợt này (tự động cộng từ các dòng SL Cần tuyển)"
    )

    referral_request_count = fields.Integer(
        string='Yêu cầu giới thiệu',
        compute='_compute_referral_request_count',
    )

    @api.depends('line_ids.target_qty')
    def _compute_target(self):
        for session in self:
            session.target = sum(session.line_ids.mapped('target_qty'))

    def _compute_referral_request_count(self):
        ReferralRequest = self.env.get('employee.referral.request')
        for session in self:
            if ReferralRequest is not None:
                session.referral_request_count = ReferralRequest.search_count([
                    ('recruitment_session_id', '=', session.id)
                ])
            else:
                session.referral_request_count = 0

    def action_view_referral_requests(self):
        self.ensure_one()
        return {
            'name': 'Yêu cầu giới thiệu',
            'type': 'ir.actions.act_window',
            'res_model': 'employee.referral.request',
            'view_mode': 'list,form',
            'domain': [('recruitment_session_id', '=', self.id)],
            'context': {'default_recruitment_session_id': self.id},
        }

    def _auto_open_jobs(self):
        """Validate session has jobs, then auto-publish and open them."""
        for session in self:
            # 1. Phải có ít nhất một vị trí tuyển dụng
            if not session.line_ids:
                raise UserError(_(
                    'Đợt tuyển dụng "%s" phải có ít nhất một vị trí tuyển dụng trước khi bắt đầu.'
                ) % session.name)

            job_ids = session.line_ids.mapped('job_id').ids

            for line in session.line_ids:
                job = line.job_id
                if not job:
                    continue
                changes = {}

                # 2. Publish job position nếu chưa được publish
                if hasattr(job, 'is_published') and not job.is_published:
                    changes['is_published'] = True

                # 3. Đảm bảo no_of_recruitment đúng với target
                if job.no_of_recruitment != line.target_qty and line.target_qty > 0:
                    changes['no_of_recruitment'] = line.target_qty

                if changes:
                    job.sudo().write(changes)

            # 4. Activate draft referral programs linked to these jobs
            ProgramLine = self.env.get('employee.referral.program.line')
            if ProgramLine is not None:
                prog_lines = self.env['employee.referral.program.line'].sudo().search([
                    ('job_id', 'in', job_ids),
                ])
                programs_to_activate = prog_lines.mapped('program_id').filtered(
                    lambda p: p.state == 'draft'
                )
                if programs_to_activate:
                    programs_to_activate.write({'state': 'active'})

    def action_start(self):
        self._auto_open_jobs()
        self.write({'state': 'ongoing'})
        # Sync job targets now that session is active
        self.line_ids._sync_job_recruitment()
        # Publish referral programs linked to this session's jobs
        self._publish_referral_programs()

    def action_close(self):
        self.write({'state': 'closed'})
        # Reset job targets now that session is closed
        self.line_ids._sync_job_recruitment()

    def action_set_ongoing(self):
        self._auto_open_jobs()
        self.write({'state': 'ongoing'})
        self.line_ids._sync_job_recruitment()

    def _publish_referral_programs(self):
        """Tự động publish (activate) các chương trình giới thiệu liên quan đến phiên này."""
        ProgramLine = self.env.get('employee.referral.program.line')
        if ProgramLine is None:
            return
        job_ids = self.line_ids.mapped('job_id').ids
        if not job_ids:
            return
        prog_lines = self.env['employee.referral.program.line'].sudo().search([
            ('job_id', 'in', job_ids),
        ])
        programs_to_publish = prog_lines.mapped('program_id').filtered(
            lambda p: p.state in ('draft', 'approved')
        )
        for prog in programs_to_publish:
            try:
                prog.sudo().action_activate()
            except Exception:
                prog.sudo().write({'state': 'active'})

class RecruitmentSessionLine(models.Model):
    _name = 'mcd.recruitment.session.line'
    _description = 'MCD Recruitment Session Line'
    
    session_id = fields.Many2one('mcd.recruitment.session', string='Đợt tuyển dụng', ondelete='cascade')
    job_id = fields.Many2one(
        'hr.job',
        string='Vị trí',
        required=True,
    )

    target_qty = fields.Integer(string='Số lượng', default=1, required=True)
    hired_qty = fields.Integer(string='SL Đã tuyển', default=0, required=True)

    job_type = fields.Selection([
        ('fulltime', 'Full-time'),
        ('parttime', 'Part-time')
    ], string='Loại', required=True, default='fulltime')

    salary = fields.Float(string='Lương (VND)', default=0)
    bonus = fields.Float(string='Thưởng (VND)', default=0)
    date_start = fields.Date(string='Ngày bắt đầu')
    date_end = fields.Date(string='Ngày kết thúc')
    note = fields.Char(string='Ghi chú')

    missing_qty = fields.Integer(string='SL Còn thiếu', compute='_compute_missing_qty', store=True)

    # Tracking fields linked to hr.applicant
    new_applications = fields.Integer(
        string='Hồ sơ mới',
        compute='_compute_applicant_counts',
        help='Số ứng viên mới nhận trong đợt tuyển này'
    )
    in_progress = fields.Integer(
        string='Đang xử lý',
        compute='_compute_applicant_counts',
        help='Số ứng viên đang trong quy trình tuyển'
    )
    refused_count = fields.Integer(
        string='Từ chối',
        compute='_compute_applicant_counts',
        help='Số ứng viên đã từ chối/loại'
    )

    @api.depends('target_qty', 'hired_qty')
    def _compute_missing_qty(self):
        for rec in self:
            rec.missing_qty = max(0, rec.target_qty - rec.hired_qty)

    @api.depends('job_id', 'session_id', 'session_id.date_start', 'session_id.date_end')
    def _compute_applicant_counts(self):
        for rec in self:
            if not rec.job_id:
                rec.new_applications = 0
                rec.in_progress = 0
                rec.refused_count = 0
                continue

            domain_base = [('job_id', '=', rec.job_id.id)]
            # Filter by session date range if set
            if rec.session_id.date_start:
                domain_base.append(('create_date', '>=', rec.session_id.date_start))
            if rec.session_id.date_end:
                domain_base.append(('create_date', '<=', rec.session_id.date_end))

            Applicant = self.env['hr.applicant']

            # New = no stage (initial) or stage sequence == 1
            new_domain = domain_base + [('stage_id.sequence', '<=', 10), ('active', '=', True)]
            rec.new_applications = Applicant.search_count(new_domain)

            # In progress = active and not hired and not refused
            inprog_domain = domain_base + [
                ('active', '=', True),
                ('date_closed', '=', False),
            ]
            rec.in_progress = Applicant.search_count(inprog_domain)

            # Refused = active=False (archived) or priority refused
            refused_domain = [('job_id', '=', rec.job_id.id), ('active', '=', False)]
            if rec.session_id.date_start:
                refused_domain.append(('create_date', '>=', rec.session_id.date_start))
            rec.refused_count = Applicant.with_context(active_test=False).search_count(refused_domain)

    def action_view_applicants(self):
        """Open kanban/list view of applicants for this session line job."""
        self.ensure_one()
        domain = [('job_id', '=', self.job_id.id)]
        if self.session_id.date_start:
            domain.append(('create_date', '>=', self.session_id.date_start))
        if self.session_id.date_end:
            domain.append(('create_date', '<=', self.session_id.date_end))
        return {
            'name': f'Ứng Viên - {self.job_id.name} ({self.session_id.name})',
            'type': 'ir.actions.act_window',
            'res_model': 'hr.applicant',
            'view_mode': 'kanban,list,form',
            'domain': domain,
            'context': {
                'default_job_id': self.job_id.id,
                'default_recruitment_type': self.job_id.recruitment_type,
            },
        }

    def _sync_job_recruitment(self, job_ids=None):
        """Recalculate and update no_of_recruitment on hr.job from active session lines."""
        if job_ids is None:
            job_ids = self.mapped('job_id').ids
        if not job_ids:
            return
        for job in self.env['hr.job'].browse(job_ids):
            total = sum(
                self.search([
                    ('job_id', '=', job.id),
                    ('session_id.state', '=', 'ongoing'),
                ]).mapped('target_qty')
            )
            job.no_of_recruitment = total

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        records._sync_job_recruitment()
        return records

    def write(self, vals):
        old_jobs = self.mapped('job_id').ids
        res = super().write(vals)
        new_jobs = self.mapped('job_id').ids
        self._sync_job_recruitment(list(set(old_jobs + new_jobs)))
        return res

    def unlink(self):
        job_ids = self.mapped('job_id').ids
        res = super().unlink()
        if job_ids:
            for job in self.env['hr.job'].browse(job_ids):
                total = sum(
                    self.search([
                        ('job_id', '=', job.id),
                        ('session_id.state', '=', 'ongoing'),
                    ]).mapped('target_qty')
                )
                job.no_of_recruitment = total
        return res
