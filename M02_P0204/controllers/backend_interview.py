# -*- coding: utf-8 -*-
from odoo import http, _, exceptions
from odoo.http import request


class BackendInterviewController(http.Controller):
    def _clean_text(self, value):
        return (value or "").strip()

    def _parse_int(self, value, min_value=None, max_value=None):
        if value in (None, ""):
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

    def _friendly_error_message(self, error):
        if isinstance(error, (exceptions.UserError, exceptions.ValidationError, exceptions.AccessError)):
            message = getattr(error, "name", False)
            if not message and getattr(error, "args", False):
                message = error.args[0]
            if not message:
                message = str(error)
            return message
        return _("He thong chua the xu ly yeu cau luc nay. Vui long thu lai.")

    def _get_evaluation_with_access(self, evaluation_id):
        evaluation = request.env["x_psm_hr_applicant_interview_evaluation"].sudo().browse(evaluation_id)
        if not evaluation.exists():
            raise exceptions.UserError(_("Khong tim thay phieu danh gia Interview."))

        applicant = evaluation.applicant_id.with_env(request.env)
        applicant._check_backend_interview_access(user=request.env.user)
        return evaluation

    def _prepare_internal_values(self, evaluation, success_message=False, error_message=False):
        if not evaluation or not evaluation.exists():
            return {
                "evaluation": evaluation,
                "sections": request.env["x_psm_hr_applicant_interview_evaluation_section"],
                "prepared_sections": [],
                "is_readonly": True,
                "success_message": success_message,
                "error_message": error_message,
                "preview_mode": False,
            }

        sections = evaluation.section_ids.filtered("is_active").sorted("sequence")
        return {
            "evaluation": evaluation,
            "sections": sections,
            "prepared_sections": self._prepare_section_rows(sections, "is_active", include_answer=True),
            "is_readonly": evaluation.state == "done",
            "success_message": success_message,
            "error_message": error_message,
            "preview_mode": False,
        }

    def _split_interview_skillset_label(self, raw_label):
        if " - " not in raw_label:
            return False, raw_label
        left, right = raw_label.split(" - ", 1)
        left = (left or "").strip()
        right = (right or "").strip()
        if not left or not right:
            return False, raw_label
        return left, right

    def _build_interview_row(
        self,
        display_type,
        raw_label,
        current_subheader="",
        group_kind=False,
        group_label=False,
        line_id=False,
        selected_score=False,
        line_comment="",
    ):
        normalized_kind = (group_kind or "").strip()
        normalized_group_label = (group_label or "").strip()

        if display_type in ("section", "subheader") or normalized_kind == "subheader":
            return {
                "display_type": "subheader",
                "label": raw_label,
                "question_text": "",
                "skillset_group": False,
                "skillset_show_left": False,
                "skillset_left": "",
                "skillset_right": "",
                "skillset_rowspan": 0,
                "line_id": line_id,
                "selected_score": selected_score,
                "line_comment": line_comment,
                "x_psm_interview_group_kind": "subheader",
                "x_psm_interview_group_label": "",
            }

        skillset_group = False
        skillset_left = ""
        skillset_right = raw_label

        if normalized_kind == "skillset_child" and normalized_group_label:
            skillset_group = True
            skillset_left = normalized_group_label
            split_left, split_right = self._split_interview_skillset_label(raw_label)
            if split_left and split_right and split_left.lower() == normalized_group_label.lower():
                skillset_right = split_right
        elif normalized_kind == "skillset_child":
            split_left, split_right = self._split_interview_skillset_label(raw_label)
            if split_left and split_right:
                skillset_group = True
                skillset_left = split_left
                skillset_right = split_right
        elif normalized_kind in ("", "none", "question", "auto"):
            is_skillset_context = "skillset" in (current_subheader or "").lower()
            split_left, split_right = self._split_interview_skillset_label(raw_label)
            if is_skillset_context and split_left and split_right:
                skillset_group = True
                skillset_left = split_left
                skillset_right = split_right

        return {
            "display_type": "question",
            "label": "",
            "question_text": skillset_right if skillset_group else raw_label,
            "skillset_group": skillset_group,
            "skillset_show_left": False,
            "skillset_left": skillset_left,
            "skillset_right": skillset_right,
            "skillset_rowspan": 0,
            "line_id": line_id,
            "selected_score": selected_score,
            "line_comment": line_comment,
            "x_psm_interview_group_kind": "skillset_child" if skillset_group else "question",
            "x_psm_interview_group_label": skillset_left if skillset_group else "",
        }

    def _prepare_section_rows(self, section_records, line_active_field, include_answer=False):
        prepared_sections = []

        for section in section_records.sorted("sequence"):
            rows = []
            current_subheader = ""

            active_lines = section.line_ids.filtered(
                lambda line: bool(getattr(line, line_active_field, False))
            ).sorted("sequence")

            for line in active_lines:
                display_type = line.display_type or "question"
                raw_label = (line.label or line.question_text or "").strip()
                row = self._build_interview_row(
                    display_type=display_type,
                    raw_label=raw_label,
                    current_subheader=current_subheader,
                    group_kind=getattr(line, "x_psm_interview_group_kind", False),
                    group_label=getattr(line, "x_psm_interview_group_label", False),
                    line_id=line.id if include_answer else False,
                    selected_score=line.selected_score if include_answer else False,
                    line_comment=line.line_comment if include_answer else "",
                )
                rows.append(row)
                if row.get("display_type") == "subheader":
                    current_subheader = row.get("label") or ""

            index = 0
            while index < len(rows):
                row = rows[index]
                if not row.get("skillset_group"):
                    index += 1
                    continue

                left_key = row.get("skillset_left")
                tail = index
                while tail < len(rows):
                    probe = rows[tail]
                    if probe.get("display_type") != "question":
                        break
                    if not probe.get("skillset_group"):
                        break
                    if probe.get("skillset_left") != left_key:
                        break
                    tail += 1

                rowspan = max(1, tail - index)
                rows[index]["skillset_show_left"] = True
                rows[index]["skillset_rowspan"] = rowspan
                for hidden_idx in range(index + 1, tail):
                    rows[hidden_idx]["skillset_show_left"] = False
                    rows[hidden_idx]["skillset_rowspan"] = 0

                index = tail

            prepared_sections.append({
                "name": section.name,
                "rows": rows,
            })

        return prepared_sections

    def _prepare_section_rows_from_payload(self, section_payloads, include_answer=False):
        prepared_sections = []

        sorted_sections = sorted(section_payloads, key=lambda section: section.get("sequence", 10))
        for section in sorted_sections:
            rows = []
            current_subheader = ""

            sorted_lines = sorted(section.get("lines", []), key=lambda line: line.get("sequence", 10))
            for line in sorted_lines:
                display_type = line.get("display_type") or "question"
                raw_label = (line.get("label") or line.get("question_text") or "").strip()
                line_ref = (line.get("line_id") or line.get("source_question_id")) if include_answer else False
                row = self._build_interview_row(
                    display_type=display_type,
                    raw_label=raw_label,
                    current_subheader=current_subheader,
                    group_kind=line.get("x_psm_interview_group_kind"),
                    group_label=line.get("x_psm_interview_group_label"),
                    line_id=line_ref,
                    selected_score=line.get("selected_score") if include_answer else False,
                    line_comment=line.get("line_comment") if include_answer else "",
                )
                rows.append(row)
                if row.get("display_type") == "subheader":
                    current_subheader = row.get("label") or ""

            index = 0
            while index < len(rows):
                row = rows[index]
                if not row.get("skillset_group"):
                    index += 1
                    continue

                left_key = row.get("skillset_left")
                tail = index
                while tail < len(rows):
                    probe = rows[tail]
                    if probe.get("display_type") != "question":
                        break
                    if not probe.get("skillset_group"):
                        break
                    if probe.get("skillset_left") != left_key:
                        break
                    tail += 1

                rowspan = max(1, tail - index)
                rows[index]["skillset_show_left"] = True
                rows[index]["skillset_rowspan"] = rowspan
                for hidden_idx in range(index + 1, tail):
                    rows[hidden_idx]["skillset_show_left"] = False
                    rows[hidden_idx]["skillset_rowspan"] = 0

                index = tail

            prepared_sections.append(
                {
                    "name": section.get("name") or _("Section"),
                    "rows": rows,
                }
            )

        return prepared_sections

    def _group_survey_questions(self, survey):
        ordered_items = survey.question_and_page_ids.sorted(lambda q: (q.sequence, q.id))
        pages = ordered_items.filtered("is_page")

        grouped = []
        if pages:
            unpaged_questions = ordered_items.filtered(lambda q: not q.is_page and not q.page_id).sorted("sequence")
            if unpaged_questions:
                grouped.append((False, unpaged_questions))

            for page in pages:
                page_questions = ordered_items.filtered(lambda q, p=page: (not q.is_page) and q.page_id == p).sorted("sequence")
                if page_questions:
                    grouped.append((page, page_questions))
            return grouped

        questions = ordered_items.filtered(lambda q: not q.is_page).sorted("sequence")
        if questions:
            grouped.append((False, questions))
        return grouped

    def _build_interview_payload_line(self, question, sequence):
        question_text = (question.title or question.question or "").strip()
        if not question_text:
            return False

        line_kind_hint = (question.x_psm_interview_line_kind or "auto").strip()
        group_label = (question.x_psm_interview_group_label or "").strip()

        display_type = "question"
        label = False
        output_question_text = question_text
        group_kind = "question"

        if line_kind_hint == "subheader":
            display_type = "subheader"
            label = question_text
            output_question_text = False
            group_kind = "subheader"
        elif line_kind_hint == "skillset_child":
            group_kind = "skillset_child"
            split_left, split_right = self._split_interview_skillset_label(question_text)
            if split_left and split_right:
                if not group_label:
                    group_label = split_left
                if group_label and split_left.lower() == group_label.lower():
                    output_question_text = split_right
        elif line_kind_hint == "question":
            group_kind = "question"
        else:
            split_left, split_right = self._split_interview_skillset_label(question_text)
            if split_left and split_right:
                normalized_left = split_left.lower()
                if "skillset" in normalized_left:
                    group_kind = "skillset_child"
                    if not group_label:
                        group_label = split_left
                    output_question_text = split_right

        if group_kind != "skillset_child":
            group_label = False

        is_required = bool(question.constr_mandatory) if display_type == "question" else False
        return {
            "source_question_id": question.id,
            "sequence": sequence,
            "display_type": display_type,
            "label": label,
            "question_text": output_question_text,
            "x_psm_interview_group_kind": group_kind,
            "x_psm_interview_group_label": group_label,
            "is_required": is_required,
            "is_active": True,
        }

    def _build_interview_section_payload(self, survey):
        payload = []
        section_sequence = 10
        for idx, (page, questions) in enumerate(self._group_survey_questions(survey), start=1):
            section_name = (page.title if page else False) or (page.question if page else False) or _("Section %s") % idx
            lines = []
            line_sequence = 10
            for question in questions:
                line_payload = self._build_interview_payload_line(question, line_sequence)
                if not line_payload:
                    continue
                lines.append(line_payload)
                line_sequence += 10

            if lines:
                payload.append(
                    {
                        "source_question_id": page.id if page else False,
                        "sequence": section_sequence,
                        "name": section_name,
                        "is_active": True,
                        "lines": lines,
                    }
                )
                section_sequence += 10
        return payload

    def _prepare_preview_values(self, preview_title, preview_intro_html, preview_sections, back_url):
        return {
            "preview_mode": True,
            "preview_title": preview_title,
            "preview_intro_html": preview_intro_html,
            "prepared_sections": preview_sections,
            "back_url": back_url,
        }

    def _write_answers(self, evaluation, post):
        evaluation.sudo().write({
            "interview_date": post.get("interview_date") or False,
            "interviewer_name": self._clean_text(post.get("interviewer_name")),
            "onboard_time": self._clean_text(post.get("onboard_time")),
            "overall_note": self._clean_text(post.get("overall_note")),
        })

        question_lines = evaluation.line_ids.filtered(
            lambda line: line.is_active and line.display_type == "question"
        )
        for line in question_lines:
            score = self._parse_int(post.get(f"line_{line.id}_score"), min_value=1, max_value=5)
            line.sudo().write({
                "selected_score": score,
                "line_comment": self._clean_text(post.get(f"line_{line.id}_comment")),
            })

    @http.route('/recruitment/interview/internal/<int:evaluation_id>', type='http', auth='user', website=True)
    def backend_interview_form(self, evaluation_id, success=None, **kwargs):
        try:
            evaluation = self._get_evaluation_with_access(evaluation_id)
            applicant = evaluation.applicant_id.with_env(request.env)

            if evaluation.state != 'done':
                refreshed = applicant.sudo()._ensure_interview_evaluation(evaluator_user=request.env.user)
                if refreshed and refreshed.id != evaluation.id:
                    return request.redirect(f'/recruitment/interview/internal/{refreshed.id}')
                evaluation = refreshed or evaluation

            values = self._prepare_internal_values(
                evaluation,
                success_message=_("Luu danh gia Interview thanh cong.") if success else False,
            )
            return request.render('M02_P0204.backend_interview_internal_page', values)

        except Exception as error:
            values = self._prepare_internal_values(
                request.env['x_psm_hr_applicant_interview_evaluation'].browse(),
                error_message=self._friendly_error_message(error),
            )
            return request.render('M02_P0204.backend_interview_internal_page', values)

    @http.route(
        '/recruitment/interview/internal/<int:evaluation_id>/submit',
        type='http',
        auth='user',
        methods=['POST'],
        website=True,
    )
    def backend_interview_submit(self, evaluation_id, **post):
        try:
            evaluation = self._get_evaluation_with_access(evaluation_id)
            if evaluation.state == 'done':
                raise exceptions.UserError(_("Phieu Interview da nop va khoa chinh sua."))

            self._write_answers(evaluation, post)
            evaluation.sudo().action_submit()
            return request.redirect(f'/recruitment/interview/internal/{evaluation.id}?success=1')

        except Exception as error:
            eval_fallback = request.env['x_psm_hr_applicant_interview_evaluation'].sudo().browse(evaluation_id)
            values = self._prepare_internal_values(
                eval_fallback,
                error_message=self._friendly_error_message(error),
            )
            return request.render('M02_P0204.backend_interview_internal_page', values)

    @http.route('/recruitment/interview/template-preview/<int:template_id>', type='http', auth='user', website=True)
    def backend_interview_template_preview(self, template_id, **kwargs):
        user = request.env.user
        if not user.has_group('M02_P0200.GDH_RST_HR_RECRUITMENT_M'):
            raise exceptions.AccessError(_("Ban khong co quyen xem preview Interview."))

        survey = request.env['survey.survey'].sudo().browse(template_id)
        if not survey.exists():
            raise exceptions.UserError(_("Khong tim thay survey Interview de preview."))

        survey.with_user(user).check_access_rights('read')
        survey.with_user(user).check_access_rule('read')

        section_payload = self._build_interview_section_payload(survey)
        preview_sections = self._prepare_section_rows_from_payload(section_payload, include_answer=False)
        values = self._prepare_preview_values(
            preview_title=f'{survey.title} (Preview)',
            preview_intro_html=survey.description,
            preview_sections=preview_sections,
            back_url=f'/web#id={survey.id}&model=survey.survey&view_type=form',
        )
        return request.render('M02_P0204.backend_interview_preview_page', values)

    @http.route('/recruitment/interview/job-preview/<int:job_id>', type='http', auth='user', website=True)
    def backend_interview_job_preview(self, job_id, **kwargs):
        user = request.env.user
        if not user.has_group('M02_P0200.GDH_RST_HR_RECRUITMENT_M'):
            raise exceptions.AccessError(_("Ban khong co quyen xem preview Interview."))

        job = request.env['hr.job'].sudo().browse(job_id)
        if not job.exists():
            raise exceptions.UserError(_("Khong tim thay Job Position de preview Interview."))

        job.with_user(user).check_access_rights('read')
        job.with_user(user).check_access_rule('read')

        if not job._is_interview_template_supported():
            raise exceptions.UserError(_("Job nay chua ho tro preview Interview. Kiem tra cau hinh recruitment type va level."))

        if not job.x_psm_interview_survey_id:
            raise exceptions.UserError(_("Job chua cau hinh Survey Interview."))

        section_payload = job._x_psm_prepare_interview_snapshot_sections() if hasattr(job, '_x_psm_prepare_interview_snapshot_sections') else []
        preview_sections = self._prepare_section_rows_from_payload(section_payload, include_answer=False)
        values = self._prepare_preview_values(
            preview_title=f'{job.name} - Interview Preview',
            preview_intro_html=job.x_psm_interview_survey_id.description,
            preview_sections=preview_sections,
            back_url=f'/web#id={job.id}&model=hr.job&view_type=form',
        )
        return request.render('M02_P0204.backend_interview_preview_page', values)
