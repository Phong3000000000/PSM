# -*- coding: utf-8 -*-
from odoo import http, _, exceptions
from odoo.http import request


class BackendOjeController(http.Controller):
    def _clean_text(self, value):
        return (value or '').strip()

    def _parse_int(self, value, min_value=None, max_value=None):
        if value in (None, ''):
            return False
        try:
            parsed = int(value)
        except (TypeError, ValueError):
            return False

        if min_value is not None and parsed < min_value:
            return False
        if max_value is not None and parsed > max_value:
            return False
        return parsed

    def _get_evaluation_with_access(self, evaluation_id):
        evaluation = request.env['x_psm_hr_applicant_oje_evaluation'].sudo().browse(evaluation_id)
        if not evaluation.exists():
            raise exceptions.UserError(_('Không tìm thấy phiếu đánh giá OJE.'))

        applicant = evaluation.applicant_id.with_env(request.env)
        applicant._check_backend_oje_access(user=request.env.user)
        return evaluation

    def _prepare_render_values(self, evaluation, success_message=False, error_message=False):
        if not evaluation or not evaluation.exists():
            return {
                'evaluation': evaluation,
                'staff_sections': request.env['x_psm_hr_applicant_oje_evaluation_section'],
                'management_sections': request.env['x_psm_hr_applicant_oje_evaluation_section'],
                'xfactor_lines': request.env['x_psm_hr_applicant_oje_evaluation_line'],
                'is_readonly': True,
                'success_message': success_message,
                'error_message': error_message,
            }

        staff_sections = evaluation.section_ids.filtered(
            lambda s: s.is_active and s.section_kind == 'staff_block'
        ).sorted('sequence')
        management_sections = evaluation.section_ids.filtered(
            lambda s: s.is_active and s.section_kind == 'management_dimension'
        ).sorted('sequence')

        xfactor_section = evaluation.section_ids.filtered(
            lambda s: s.is_active and s.section_kind == 'management_xfactor'
        )[:1]
        if xfactor_section:
            xfactor_lines = xfactor_section.line_ids.filtered(
                lambda l: l.is_active and l.line_kind == 'management_xfactor'
            ).sorted('sequence')
        else:
            xfactor_lines = evaluation.line_ids.filtered(
                lambda l: l.is_active and l.line_kind == 'management_xfactor'
            ).sorted('sequence')

        return {
            'evaluation': evaluation,
            'staff_sections': staff_sections,
            'management_sections': management_sections,
            'xfactor_lines': xfactor_lines,
            'is_readonly': evaluation.state == 'done',
            'success_message': success_message,
            'error_message': error_message,
        }

    def _write_common_header_values(self, evaluation, post):
        header_vals = {
            'trial_date': post.get('trial_date') or False,
            'trial_time': self._clean_text(post.get('trial_time')),
            'restaurant_name': self._clean_text(post.get('restaurant_name')),
            'shift_schedule': self._clean_text(post.get('shift_schedule')),
            'operation_consultant_name': self._clean_text(post.get('operation_consultant_name')),
            'interviewer_note': self._clean_text(post.get('interviewer_note')),
            'manager_signature_name': self._clean_text(post.get('manager_signature_name')),
        }
        evaluation.sudo().write(header_vals)

    def _write_staff_answers(self, evaluation, post):
        staff_lines = evaluation.line_ids.filtered(
            lambda l: l.is_active and l.line_kind == 'staff_question'
        )

        for line in staff_lines:
            rating = self._clean_text(post.get(f'line_{line.id}_rating')).lower()
            if rating not in ('ni', 'gd', 'ex', 'os'):
                rating = False
            line_comment = self._clean_text(post.get(f'line_{line.id}_comment'))
            line.sudo().write({
                'staff_rating': rating,
                'line_comment': line_comment,
            })

        staff_decision = self._clean_text(post.get('staff_decision'))
        if staff_decision not in ('reject', 'hire', 'other_position'):
            staff_decision = False

        evaluation.sudo().write({
            'staff_decision': staff_decision,
        })

    def _write_management_answers(self, evaluation, post):
        task_lines = evaluation.line_ids.filtered(
            lambda l: l.is_active and l.line_kind == 'management_task'
        )
        for line in task_lines:
            score = self._parse_int(post.get(f'line_{line.id}_score'), min_value=1, max_value=5)
            line_comment = self._clean_text(post.get(f'line_{line.id}_comment'))
            line.sudo().write({
                'management_score': score,
                'line_comment': line_comment,
            })

        xfactor_lines = evaluation.line_ids.filtered(
            lambda l: l.is_active and l.line_kind == 'management_xfactor'
        )
        for line in xfactor_lines:
            answer = self._clean_text(post.get(f'line_{line.id}_yn')).lower()
            if answer not in ('y', 'n'):
                answer = False
            line.sudo().write({'yes_no_answer': answer})

        evaluation.sudo().write({
            'overall_comments': self._clean_text(post.get('overall_comments')),
        })

    def _friendly_error_message(self, error):
        if isinstance(error, (exceptions.UserError, exceptions.ValidationError, exceptions.AccessError)):
            message = getattr(error, 'name', False)
            if not message and getattr(error, 'args', False):
                message = error.args[0]
            if not message:
                message = str(error)
            return message
        return _('Hệ thống chưa thể xử lý yêu cầu lúc này. Vui lòng thử lại.')

    def _is_xfactor_label(self, value):
        normalized = (value or '').strip().lower().replace(' ', '')
        return 'xfactor' in normalized or 'x-factor' in (value or '').strip().lower()

    def _group_questions_by_page(self, survey):
        ordered_items = survey.question_and_page_ids.sorted(lambda q: (q.sequence, q.id))
        pages = ordered_items.filtered('is_page')

        grouped = []
        if pages:
            unpaged_questions = ordered_items.filtered(lambda q: not q.is_page and not q.page_id).sorted('sequence')
            if unpaged_questions:
                grouped.append((False, unpaged_questions))

            for page in pages:
                page_questions = ordered_items.filtered(lambda q, p=page: (not q.is_page) and q.page_id == p).sorted('sequence')
                if page_questions:
                    grouped.append((page, page_questions))
            return grouped

        questions = ordered_items.filtered(lambda q: not q.is_page).sorted('sequence')
        if questions:
            grouped.append((False, questions))
        return grouped

    def _build_oje_snapshot_sections_from_survey(self, survey, scope):
        if not survey or scope not in ('store_staff', 'store_management'):
            return []

        prepared_sections = []
        section_sequence = 10

        for idx, (page, questions) in enumerate(self._group_questions_by_page(survey), start=1):
            page_title = (page.title if page else False) or (page.question if page else False) or _('Section %s') % idx
            objective_text = page.description if page and 'description' in page._fields else False

            if scope == 'store_staff':
                lines = []
                line_sequence = 10
                for question in questions:
                    question_text = (question.title or question.question or '').strip()
                    if not question_text:
                        continue
                    lines.append(
                        {
                            'source_question_id': question.id,
                            'sequence': line_sequence,
                            'name': question_text,
                            'question_text': question_text,
                            'line_kind': 'staff_question',
                            'scope': scope,
                            'rating_mode': 'staff_matrix',
                            'is_required': bool(question.constr_mandatory),
                            'is_active': True,
                            'field_type': 'radio',
                            'text_max_score': 0.0,
                            'checkbox_score': 0.0,
                        }
                    )
                    line_sequence += 10

                if lines:
                    prepared_sections.append(
                        {
                            'source_question_id': page.id if page else False,
                            'sequence': section_sequence,
                            'name': page_title,
                            'section_kind': 'staff_block',
                            'scope': scope,
                            'rating_mode': 'staff_matrix',
                            'objective_text': objective_text,
                            'hint_html': False,
                            'behavior_html': False,
                            'is_active': True,
                            'lines': lines,
                        }
                    )
                    section_sequence += 10
                continue

            section_kind_hint = page.x_psm_oje_section_kind if page and page.x_psm_oje_section_kind else 'auto'
            page_force_xfactor = section_kind_hint == 'management_xfactor'
            if section_kind_hint == 'auto' and self._is_xfactor_label(page_title):
                page_force_xfactor = True

            task_lines = []
            xfactor_lines = []
            line_sequence = 10

            for question in questions:
                question_text = (question.title or question.question or '').strip()
                if not question_text:
                    continue

                line_kind_hint = question.x_psm_oje_line_kind or 'auto'
                if line_kind_hint != 'auto':
                    line_kind = line_kind_hint
                elif page_force_xfactor or self._is_xfactor_label(question_text):
                    line_kind = 'management_xfactor'
                else:
                    line_kind = 'management_task'

                line_vals = {
                    'source_question_id': question.id,
                    'sequence': line_sequence,
                    'name': question_text,
                    'question_text': question_text,
                    'line_kind': line_kind,
                    'scope': scope,
                    'is_required': bool(question.constr_mandatory),
                    'is_active': True,
                }

                if line_kind == 'management_xfactor':
                    line_vals.update(
                        {
                            'rating_mode': 'xfactor_yes_no',
                            'field_type': 'checkbox',
                            'text_max_score': 0.0,
                            'checkbox_score': 1.0,
                        }
                    )
                    xfactor_lines.append(line_vals)
                else:
                    line_vals.update(
                        {
                            'line_kind': 'management_task',
                            'rating_mode': 'management_1_5',
                            'field_type': 'text',
                            'text_max_score': 5.0,
                            'checkbox_score': 0.0,
                        }
                    )
                    task_lines.append(line_vals)

                line_sequence += 10

            if task_lines:
                prepared_sections.append(
                    {
                        'source_question_id': page.id if page else False,
                        'sequence': section_sequence,
                        'name': page_title,
                        'section_kind': 'management_dimension',
                        'scope': scope,
                        'rating_mode': 'management_1_5',
                        'objective_text': objective_text,
                        'hint_html': False,
                        'behavior_html': False,
                        'is_active': True,
                        'lines': task_lines,
                    }
                )
                section_sequence += 10

            if xfactor_lines:
                section_name = page_title if page_force_xfactor else _('X-Factor')
                prepared_sections.append(
                    {
                        'source_question_id': page.id if page else False,
                        'sequence': section_sequence,
                        'name': section_name,
                        'section_kind': 'management_xfactor',
                        'scope': scope,
                        'rating_mode': 'xfactor_yes_no',
                        'objective_text': False,
                        'hint_html': False,
                        'behavior_html': False,
                        'is_active': True,
                        'lines': xfactor_lines,
                    }
                )
                section_sequence += 10

        return prepared_sections

    def _prepare_oje_preview_values(self, scope, section_records, line_active_field, title, back_url, intro_html=False):
        section_records = section_records.sorted('sequence')

        def _is_line_active(line):
            return bool(getattr(line, line_active_field, False))

        def _serialize_lines(lines):
            items = []
            index = 0
            for line in lines:
                index += 1
                items.append({
                    'index': index,
                    'text': line.question_text or line.name or '',
                })
            return items

        preview_staff_sections = []
        for section in section_records.filtered(lambda s: s.section_kind == 'staff_block'):
            lines = section.line_ids.filtered(
                lambda l: _is_line_active(l) and l.line_kind == 'staff_question'
            ).sorted('sequence')
            preview_staff_sections.append({
                'name': section.name,
                'lines': _serialize_lines(lines),
            })

        preview_management_sections = []
        for section in section_records.filtered(lambda s: s.section_kind == 'management_dimension'):
            lines = section.line_ids.filtered(
                lambda l: _is_line_active(l) and l.line_kind == 'management_task'
            ).sorted('sequence')
            preview_management_sections.append({
                'name': section.name,
                'objective_text': section.objective_text,
                'hint_html': section.hint_html,
                'behavior_html': section.behavior_html,
                'lines': _serialize_lines(lines),
            })

        preview_xfactor_lines = []
        xfactor_sections = section_records.filtered(lambda s: s.section_kind == 'management_xfactor')
        for section in xfactor_sections:
            xfactor_lines = section.line_ids.filtered(
                lambda l: _is_line_active(l) and l.line_kind == 'management_xfactor'
            ).sorted('sequence')
            preview_xfactor_lines.extend(_serialize_lines(xfactor_lines))

        return {
            'preview_title': title,
            'preview_scope': scope,
            'preview_intro_html': intro_html,
            'preview_staff_sections': preview_staff_sections,
            'preview_management_sections': preview_management_sections,
            'preview_xfactor_lines': preview_xfactor_lines,
            'back_url': back_url,
        }

    def _prepare_oje_preview_values_from_payload(self, scope, section_payloads, title, back_url, intro_html=False):
        sorted_sections = sorted(section_payloads, key=lambda section: section.get('sequence', 10))

        def _serialize_lines(lines):
            items = []
            for index, line in enumerate(sorted(lines, key=lambda item: item.get('sequence', 10)), start=1):
                items.append(
                    {
                        'index': index,
                        'text': line.get('question_text') or line.get('name') or '',
                    }
                )
            return items

        preview_staff_sections = []
        for section in sorted_sections:
            if section.get('section_kind') != 'staff_block':
                continue
            active_lines = [line for line in section.get('lines', []) if line.get('is_active') and line.get('line_kind') == 'staff_question']
            preview_staff_sections.append(
                {
                    'name': section.get('name'),
                    'lines': _serialize_lines(active_lines),
                }
            )

        preview_management_sections = []
        for section in sorted_sections:
            if section.get('section_kind') != 'management_dimension':
                continue
            active_lines = [line for line in section.get('lines', []) if line.get('is_active') and line.get('line_kind') == 'management_task']
            preview_management_sections.append(
                {
                    'name': section.get('name'),
                    'objective_text': section.get('objective_text'),
                    'hint_html': section.get('hint_html'),
                    'behavior_html': section.get('behavior_html'),
                    'lines': _serialize_lines(active_lines),
                }
            )

        preview_xfactor_lines = []
        for section in sorted_sections:
            if section.get('section_kind') != 'management_xfactor':
                continue
            active_lines = [line for line in section.get('lines', []) if line.get('is_active') and line.get('line_kind') == 'management_xfactor']
            preview_xfactor_lines.extend(_serialize_lines(active_lines))

        return {
            'preview_title': title,
            'preview_scope': scope,
            'preview_intro_html': intro_html,
            'preview_staff_sections': preview_staff_sections,
            'preview_management_sections': preview_management_sections,
            'preview_xfactor_lines': preview_xfactor_lines,
            'back_url': back_url,
        }

    @http.route('/recruitment/oje/template-preview/<int:template_id>', type='http', auth='user', website=True)
    def backend_oje_template_preview(self, template_id, **kwargs):
        user = request.env.user
        if not user.has_group('M02_P0200.GDH_RST_HR_RECRUITMENT_M'):
            raise exceptions.AccessError(_('Bạn không có quyền xem preview OJE.'))

        survey = request.env['survey.survey'].sudo().browse(template_id)
        if not survey.exists():
            raise exceptions.UserError(_('Không tìm thấy survey OJE để preview.'))

        survey.with_user(user).check_access_rights('read')
        survey.with_user(user).check_access_rule('read')

        scope = survey.x_psm_oje_scope
        if scope not in ('store_staff', 'store_management'):
            raise exceptions.UserError(_('Survey OJE chưa cấu hình PSM OJE Scope hợp lệ.'))

        sections_payload = self._build_oje_snapshot_sections_from_survey(survey, scope)
        values = self._prepare_oje_preview_values_from_payload(
            scope,
            sections_payload,
            title=f'{survey.title} (Preview)',
            back_url=f'/web#id={survey.id}&model=survey.survey&view_type=form',
            intro_html=survey.description,
        )
        return request.render('M02_P0204.backend_oje_template_preview_page', values)

    @http.route('/recruitment/oje/job-preview/<int:job_id>', type='http', auth='user', website=True)
    def backend_oje_job_preview(self, job_id, **kwargs):
        user = request.env.user
        if not user.has_group('M02_P0200.GDH_RST_HR_RECRUITMENT_M'):
            raise exceptions.AccessError(_('Bạn không có quyền xem preview OJE.'))

        job = request.env['hr.job'].sudo().browse(job_id)
        if not job.exists():
            raise exceptions.UserError(_('Không tìm thấy Job Position để preview OJE.'))

        job.with_user(user).check_access_rights('read')
        job.with_user(user).check_access_rule('read')

        scope = job._get_oje_template_scope()
        if not scope:
            raise exceptions.UserError(_('Chỉ hỗ trợ preview OJE cho job thuộc khối Cửa hàng.'))

        if not job.x_psm_oje_survey_id:
            raise exceptions.UserError(_('Job chưa cấu hình Survey OJE.'))

        sections_payload = job._x_psm_prepare_oje_snapshot_sections() if hasattr(job, '_x_psm_prepare_oje_snapshot_sections') else []
        values = self._prepare_oje_preview_values_from_payload(
            scope,
            sections_payload,
            title=f'{job.name} - OJE Preview',
            back_url=f'/web#id={job.id}&model=hr.job&view_type=form',
            intro_html=job.x_psm_oje_survey_id.description,
        )
        return request.render('M02_P0204.backend_oje_template_preview_page', values)

    @http.route('/recruitment/oje/internal/<int:evaluation_id>', type='http', auth='user', website=True)
    def backend_oje_form(self, evaluation_id, success=None, **kwargs):
        try:
            evaluation = self._get_evaluation_with_access(evaluation_id)
            applicant = evaluation.applicant_id.with_env(request.env)

            # Self-heal stale snapshot when user opens old URL directly.
            if evaluation.state != 'done':
                refreshed_evaluation = applicant.sudo()._ensure_oje_evaluation(evaluator_user=request.env.user)
                if refreshed_evaluation and refreshed_evaluation.id != evaluation.id:
                    return request.redirect(f'/recruitment/oje/internal/{refreshed_evaluation.id}')
                evaluation = refreshed_evaluation or evaluation
        except Exception as error:
            values = self._prepare_render_values(
                request.env['x_psm_hr_applicant_oje_evaluation'].browse(),
                error_message=self._friendly_error_message(error),
            )
            return request.render('M02_P0204.backend_oje_internal_page', values)

        values = self._prepare_render_values(
            evaluation,
            success_message=_('Lưu đánh giá OJE thành công.') if success else False,
        )
        return request.render('M02_P0204.backend_oje_internal_page', values)

    @http.route(
        '/recruitment/oje/internal/<int:evaluation_id>/submit',
        type='http',
        auth='user',
        methods=['POST'],
        website=True,
    )
    def backend_oje_submit(self, evaluation_id, **post):
        try:
            evaluation = self._get_evaluation_with_access(evaluation_id)
            applicant = evaluation.applicant_id.with_env(request.env)

            if evaluation.state != 'done':
                refreshed_evaluation = applicant.sudo()._ensure_oje_evaluation(evaluator_user=request.env.user)
                if refreshed_evaluation and refreshed_evaluation.id != evaluation.id:
                    return request.redirect(f'/recruitment/oje/internal/{refreshed_evaluation.id}')
                evaluation = refreshed_evaluation or evaluation

            if evaluation.state == 'done':
                raise exceptions.UserError(_('Phiếu đánh giá này đã được nộp và khóa chỉnh sửa.'))

            if evaluation.template_scope not in ('store_staff', 'store_management'):
                raise exceptions.UserError(_('Route này chỉ hỗ trợ form OJE store staff/management.'))

            self._write_common_header_values(evaluation, post)

            if evaluation.template_scope == 'store_staff':
                self._write_staff_answers(evaluation, post)
            else:
                self._write_management_answers(evaluation, post)

            evaluation.sudo().action_submit()
            return request.redirect(f'/recruitment/oje/internal/{evaluation.id}?success=1')

        except Exception as error:
            eval_fallback = request.env['x_psm_hr_applicant_oje_evaluation'].sudo().browse(evaluation_id)
            values = self._prepare_render_values(
                eval_fallback,
                error_message=self._friendly_error_message(error),
            )
            return request.render('M02_P0204.backend_oje_internal_page', values)
