# -*- coding: utf-8 -*-
import logging

from odoo import fields, http
from odoo.addons.portal.controllers.portal import CustomerPortal
from odoo.http import request

_logger = logging.getLogger(__name__)


class JobPortalHome(CustomerPortal):
    """Extend portal home to add job counts."""

    def _prepare_home_portal_values(self, counters):
        values = super()._prepare_home_portal_values(counters)
        if 'published_job_count' in counters:
            plan_line_count = request.env['recruitment.plan.line'].sudo().search_count([
                ('plan_id.state', '=', 'in_progress'),
                ('plan_id.is_sub_plan', '=', True),
                ('is_approved', '=', True),
                ('job_id.recruitment_type', '=', 'office'),
                ('job_id.website_published', '=', True),
                ('job_id.active', '=', True),
            ])
            unplanned_count = request.env['recruitment.request'].sudo().search_count([
                ('request_type', '=', 'unplanned'),
                ('state', '=', 'in_progress'),
                ('is_published', '=', True),
                ('job_id.recruitment_type', '=', 'office'),
                ('job_id.website_published', '=', True),
                ('job_id.active', '=', True),
            ])
            values['published_job_count'] = plan_line_count + unplanned_count
        return values


class JobPortal(http.Controller):

    def _get_office_apply_source_context(self, line_id=None, request_id=None):
        source_context = {
            'source_type': None,
            'source_title': None,
            'source_subtitle': None,
            'line_id': None,
            'request_id': None,
        }
        if line_id:
            line = request.env['recruitment.plan.line'].sudo().browse(int(line_id))
            if line.exists():
                source_context.update({
                    'source_type': 'plan_line',
                    'source_title': line.plan_id.name or 'Kế hoạch tuyển dụng',
                    'source_subtitle': line.planned_date and f"Thời gian dự kiến: {line.planned_date}" or None,
                    'line_id': line.id,
                })
        elif request_id:
            req = request.env['recruitment.request'].sudo().browse(int(request_id))
            if req.exists():
                source_context.update({
                    'source_type': 'request',
                    'source_title': req.name or 'Yêu cầu tuyển dụng',
                    'source_subtitle': 'Nguồn tuyển dụng đột xuất',
                    'request_id': req.id,
                })
        return source_context

    def _prepare_office_survey_questions(self, questions):
        type_labels = {
            'char_box': 'Trả lời ngắn',
            'text_box': 'Trả lời chi tiết',
            'numerical_box': 'Điền số',
            'date': 'Chọn ngày',
            'simple_choice': 'Chọn một đáp án',
            'multiple_choice': 'Chọn nhiều đáp án',
        }
        helper_texts = {
            'char_box': 'Nhập câu trả lời ngắn gọn, đúng trọng tâm.',
            'text_box': 'Trình bày đầy đủ và cụ thể theo kinh nghiệm thực tế của bạn.',
            'numerical_box': 'Nhập số liệu phù hợp với nội dung câu hỏi.',
            'date': 'Chọn mốc thời gian phù hợp nhất.',
            'simple_choice': 'Chọn một phương án đúng nhất với tình huống của bạn.',
            'multiple_choice': 'Bạn có thể chọn nhiều phương án nếu phù hợp.',
        }
        prepared = []
        for question in questions:
            q_title = (question.title or '').lower()
            if 'phỏng vấn' in q_title or 'pv' in q_title or 'schedule' in q_title:
                continue
            prepared.append({
                'question': question,
                'number': len(prepared) + 1,
                'type_label': type_labels.get(question.question_type, 'Câu hỏi'),
                'helper_text': helper_texts.get(question.question_type, ''),
            })
        return prepared

    def _build_office_form_sections(self, form_fields):
        label_overrides = {
            'partner_name': 'Họ và tên',
            'email_from': 'Email liên hệ',
            'attachment': 'CV đính kèm',
            'partner_phone': 'Số điện thoại',
            'x_current_job': 'Vị trí công việc hiện tại',
            'x_portrait_image': 'Ảnh chân dung',
            'x_birthday': 'Ngày sinh',
            'x_gender': 'Giới tính',
            'x_id_number': 'CCCD/CMND/Hộ chiếu',
            'x_id_issue_date': 'Ngày cấp giấy tờ tùy thân',
            'x_id_issue_place': 'Nơi cấp giấy tờ tùy thân',
            'x_permanent_address': 'Địa chỉ thường trú',
            'x_education_level': 'Trình độ học vấn',
            'x_school_name': 'Trường / chuyên ngành',
            'x_hometown': 'Quê quán',
            'x_current_address': 'Địa chỉ hiện tại',
            'x_years_experience': 'Số năm kinh nghiệm',
            'x_height': 'Chiều cao',
            'x_weight': 'Cân nặng',
            'x_nationality': 'Quốc tịch',
            'x_weekend_available': 'Có thể làm việc ngoài giờ khi cần',
            'x_worked_mcdonalds': 'Đã từng làm việc tại McDonald’s Việt Nam',
            'x_last_company': 'Công ty gần nhất',
            'x_referral_staff_id': 'Mã giới thiệu nội bộ',
            'x_application_content': 'Thư giới thiệu / Điểm nổi bật',
            'x_salutation': 'Danh xưng',
        }
        placeholder_overrides = {
            'partner_name': 'Nhập họ và tên đầy đủ',
            'email_from': 'example@email.com',
            'partner_phone': 'Nhập số điện thoại liên hệ',
            'x_current_job': 'Ví dụ: Digital Marketing Specialist',
            'x_birthday': 'Chọn ngày sinh',
            'x_current_address': 'Nhập địa chỉ hiện tại',
            'x_years_experience': 'Ví dụ: 3',
            'x_school_name': 'Tên trường / chuyên ngành',
            'x_last_company': 'Tên công ty gần nhất bạn làm việc',
            'x_application_content': 'Tóm tắt kinh nghiệm, điểm mạnh và lý do bạn phù hợp với vị trí này',
            'x_referral_staff_id': 'Nếu có người giới thiệu, nhập mã nhân viên tại đây',
        }
        help_overrides = {
            'attachment': 'Tải lên CV cập nhật mới nhất của bạn.',
            'x_portrait_image': 'Không bắt buộc, có thể bổ sung để hồ sơ đầy đủ hơn.',
            'x_weekend_available': 'Chỉ dùng để tham khảo mức độ linh hoạt của ứng viên.',
            'x_worked_mcdonalds': 'Thông tin hỗ trợ đội tuyển dụng tra cứu lịch sử làm việc nếu có.',
            'x_referral_staff_id': 'Bỏ trống nếu bạn không ứng tuyển qua giới thiệu nội bộ.',
        }
        section_specs = [
            {
                'key': 'personal',
                'title': '1. Thông tin cá nhân',
                'description': 'Thông tin liên hệ cơ bản để đội tuyển dụng có thể kết nối với bạn.',
                'header_style': 'background: linear-gradient(135deg, #0d6efd, #3b82f6); border-radius: 24px 24px 0 0;',
                'field_names': [
                    'partner_name', 'email_from', 'partner_phone', 'x_birthday',
                    'x_gender', 'x_current_address', 'x_permanent_address',
                    'x_hometown', 'x_nationality',
                ],
            },
            {
                'key': 'career',
                'title': '2. Kinh nghiệm và định hướng nghề nghiệp',
                'description': 'Cho chúng tôi biết về vị trí hiện tại, kinh nghiệm và bối cảnh làm việc gần nhất của bạn.',
                'header_style': 'background: linear-gradient(135deg, #0f766e, #14b8a6); border-radius: 24px 24px 0 0;',
                'field_names': [
                    'x_current_job', 'x_years_experience', 'x_last_company',
                    'x_application_content',
                ],
            },
            {
                'key': 'education',
                'title': '3. Học vấn và hồ sơ chuyên môn',
                'description': 'Thông tin phục vụ việc đánh giá nền tảng học vấn và hồ sơ ứng viên.',
                'header_style': 'background: linear-gradient(135deg, #7c3aed, #a855f7); border-radius: 24px 24px 0 0;',
                'field_names': [
                    'x_education_level', 'x_school_name', 'x_id_number',
                    'x_id_issue_date', 'x_id_issue_place',
                ],
            },
            {
                'key': 'attachments',
                'title': '4. Hồ sơ đính kèm',
                'description': 'Tải lên tài liệu cần thiết để hoàn thiện hồ sơ ứng tuyển.',
                'header_style': 'background: linear-gradient(135deg, #c2410c, #f97316); border-radius: 24px 24px 0 0;',
                'field_names': ['attachment', 'x_portrait_image'],
            },
            {
                'key': 'additional',
                'title': '5. Thông tin bổ sung',
                'description': 'Các thông tin thêm giúp đội tuyển dụng hiểu rõ hơn về mức độ phù hợp của hồ sơ.',
                'header_style': 'background: linear-gradient(135deg, #334155, #475569); border-radius: 24px 24px 0 0;',
                'field_names': [
                    'x_salutation', 'x_height', 'x_weight',
                    'x_weekend_available', 'x_worked_mcdonalds',
                    'x_referral_staff_id',
                ],
            },
        ]

        fields_by_name = {field.field_name: field for field in form_fields}
        consumed_names = set()
        sections = []

        for spec in section_specs:
            items = []
            for field_name in spec['field_names']:
                field = fields_by_name.get(field_name)
                if not field or not field.is_active:
                    continue
                items.append({
                    'field': field,
                    'display_label': label_overrides.get(field.field_name, field.field_label),
                    'placeholder': placeholder_overrides.get(field.field_name, ''),
                    'help_text': help_overrides.get(field.field_name, ''),
                })
                consumed_names.add(field.field_name)
            if items:
                sections.append({
                    'key': spec['key'],
                    'title': spec['title'],
                    'description': spec['description'],
                    'header_style': spec['header_style'],
                    'items': items,
                })

        remaining_items = []
        for field in form_fields:
            if field.field_name in consumed_names or not field.is_active:
                continue
            remaining_items.append({
                'field': field,
                'display_label': label_overrides.get(field.field_name, field.field_label),
                'placeholder': placeholder_overrides.get(field.field_name, ''),
                'help_text': help_overrides.get(field.field_name, ''),
            })

        if remaining_items:
            sections.append({
                'key': 'others',
                'title': '6. Thông tin khác',
                'description': 'Một số trường bổ sung chưa được phân loại riêng sẽ hiển thị tại đây.',
                'header_style': 'background: linear-gradient(135deg, #6b7280, #9ca3af); border-radius: 24px 24px 0 0;',
                'items': remaining_items,
            })

        return sections

    def _render_public_apply_page(self, job, source_context=None):
        """Render the unified public apply page with sudo so public users can access office jobs."""
        if not job or not job.exists() or not job.active:
            return request.render("website_hr_recruitment.index")

        job_sudo = job.sudo()
        if not job_sudo.application_field_ids:
            job_sudo._ensure_default_application_fields()
        section_order = {
            'basic_info': 1,
            'other_info': 2,
            'supplementary_question': 3,
            'internal_question': 4,
        }
        form_fields = job_sudo.application_field_ids.filtered('is_active').sorted(
            key=lambda f: (section_order.get(f.section, 99), f.sequence)
        )
        survey = job_sudo.generated_survey_template_id or job_sudo.survey_id
        questions = survey.sudo().question_ids if survey else []
        office_survey_questions = self._prepare_office_survey_questions(questions)
        office_form_sections = self._build_office_form_sections(form_fields)
        mandatory_office_question_count = len([
            item for item in office_survey_questions
            if item['question'].is_mandatory_correct
        ])

        schedule = False
        if job_sudo.recruitment_type == 'store':
            domain = [('state', '=', 'confirmed'), ('week_end_date', '>=', fields.Date.today())]
            if job_sudo.department_id:
                domain.append(('department_id', '=', job_sudo.department_id.id))
            schedule = request.env['interview.schedule'].sudo().search(
                domain, order='week_start_date asc', limit=1
            )

        return request.render("M02_P0205_00.office_job_apply_custom", {
            'job': job_sudo,
            'form_fields': form_fields,
            'office_form_sections': office_form_sections,
            'survey': survey,
            'questions': questions,
            'office_survey_questions': office_survey_questions,
            'mandatory_office_question_count': mandatory_office_question_count,
            'schedule': schedule,
            'submit_url': '/jobs/apply/submit',
            'apply_origin': 'office_0205',
            'source_context': source_context or {},
            'error': {},
            'default': {},
        })

    def _get_public_office_plan_lines(self):
        return request.env['recruitment.plan.line'].sudo().search([
            ('plan_id.state', '=', 'in_progress'),
            ('plan_id.is_sub_plan', '=', True),
            ('is_approved', '=', True),
            ('job_id', '!=', False),
            ('job_id.recruitment_type', '=', 'office'),
            ('job_id.website_published', '=', True),
            ('job_id.active', '=', True),
        ], order='plan_id asc, planned_date asc, id desc')

    def _group_lines_by_batch(self, lines):
        batches_dict = {}
        no_batch_lines = []

        for line in lines:
            batch = line.plan_id.batch_id
            if batch:
                key = batch.id
                if key not in batches_dict:
                    batches_dict[key] = {
                        'batch': batch,
                        'lines': [],
                    }
                batches_dict[key]['lines'].append(line)
            else:
                no_batch_lines.append(line)

        return list(batches_dict.values()), no_batch_lines

    def _get_public_office_unplanned_requests(self):
        return request.env['recruitment.request'].sudo().search([
            ('request_type', '=', 'unplanned'),
            ('state', '=', 'in_progress'),
            ('is_published', '=', True),
            ('job_id', '!=', False),
            ('job_id.recruitment_type', '=', 'office'),
            ('job_id.website_published', '=', True),
            ('job_id.active', '=', True),
        ], order='create_date desc')

    @http.route('/my/jobs', type='http', auth='user', website=True)
    def portal_published_jobs(self, **kw):
        """Show published office job listings for logged-in users."""
        lines = self._get_public_office_plan_lines()
        batches, no_batch_lines = self._group_lines_by_batch(lines)
        unplanned_requests = self._get_public_office_unplanned_requests()

        return request.render('M02_P0205_00.portal_my_published_jobs', {
            'batches': batches,
            'no_batch_lines': no_batch_lines,
            'unplanned_requests': unplanned_requests,
            'page_name': 'published_jobs',
        })

    @http.route('/office-jobs', type='http', auth='public', website=True)
    def public_office_jobs(self, **kw):
        """Public list of published office jobs without requiring login."""
        lines = self._get_public_office_plan_lines()
        batches, no_batch_lines = self._group_lines_by_batch(lines)
        unplanned_requests = self._get_public_office_unplanned_requests()

        return request.render('M02_P0205_00.office_job_public_list', {
            'batches': batches,
            'no_batch_lines': no_batch_lines,
            'unplanned_requests': unplanned_requests,
            'page_name': 'office_jobs_public',
        })

    @http.route('/jobs/detail/<int:line_id>', type='http', auth='public', website=True)
    def job_detail_and_apply(self, line_id, **kw):
        """Redirect published office recruitment plan lines to the real public apply page."""
        line = request.env['recruitment.plan.line'].sudo().browse(line_id)
        if (
            not line.exists()
            or line.plan_id.state != 'in_progress'
            or not line.plan_id.is_sub_plan
            or not line.is_approved
            or not line.job_id
            or line.job_id.recruitment_type != 'office'
            or not line.job_id.website_published
            or not line.job_id.active
        ):
            return request.redirect('/404')

        return request.redirect(f'/jobs/apply/{line.job_id.id}?line_id={line.id}')

    @http.route('/jobs/request/detail/<int:request_id>', type='http', auth='public', website=True)
    def job_request_detail_and_apply(self, request_id, **kw):
        """Redirect published unplanned office requests to the real public apply page."""
        req = request.env['recruitment.request'].sudo().browse(request_id)
        if (
            not req.exists()
            or req.request_type != 'unplanned'
            or req.state != 'in_progress'
            or not req.is_published
            or not req.job_id
            or req.job_id.recruitment_type != 'office'
            or not req.job_id.website_published
            or not req.job_id.active
        ):
            return request.redirect('/404')

        return request.redirect(f'/jobs/apply/{req.job_id.id}?request_id={req.id}')

    @http.route('/jobs/apply/<int:job_id>', type='http', auth='public', website=True)
    def office_job_apply_public(self, job_id, **kwargs):
        """Public apply route for office jobs using sudo, avoiding model-converter access issues."""
        job = request.env['hr.job'].sudo().browse(job_id)
        if (
            not job.exists()
            or job.recruitment_type != 'office'
            or not job.website_published
            or not job.active
        ):
            return request.redirect('/404')
        source_context = self._get_office_apply_source_context(
            line_id=kwargs.get('line_id'),
            request_id=kwargs.get('request_id'),
        )
        return self._render_public_apply_page(job, source_context=source_context)

    @http.route('/jobs/submit', type='http', auth='public', methods=['POST'], website=True, csrf=True)
    def job_apply_submit(self, **post):
        """Redirect to the unified apply route in M02_P0204_00."""
        line_id = post.get('line_id')
        request_id = post.get('request_id')

        if not line_id and not request_id:
            return request.redirect('/404')

        job = False
        if line_id:
            line = request.env['recruitment.plan.line'].sudo().browse(int(line_id))
            if line.exists():
                job = line.job_id
        elif request_id:
            req = request.env['recruitment.request'].sudo().browse(int(request_id))
            if req.exists():
                job = req.job_id

        if not job:
            return request.redirect('/404')

        return request.redirect(f'/jobs/apply/{job.id}')

    @http.route('/jobs/thankyou', type='http', auth='public', website=True)
    def job_thankyou(self, **kw):
        """Thank you page after application."""
        return request.render('M02_P0205_00.job_thankyou_template', {})
