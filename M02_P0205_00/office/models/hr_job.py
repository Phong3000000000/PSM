# -*- coding: utf-8 -*-
import json

from odoo import models, fields, api


class HrJob(models.Model):
    _inherit = 'hr.job'

    # recruitment_type is now owned by M02_P0204_00 (computed from department.block)
    # No re-declaration needed here.

    current_employee_count = fields.Integer(
        string="Current Employees",
        compute="_compute_current_employee_count",
        help="Số lượng nhân sự hiện đang giữ vị trí này.",
    )

    needed_recruitment = fields.Integer(
        string="Needed Recruitment",
        compute="_compute_needed_recruitment",
        help="Số lượng cần tuyển = target - số đang có (ít nhất 0).",
    )

    # ==================== SURVEY ====================
    survey_id = fields.Many2one(
        'survey.survey',
        string='Khảo Sát Năng Lực',
        domain=[('is_pre_interview', '=', True)],
        help='Bài khảo sát năng lực dành riêng cho vị trí này. '
             'Ứng viên sẽ được yêu cầu làm bài này sau khi nộp đơn.',
    )

    # ==================== WEBSITE CONTENT ====================
    job_intro = fields.Text(
        string='Mô tả công việc',
        help='Đoạn giới thiệu về vị trí này. Mỗi đoạn cách nhau bằng dòng trắng.',
    )
    responsibilities = fields.Text(
        string='Trách nhiệm công việc',
        help='Mỗi dòng = 1 mục trong danh sách Responsibilities.',
    )
    must_have = fields.Text(
        string='Yêu cầu bắt buộc',
        help='Mỗi dòng = 1 mục trong danh sách Must Have.',
    )
    nice_to_have = fields.Text(
        string='Yêu cầu thêm (Nice to have)',
        help='Mỗi dòng = 1 mục trong danh sách Nice to have.',
    )
    whats_great = fields.Text(
        string='Điểm nổi bật của công việc',
        help='Mỗi dòng = 1 mục trong danh sách "What\'s great in the job?".',
    )

    # ==================== HELPERS ====================

    def _is_office_job(self):
        """Check if this job is an office job. Uses computed recruitment_type from 0204."""
        self.ensure_one()
        return self.recruitment_type == 'office'

    def _is_office_job_vals(self, vals):
        """Check if vals would produce an office job, without saving."""
        temp = self.new(vals)
        return temp.recruitment_type == 'office'

    def _get_office_default_application_fields(self):
        """Office-specific default application fields used only by module 0205."""
        return [
            ('partner_name', 'Họ và tên', 'text', True, '6', 10, 'basic_info', True),
            ('email_from', 'Email liên hệ', 'email', True, '6', 20, 'basic_info', True),
            ('partner_phone', 'Số điện thoại', 'tel', True, '6', 30, 'basic_info', True),
            ('x_birthday', 'Ngày sinh', 'date', True, '6', 40, 'basic_info', True),
            ('x_gender', 'Giới tính', 'select', False, '6', 50, 'basic_info', True,
             '[{"value": "male", "label": "Nam"}, {"value": "female", "label": "Nữ"}, {"value": "not_display", "label": "Không muốn nêu"}]'),
            ('x_current_address', 'Địa chỉ hiện tại', 'text', True, '12', 60, 'basic_info', True),
            ('x_permanent_address', 'Địa chỉ thường trú', 'text', False, '12', 70, 'basic_info', True),
            ('x_hometown', 'Quê quán', 'text', False, '6', 80, 'basic_info', True),
            ('x_nationality', 'Quốc tịch', 'text', False, '6', 90, 'basic_info', True),

            ('x_current_job', 'Vị trí công việc hiện tại', 'text', False, '6', 10, 'other_info', True),
            ('x_years_experience', 'Số năm kinh nghiệm', 'number', False, '6', 20, 'other_info', True),
            ('x_last_company', 'Công ty gần nhất', 'text', False, '12', 30, 'other_info', True),
            ('x_application_content', 'Thư giới thiệu / Điểm nổi bật', 'textarea', False, '12', 40, 'other_info', True),
            ('x_education_level', 'Trình độ học vấn', 'select', False, '6', 50, 'other_info', True,
             '[{"value": "high_school", "label": "Trung học phổ thông"}, {"value": "vocational", "label": "Trung cấp"}, {"value": "college", "label": "Cao đẳng"}, {"value": "university", "label": "Đại học"}, {"value": "master", "label": "Thạc sĩ"}, {"value": "phd", "label": "Tiến sĩ"}, {"value": "others", "label": "Khác"}]'),
            ('x_school_name', 'Trường / Chuyên ngành', 'text', False, '6', 60, 'other_info', True),

            ('attachment', 'CV đính kèm', 'file', True, '12', 10, 'supplementary_question', True),
            ('x_portrait_image', 'Ảnh chân dung', 'file', False, '12', 20, 'supplementary_question', True),
            ('x_weekend_available', 'Có thể làm việc ngoài giờ khi cần', 'select', False, '6', 30, 'supplementary_question', True,
             '[{"value": "yes", "label": "Có"}, {"value": "no", "label": "Không"}]'),
            ('x_worked_mcdonalds', 'Đã từng làm việc tại McDonald’s Việt Nam', 'select', False, '6', 40, 'supplementary_question', True,
             '[{"value": "yes", "label": "Rồi"}, {"value": "no", "label": "Chưa"}]'),

            ('x_id_number', 'CCCD/CMND/Hộ chiếu', 'text', False, '6', 10, 'internal_question', True),
            ('x_id_issue_date', 'Ngày cấp giấy tờ tùy thân', 'date', False, '6', 20, 'internal_question', True),
            ('x_id_issue_place', 'Nơi cấp giấy tờ tùy thân', 'text', False, '12', 30, 'internal_question', True),
            ('x_referral_staff_id', 'Mã giới thiệu nội bộ', 'text', False, '12', 40, 'internal_question', True),
        ]

    def _load_application_fields_from_definitions(self, default_fields):
        """Shared loader for office-specific defaults while keeping custom fields intact."""
        self.ensure_one()
        core_names = ('partner_name', 'email_from', 'attachment')
        to_unlink = self.application_field_ids.filtered(
            lambda f: f.is_default and f.field_name not in core_names
        )
        to_unlink.unlink()

        core_fields = self.application_field_ids.filtered(
            lambda f: f.is_default and f.field_name in core_names
        )
        for cf in core_fields:
            if not cf.is_required or not cf.is_active:
                cf.write({'is_active': True, 'is_required': True})

        existing_core_names = set(core_fields.mapped('field_name'))
        vals_list = []
        for field_def in default_fields:
            if field_def[0] in existing_core_names:
                continue
            vals = {
                'job_id': self.id,
                'field_name': field_def[0],
                'field_label': field_def[1],
                'field_type': field_def[2],
                'is_required': field_def[3],
                'col_size': field_def[4],
                'sequence': field_def[5],
                'section': field_def[6],
                'is_active': field_def[7],
                'is_default': True,
            }
            if len(field_def) >= 9:
                vals['selection_options'] = field_def[8]
            vals_list.append(vals)

        if not vals_list:
            return True

        fields_created = self.env['job.application.field'].create(vals_list)
        for field_def in default_fields:
            if len(field_def) >= 9 and field_def[8]:
                field = fields_created.filtered(lambda x: x.field_name == field_def[0])
                if not field:
                    continue
                try:
                    options_json = json.loads(field_def[8])
                    for opt_vals in options_json:
                        self.env['job.application.field.option'].create({
                            'field_id': field.id,
                            'value': opt_vals['value'],
                            'name': opt_vals['label'],
                        })
                except Exception:
                    continue
        return True

    def action_load_default_fields(self):
        """Office jobs use 0205 defaults; other jobs keep 0204 behavior."""
        self.ensure_one()
        if not self._is_office_job():
            return super().action_load_default_fields()
        return self._load_application_fields_from_definitions(
            self._get_office_default_application_fields()
        )

    def _get_group_interviewer_users(self, xmlid):
        group = self.env.ref(xmlid, raise_if_not_found=False)
        return group.user_ids.filtered(lambda user: not user.share) if group else self.env['res.users']

    def _get_default_interviewer_users(self):
        self.ensure_one()
        users = self.env['res.users']
        manager = self.department_id.manager_id
        if manager and manager.user_id and not manager.user_id.share:
            users |= manager.user_id
        ceo_employee = self.company_id.ceo_id
        if ceo_employee and ceo_employee.user_id and not ceo_employee.user_id.share:
            users |= ceo_employee.user_id
        users |= self._get_group_interviewer_users('M02_P0205_00.group_gdh_rst_all_bod_recruitment_m')
        users |= self._get_group_interviewer_users('M02_P0205_00.group_gdh_rst_all_abu_recruitment_m')
        return users.filtered(lambda user: not user.share)

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
        res = super().write(vals)
        if not needs_sync or 'interviewer_ids' in vals:
            return res
        for rec in self.filtered(lambda job: job._is_office_job() and not job.interviewer_ids):
            default_users = rec._get_default_interviewer_users()
            if default_users:
                rec.with_context(skip_job_default_interviewers_sync=True).write({
                    'interviewer_ids': [(6, 0, default_users.ids)],
                })
        return res

    def action_go_to_portal_home(self):
        self.ensure_one()
        # Publish to website first
        self.write({'website_published': True})

        # Find or create a Blog for job postings
        blog = False

        # 1. Try to get blog from employee.referral.config
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
        """Force update the standard Job multi-company rule to allow reading published jobs"""
        res = super()._register_hook()
        rule = self.env.ref('hr.hr_job_comp_rule', raise_if_not_found=False)
        if rule:
            if 'website_published' not in rule.domain_force:
                rule.sudo().write({
                    'domain_force': "['|', ('website_published', '=', True), ('company_id', 'in', company_ids + [False])]",
                    'name': 'Job multi company rule (Published bypass)',
                })
                data = self.env['ir.model.data'].sudo().search([
                    ('module', '=', 'hr'),
                    ('name', '=', 'hr_job_comp_rule')
                ])
                if data:
                    data.write({'noupdate': False})
        return res

    def _compute_current_employee_count(self):
        for job in self:
            job.current_employee_count = self.env['hr.employee'].search_count([('job_id', '=', job.id)])

    @api.depends('no_of_recruitment', 'current_employee_count')
    def _compute_needed_recruitment(self):
        for job in self:
            needed = (job.no_of_recruitment or 0) - (job.current_employee_count or 0)
            job.needed_recruitment = needed if needed > 0 else 0
