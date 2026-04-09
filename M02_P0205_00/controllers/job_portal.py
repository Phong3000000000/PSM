# -*- coding: utf-8 -*-
import logging

from odoo import fields, http
from odoo.addons.M02_P0204_00.controllers.website_recruitment import WebsiteRecruitmentCustom
from odoo.addons.portal.controllers.portal import CustomerPortal
from odoo.http import request

_logger = logging.getLogger(__name__)


def _office_job_domain():
    return [('job_id.x_psm_0205_is_office_job', '=', True)]


class JobPortalHome(CustomerPortal):
    """Extend portal home to add job counts."""

    def _prepare_home_portal_values(self, counters):
        values = super()._prepare_home_portal_values(counters)
        if 'published_job_count' in counters:
            plan_line_count_domain = [
                ('plan_id.state', '=', 'in_progress'),
                ('plan_id.is_sub_plan', '=', True),
                ('is_approved', '=', True),
                ('job_id.x_psm_0205_is_office_job', '=', True),
                ('job_id.website_published', '=', True),
                ('job_id.active', '=', True),
            ]
            plan_line_count = request.env['x_psm_recruitment_plan_line'].sudo().search_count(plan_line_count_domain)
            unplanned_count_domain = [
                ('request_type', '=', 'unplanned'),
                ('state', '=', 'in_progress'),
                ('is_published', '=', True),
                ('job_id.x_psm_0205_is_office_job', '=', True),
                ('job_id.website_published', '=', True),
                ('job_id.active', '=', True),
            ]
            unplanned_count = request.env['x_psm_recruitment_request'].sudo().search_count(unplanned_count_domain)
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
            line = request.env['x_psm_recruitment_plan_line'].sudo().browse(int(line_id))
            if line.exists():
                source_context.update({
                    'source_type': 'plan_line',
                    'source_title': line.plan_id.name or 'Kế hoạch tuyển dụng',
                    'source_subtitle': line.planned_date and f"Thời gian dự kiến: {line.planned_date}" or None,
                    'line_id': line.id,
                })
        elif request_id:
            req = request.env['x_psm_recruitment_request'].sudo().browse(int(request_id))
            if req.exists():
                source_context.update({
                    'source_type': 'request',
                    'source_title': req.name or 'Yêu cầu tuyển dụng',
                    'source_subtitle': 'Nguồn tuyển dụng đột xuất',
                    'request_id': req.id,
                })
        return source_context

    def _prepare_office_survey_questions(self, questions, question_field_map=None):
        question_field_map = question_field_map or {}
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
            if (
                question.survey_id.x_psm_survey_usage == 'pre_interview'
                and question.x_psm_show_on_webform is False
            ):
                continue

            q_title = (question.title or '').lower()
            if 'phỏng vấn' in q_title or 'pv' in q_title or 'schedule' in q_title:
                continue

            linked_field = question_field_map.get(question.id) if question.id else False
            if question_field_map and not linked_field:
                continue

            input_name = linked_field.get('name') if linked_field else f'question_{question.id}'
            is_required = bool((linked_field and linked_field.get('required')) or question.x_psm_0204_is_mandatory_correct)
            prepared.append({
                'question': question,
                'number': len(prepared) + 1,
                'type_label': type_labels.get(question.question_type, 'Câu hỏi'),
                'helper_text': helper_texts.get(question.question_type, ''),
                'linked_field': linked_field or False,
                'input_name': input_name,
                'is_required': is_required,
            })
        return prepared

    def _get_office_webform_survey(self, job):
        survey = False
        if hasattr(job, '_x_psm_get_pre_interview_survey_for_webform'):
            try:
                survey = job._x_psm_get_pre_interview_survey_for_webform()
            except Exception as error_exc:
                _logger.warning(
                    'Cannot resolve office webform survey for job %s: %s',
                    job.id,
                    error_exc,
                )
        resolved_survey = survey or job.survey_id
        return resolved_survey.sudo() if resolved_survey else False

    def _normalize_office_property_field(self, field_data, fallback_sequence=999):
        if not isinstance(field_data, dict):
            return False

        field_name = field_data.get('name')
        if not field_name:
            return False

        sequence = field_data.get('sequence', fallback_sequence)
        try:
            sequence = int(sequence)
        except (TypeError, ValueError):
            sequence = fallback_sequence

        return {
            'name': field_name,
            'label': field_data.get('label') or field_data.get('string') or field_name.replace('_', ' ').title(),
            'type': field_data.get('type') or 'char',
            'required': bool(field_data.get('required') or field_data.get('is_required')),
            'default': field_data.get('default'),
            'selection': field_data.get('selection') or [],
            'sequence': sequence,
            'is_active': field_data.get('is_active', True),
            'widget': field_data.get('widget') or False,
            'source_survey_question_id': field_data.get('source_survey_question_id') or False,
            'mandatory_correct': bool(field_data.get('mandatory_correct')),
            'reject_when_wrong': bool(field_data.get('reject_when_wrong')),
            'correct_selection_values': field_data.get('correct_selection_values') or [],
        }

    def _get_office_core_property_fields(self):
        # Keep submit contract compatible with M02_P0204_00 /jobs/apply/submit.
        return [
            {
                'name': 'partner_name',
                'label': 'Họ và tên',
                'type': 'char',
                'required': True,
                'sequence': 10,
            },
            {
                'name': 'email_from',
                'label': 'Email liên hệ',
                'type': 'char',
                'required': True,
                'sequence': 20,
            },
            {
                'name': 'partner_phone',
                'label': 'Số điện thoại',
                'type': 'char',
                'required': False,
                'sequence': 30,
            },
            {
                'name': 'linkedin_profile',
                'label': 'LinkedIn Profile',
                'type': 'char',
                'required': False,
                'sequence': 40,
            },
            {
                'name': 'x_id_document_type',
                'label': 'Loại giấy tờ tùy thân',
                'type': 'selection',
                'selection': [
                    {'value': 'citizen_id', 'label': 'CCCD'},
                    {'value': 'passport', 'label': 'Hộ chiếu'},
                ],
                'default': 'citizen_id',
                'required': False,
                'sequence': 215,
            },
            {
                'name': 'x_id_number',
                'label': 'Số giấy tờ tùy thân',
                'type': 'char',
                'required': False,
                'sequence': 220,
            },
            {
                'name': 'x_cv_attachment',
                'label': 'CV đính kèm',
                'type': 'char',
                'required': True,
                'sequence': 390,
                'widget': 'file',
            },
            {
                'name': 'x_portrait_image',
                'label': 'Ảnh chân dung',
                'type': 'char',
                'required': False,
                'sequence': 400,
                'widget': 'file',
            },
        ]

    def _build_office_property_fields(self, job):
        dynamic_fields = []
        try:
            dynamic_fields = WebsiteRecruitmentCustom()._build_property_fields(job)
        except Exception as error_exc:
            _logger.warning('Cannot build office property fields for job %s: %s', job.id, error_exc)

        normalized_dynamic_fields = []
        for index, field_data in enumerate(dynamic_fields, start=1):
            normalized = self._normalize_office_property_field(field_data, fallback_sequence=index * 10)
            if normalized:
                normalized_dynamic_fields.append(normalized)

        if not normalized_dynamic_fields:
            return [], False

        fields_by_name = {field['name']: field for field in normalized_dynamic_fields}
        for core_field in self._get_office_core_property_fields():
            normalized_core = self._normalize_office_property_field(
                core_field,
                fallback_sequence=core_field.get('sequence', 999),
            )
            if not normalized_core:
                continue

            existing = fields_by_name.get(normalized_core['name'])
            if not existing:
                fields_by_name[normalized_core['name']] = normalized_core
                continue

            if normalized_core.get('required'):
                existing['required'] = True
            if normalized_core.get('widget'):
                existing['widget'] = normalized_core.get('widget')

        merged_fields = sorted(
            fields_by_name.values(),
            key=lambda item: (item.get('sequence', 999), item.get('name')),
        )
        return merged_fields, True

    def _build_office_question_field_map(self, property_fields):
        question_field_map = {}
        for field in property_fields:
            if not isinstance(field, dict) or field.get('is_active') is False:
                continue
            source_question_id = field.get('source_survey_question_id')
            try:
                source_question_id = int(source_question_id)
            except (TypeError, ValueError):
                source_question_id = 0

            if source_question_id and source_question_id not in question_field_map:
                question_field_map[source_question_id] = field
        return question_field_map

    def _build_office_extra_property_items(self, property_fields, question_field_map=None):
        question_field_map = question_field_map or {}
        label_overrides = {
            'partner_name': 'Họ và tên',
            'email_from': 'Email liên hệ',
            'x_cv_attachment': 'CV đính kèm',
            'attachment': 'CV đính kèm',
            'partner_phone': 'Số điện thoại',
            'x_current_job': 'Vị trí công việc hiện tại',
            'x_portrait_image': 'Ảnh chân dung',
            'x_birthday': 'Ngày sinh',
            'x_gender': 'Giới tính',
            'x_id_document_type': 'Loại giấy tờ tùy thân',
            'x_id_number': 'Số giấy tờ tùy thân',
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
            'x_id_number': 'Nhập số CCCD (12 số) hoặc hộ chiếu (chữ và số 6-12 ký tự)',
            'x_last_company': 'Tên công ty gần nhất bạn làm việc',
            'x_application_content': 'Tóm tắt kinh nghiệm, điểm mạnh và lý do bạn phù hợp với vị trí này',
            'x_referral_staff_id': 'Nếu có người giới thiệu, nhập mã nhân viên tại đây',
            'linkedin_profile': 'https://linkedin.com/in/your-profile',
        }
        help_overrides = {
            'x_cv_attachment': 'Tải lên CV cập nhật mới nhất của bạn.',
            'attachment': 'Tải lên CV cập nhật mới nhất của bạn.',
            'x_portrait_image': 'Không bắt buộc, có thể bổ sung để hồ sơ đầy đủ hơn.',
            'x_id_document_type': 'Chọn CCCD hoặc Hộ chiếu để hệ thống kiểm tra đúng định dạng số giấy tờ.',
            'x_id_number': 'CCCD: 12 chữ số. Hộ chiếu: chữ và số, độ dài từ 6 đến 12 ký tự.',
            'x_weekend_available': 'Chỉ dùng để tham khảo mức độ linh hoạt của ứng viên.',
            'x_worked_mcdonalds': 'Thông tin hỗ trợ đội tuyển dụng tra cứu lịch sử làm việc nếu có.',
            'x_referral_staff_id': 'Bỏ trống nếu bạn không ứng tuyển qua giới thiệu nội bộ.',
        }
        full_width_field_names = {'x_application_content', 'x_cv_attachment', 'x_portrait_image'}

        mapped_field_names = {
            field.get('name')
            for field in question_field_map.values()
            if isinstance(field, dict) and field.get('name')
        }

        items = []
        for field in property_fields:
            field_name = field.get('name') if isinstance(field, dict) else False
            if not field_name or field.get('is_active') is False or field_name in mapped_field_names:
                continue

            field_type = (field.get('type') or '').lower()
            col_size = 12 if field_type in ('text', 'html') or field_name in full_width_field_names else 6
            items.append({
                'field': field,
                'display_label': label_overrides.get(field_name, field.get('label') or field_name),
                'placeholder': placeholder_overrides.get(field_name, ''),
                'help_text': help_overrides.get(field_name, ''),
                'col_size': col_size,
            })

        return items

    def _render_public_apply_page(self, job, source_context=None):
        """Render the unified public apply page with sudo so public users can access office jobs."""
        if not job or not job.exists() or not job.active:
            return request.render("website_hr_recruitment.index")

        job_sudo = job.sudo()
        shared_builder = WebsiteRecruitmentCustom()
        property_fields = shared_builder._build_property_fields(job_sudo)
        apply_sections = shared_builder._build_apply_sections(job_sudo, property_fields=property_fields)
        has_property_schema = bool(apply_sections)
        survey = self._get_office_webform_survey(job_sudo)
        questions = survey.sudo().question_ids if survey else []
        office_survey_questions = []
        office_extra_property_items = []
        mandatory_office_question_count = 0

        schedule = False
        if job_sudo.recruitment_type == 'store':
            domain = [('state', '=', 'confirmed'), ('week_end_date', '>=', fields.Date.today())]
            if job_sudo.department_id:
                domain.append(('department_id', '=', job_sudo.department_id.id))
            schedule = request.env['interview.schedule'].sudo().search(
                domain, order='week_start_date asc', limit=1
            )

        return request.render("M02_P0205_00.psm_office_job_apply_custom", {
            'job': job_sudo,
            'property_fields': property_fields,
            'apply_sections': apply_sections,
            'has_property_schema': has_property_schema,
            'survey': survey,
            'questions': questions,
            'office_survey_questions': office_survey_questions,
            'office_extra_property_items': office_extra_property_items,
            'mandatory_office_question_count': mandatory_office_question_count,
            'schedule': schedule,
            'submit_url': '/jobs/apply/submit',
            'apply_origin': 'office_0205',
            'source_context': source_context or {},
            'error': {},
            'default': {},
        })

    def _get_public_office_plan_lines(self):
        domain = [
            ('plan_id.state', '=', 'in_progress'),
            ('plan_id.is_sub_plan', '=', True),
            ('is_approved', '=', True),
            ('job_id', '!=', False),
            ('job_id.x_psm_0205_is_office_job', '=', True),
            ('job_id.website_published', '=', True),
            ('job_id.active', '=', True),
        ]
        return request.env['x_psm_recruitment_plan_line'].sudo().search(domain, order='plan_id asc, planned_date asc, id desc')

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
        domain = [
            ('request_type', '=', 'unplanned'),
            ('state', '=', 'in_progress'),
            ('is_published', '=', True),
            ('job_id', '!=', False),
            ('job_id.x_psm_0205_is_office_job', '=', True),
            ('job_id.website_published', '=', True),
            ('job_id.active', '=', True),
        ]
        return request.env['x_psm_recruitment_request'].sudo().search(domain, order='create_date desc')

    @http.route('/my/jobs', type='http', auth='user', website=True)
    def portal_published_jobs(self, **kw):
        """Show published office job listings for logged-in users."""
        lines = self._get_public_office_plan_lines()
        batches, no_batch_lines = self._group_lines_by_batch(lines)
        unplanned_requests = self._get_public_office_unplanned_requests()

        return request.render('M02_P0205_00.psm_portal_my_published_jobs', {
            'batches': batches,
            'no_batch_lines': no_batch_lines,
            'unplanned_requests': unplanned_requests,
            'page_name': 'published_jobs',
        })

    @http.route('/jobs/detail/<int:line_id>', type='http', auth='public', website=True)
    def job_detail_and_apply(self, line_id, **kw):
        """Redirect published office recruitment plan lines to the real public apply page."""
        line = request.env['x_psm_recruitment_plan_line'].sudo().browse(line_id)
        if (
            not line.exists()
            or line.plan_id.state != 'in_progress'
            or not line.plan_id.is_sub_plan
            or not line.is_approved
            or not line.job_id
            or not line.job_id.x_psm_0205_is_office_job
            or not line.job_id.website_published
            or not line.job_id.active
        ):
            return request.redirect('/404')

        return request.redirect(f'/jobs/apply/{line.job_id.id}?line_id={line.id}')

    @http.route('/jobs/request/detail/<int:request_id>', type='http', auth='public', website=True)
    def job_request_detail_and_apply(self, request_id, **kw):
        """Redirect published unplanned office requests to the real public apply page."""
        req = request.env['x_psm_recruitment_request'].sudo().browse(request_id)
        if (
            not req.exists()
            or req.request_type != 'unplanned'
            or req.state != 'in_progress'
            or not req.is_published
            or not req.job_id
            or not req.job_id.x_psm_0205_is_office_job
            or not req.job_id.website_published
            or not req.job_id.active
        ):
            return request.redirect('/404')

        return request.redirect(f'/jobs/apply/{req.job_id.id}?request_id={req.id}')

    @http.route([
        '/jobs/apply/<int:job_id>',
        '/jobs/apply/<model("hr.job"):job>',
    ], type='http', auth='public', website=True)
    def office_job_apply_public(self, job_id=None, job=None, **kwargs):
        """Public apply route for office jobs, while delegating non-office jobs to the base flow."""
        job = job.sudo() if job else request.env['hr.job'].sudo().browse(job_id)
        if (
            not job.exists()
            or not job.website_published
            or not job.active
        ):
            return request.redirect('/404')
        if not job.x_psm_0205_is_office_job:
            return WebsiteRecruitmentCustom().website_job_apply_custom(job, **kwargs)
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
            line = request.env['x_psm_recruitment_plan_line'].sudo().browse(int(line_id))
            if line.exists():
                job = line.job_id
        elif request_id:
            req = request.env['x_psm_recruitment_request'].sudo().browse(int(request_id))
            if req.exists():
                job = req.job_id

        if not job:
            return request.redirect('/404')

        return request.redirect(f'/jobs/apply/{job.id}')

    @http.route('/jobs/thankyou', type='http', auth='public', website=True)
    def job_thankyou(self, **kw):
        """Thank you page after application."""
        return request.render('M02_P0205_00.psm_job_thankyou_template', {})
