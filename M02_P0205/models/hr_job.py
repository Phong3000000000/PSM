# -*- coding: utf-8 -*-
from odoo import _, api, exceptions, fields, models


class HrJob(models.Model):
    _inherit = 'hr.job'

    # recruitment_type is now owned by M02_P0204 (computed from department.block)
    # No re-declaration needed here.
    x_psm_0205_max_interview_round = fields.Integer(
        related='level_id.x_psm_0205_max_interview_round',
        string='So vong phong van',
        readonly=True,
    )

    x_psm_0205_current_employee_count = fields.Integer(
        string="Current Employees",
        compute="_compute_current_employee_count",
        help="Số lượng nhân sự hiện đang giữ vị trí này.",
    )

    x_psm_0205_needed_recruitment = fields.Integer(
        string="Needed Recruitment",
        compute="_compute_needed_recruitment",
        help="Số lượng cần tuyển = target - số đang có (ít nhất 0).",
    )

    x_psm_0205_is_office_job = fields.Boolean(
        string="Is Office Job",
        compute="_compute_is_office_job",
        store=True,
        compute_sudo=True,
        index=True,
        help="Cờ lưu sẵn để nhận diện job thuộc khối văn phòng.",
    )

    # ==================== WEBSITE CONTENT ====================
    x_psm_0205_job_intro = fields.Text(
        string='Mô tả công việc',
        help='Đoạn giới thiệu về vị trí này. Mỗi đoạn cách nhau bằng dòng trắng.',
    )
    x_psm_0205_responsibilities = fields.Text(
        string='Trách nhiệm công việc',
        help='Mỗi dòng = 1 mục trong danh sách x_psm_0205_responsibilities.',
    )
    x_psm_0205_must_have = fields.Text(
        string='Yêu cầu bắt buộc',
        help='Mỗi dòng = 1 mục trong danh sách Must Have.',
    )
    x_psm_0205_nice_to_have = fields.Text(
        string='Yêu cầu thêm (Nice to have)',
        help='Mỗi dòng = 1 mục trong danh sách Nice to have.',
    )
    x_psm_0205_whats_great = fields.Text(
        string='Điểm nổi bật của công việc',
        help='Mỗi dòng = 1 mục trong danh sách "What\'s great in the job?".',
    )

    # ==================== HELPERS ====================

    def _get_0205_company_for_config(self):
        self.ensure_one()
        return self.company_id or self.env.company

    def _is_office_department_block(self, block):
        """Return True when the department block matches the office block."""
        if not block:
            return False
        company = self._get_0205_company_for_config()
        block_code = (block.code or '').strip().upper()
        block_name = (block.name or '').strip().upper()
        office_codes = company._x_psm_0205_get_office_block_codes() if company else set()
        office_names = company._x_psm_0205_get_office_block_names() if company else set()
        if not office_codes and not office_names:
            office_codes = {'RST'}
            office_names = {'HEAD OFFICE'}
        return block_code in office_codes or block_name in office_names

    def _is_office_job(self):
        """Check if this job belongs to the office block through its stored flag."""
        self.ensure_one()
        return bool(self.x_psm_0205_is_office_job)

    def _is_office_job_vals(self, vals):
        """Check if vals would produce an office job, without saving."""
        temp = self.new(vals)
        return temp._is_office_job()

    def _is_interview_template_supported(self):
        self.ensure_one()
        return bool(self._is_office_job() or super()._is_interview_template_supported())

    def _get_group_interviewer_users(self, xmlid):
        group = self.env.ref(xmlid, raise_if_not_found=False)
        return group.user_ids.filtered(lambda user: not user.share) if group else self.env['res.users']

    def _get_default_interviewer_users(self):
        self.ensure_one()
        company = self._get_0205_company_for_config()
        users = self.env['res.users']
        if company.x_psm_0205_include_department_manager_interviewer:
            manager = self.department_id.manager_id
            if manager and manager.user_id and not manager.user_id.share:
                users |= manager.user_id
        if company.x_psm_0205_include_ceo_interviewer:
            ceo_employee = company.x_psm_0205_ceo_id
            if ceo_employee and ceo_employee.user_id and not ceo_employee.user_id.share:
                users |= ceo_employee.user_id
        bod_group = company._x_psm_0205_get_bod_interviewer_group() if company else False
        if bod_group:
            users |= bod_group.user_ids.filtered(lambda user: not user.share)
        abu_group = company._x_psm_0205_get_abu_interviewer_group() if company else False
        if abu_group:
            users |= abu_group.user_ids.filtered(lambda user: not user.share)
        return users.filtered(lambda user: not user.share)

    def _sync_related_applicant_skills(self):
        applicant_model = self.env['hr.applicant']
        for job in self:
            applicants = applicant_model.search([('job_id', '=', job.id)])
            if applicants:
                applicants._replace_skills_from_job()

    @api.onchange('department_id', 'company_id', 'recruitment_type')
    def _onchange_default_interviewer_ids(self):
        for rec in self:
            if not rec._is_office_job() or rec.interviewer_ids:
                continue
            rec.interviewer_ids = rec._get_default_interviewer_users()

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('interviewer_ids'):
                continue
            # Use helper to check if resulting job would be office type
            if not self._is_office_job_vals(vals):
                continue
            job = self.new(vals)
            default_users = job._get_default_interviewer_users()
            if default_users:
                vals['interviewer_ids'] = [(6, 0, default_users.ids)]
        return super().create(vals_list)

    def write(self, vals):
        if self.env.context.get('skip_job_default_interviewers_sync'):
            return super().write(vals)
        needs_sync = any(field in vals for field in ('department_id', 'company_id', 'recruitment_type'))
        needs_skill_sync = any(field in vals for field in ('current_job_skill_ids', 'job_skill_ids'))
        res = super().write(vals)
        if not needs_sync or 'interviewer_ids' in vals:
            if needs_skill_sync:
                self._sync_related_applicant_skills()
            return res
        for rec in self.filtered(lambda job: job._is_office_job() and not job.interviewer_ids):
            default_users = rec._get_default_interviewer_users()
            if default_users:
                rec.with_context(skip_job_default_interviewers_sync=True).write({
                    'interviewer_ids': [(6, 0, default_users.ids)],
                })
        if needs_skill_sync:
            self._sync_related_applicant_skills()
        return res

    def action_go_to_portal_home(self):
        self.ensure_one()
        # Publish to website first
        self.write({'website_published': True})

        company = self._get_0205_company_for_config()

        # Find or create a Blog for job postings
        blog = company.x_psm_0205_default_recruitment_blog_id if company else False

        # 1. Try to get blog from employee.referral.config
        if not blog:
            try:
                config = self.env['employee.referral.config'].sudo().search([('active', '=', True)], limit=1)
                if config and config.news_blog_id:
                    blog = config.news_blog_id
            except Exception:
                pass

        # 2. Fallback: find any blog with "tuyển dụng" or "recruitment" in name
        if not blog:
            blog = self.env['blog.blog'].sudo().search([
                '|',
                ('name', 'ilike', 'tuyển dụng'),
                ('name', 'ilike', 'recruitment'),
            ], limit=1)

        # 3. Last fallback: create a new Recruitment Blog
        if not blog:
            blog = self.env['blog.blog'].sudo().create({
                'name': 'Tin Tuyển Dụng',
            })
            try:
                config = self.env['employee.referral.config'].sudo().search([('active', '=', True)], limit=1)
                if config:
                    config.news_blog_id = blog.id
            except Exception:
                pass

        # Create Blog Post (check for duplicates)
        existing_post = self.env['blog.post'].sudo().search([
            ('blog_id', '=', blog.id),
            ('name', '=', f"TUYỂN DỤNG: {self.name}")
        ], limit=1)

        if not existing_post:
            content = f"""
                <div class="job_post_content">
                    <h3 class="text-primary">{self.name}</h3>
                    <p><b>Địa điểm:</b> {self.address_id.name or 'Văn phòng'}</p>
                    <p><b>Số lượng:</b> {self.no_of_recruitment}</p>
                    <hr/>
                    <div class="mt-3">
                        {self.description or 'Liên hệ HR để biết thêm chi tiết.'}
                    </div>
                    <p class="mt-4">
                        <a href="/jobs/detail/{self.id}" class="btn btn-primary" style="background-color: #DA291C; border-color: #DA291C; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">
                            Xem chi tiết &amp; Ứng tuyển
                        </a>
                    </p>
                </div>
            """
            post = self.env['blog.post'].sudo().create({
                'blog_id': blog.id,
                'name': f"TUYỂN DỤNG: {self.name}",
                'subtitle': f"Đang tuyển {self.no_of_recruitment} vị trí",
                'is_published': True,
                'content': content,
                'author_id': self.env.user.partner_id.id,
            })

            self.message_post(body=f"📢 Đã đăng tin tuyển dụng lên Portal: <b>{post.name}</b>")

            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Đăng tin thành công!',
                    'message': f'Đã tạo bài đăng "{post.name}" trên Portal.',
                    'type': 'success',
                    'next': {
                        'type': 'ir.actions.act_url',
                        'url': f'/blog/{blog.id}/post/{post.id}',
                        'target': 'new',
                    }
                }
            }
        else:
            existing_post.write({'is_published': True})
            self.message_post(body="ℹ️ Bài đăng tuyển dụng đã tồn tại và đã được kích hoạt lại.")
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Đã tồn tại',
                    'message': f'Bài đăng "{existing_post.name}" đang hiển thị trên Portal.',
                    'type': 'warning',
                    'next': {
                        'type': 'ir.actions.act_url',
                        'url': f'/blog/{blog.id}/post/{existing_post.id}',
                        'target': 'new',
                    }
                }
            }

    @api.model
    def _register_hook(self):
        """Keep standard multi-company job rule and neutralize broad recruitment rules."""
        res = super()._register_hook()
        rule = self.env.ref('hr.hr_job_comp_rule', raise_if_not_found=False)
        expected_domain = "[('company_id', 'in', company_ids + [False])]"
        if rule and (rule.domain_force != expected_domain or rule.name != 'Job multi company rule'):
            rule.sudo().write({
                'domain_force': expected_domain,
                'name': 'Job multi company rule',
            })

        # Disable broad backend rules that bypass department-scoped recruitment visibility.
        for xmlid in (
            'hr_recruitment.hr_job_user_rule',
            'hr_recruitment.hr_applicant_user_rule',
            'website_hr_recruitment.hr_job_officer',
            # Keep both ids for compatibility across hr_referral variants.
            'hr_referral.hr_applicant_officer',
            'hr_referral.hr_applicant_officer_rule',
        ):
            broad_rule = self.env.ref(xmlid, raise_if_not_found=False)
            if broad_rule and broad_rule.active:
                broad_rule.sudo().write({'active': False})
        return res

    def _compute_current_employee_count(self):
        for job in self:
            job.x_psm_0205_current_employee_count = self.env['hr.employee'].search_count([('job_id', '=', job.id)])

    @api.depends('no_of_recruitment', 'x_psm_0205_current_employee_count')
    def _compute_needed_recruitment(self):
        for job in self:
            needed = (job.no_of_recruitment or 0) - (job.x_psm_0205_current_employee_count or 0)
            job.x_psm_0205_needed_recruitment = needed if needed > 0 else 0

    @api.depends(
        'department_id',
        'department_id.block_id',
        'department_id.block_id.name',
        'department_id.block_id.code',
    )
    def _compute_is_office_job(self):
        for job in self:
            job.x_psm_0205_is_office_job = job._is_office_department_block(job.department_id.block_id)
