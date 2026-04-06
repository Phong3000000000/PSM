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
        evaluation = request.env["hr.applicant.interview.evaluation"].sudo().browse(evaluation_id)
        if not evaluation.exists():
            raise exceptions.UserError(_("Khong tim thay phieu danh gia Interview."))

        applicant = evaluation.applicant_id.with_env(request.env)
        applicant._check_backend_interview_access(user=request.env.user)
        return evaluation

    def _prepare_internal_values(self, evaluation, success_message=False, error_message=False):
        if not evaluation or not evaluation.exists():
            return {
                "evaluation": evaluation,
                "sections": request.env["hr.applicant.interview.evaluation.section"],
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

                if display_type in ("section", "subheader"):
                    current_subheader = raw_label
                    rows.append({
                        "display_type": display_type,
                        "label": raw_label,
                        "question_text": "",
                        "skillset_group": False,
                        "skillset_show_left": False,
                        "skillset_left": "",
                        "skillset_right": "",
                        "skillset_rowspan": 0,
                        "line_id": line.id if include_answer else False,
                        "selected_score": line.selected_score if include_answer else False,
                        "line_comment": line.line_comment if include_answer else "",
                    })
                    continue

                is_skillset_context = "skillset" in (current_subheader or "").lower()
                has_split = " - " in raw_label
                skillset_group = bool(is_skillset_context and has_split)
                skillset_left = ""
                skillset_right = raw_label

                if skillset_group:
                    split_parts = raw_label.split(" - ", 1)
                    skillset_left = (split_parts[0] or "").strip()
                    skillset_right = (split_parts[1] or "").strip()

                rows.append({
                    "display_type": "question",
                    "label": "",
                    "question_text": raw_label,
                    "skillset_group": skillset_group,
                    "skillset_show_left": False,
                    "skillset_left": skillset_left,
                    "skillset_right": skillset_right,
                    "skillset_rowspan": 0,
                    "line_id": line.id if include_answer else False,
                    "selected_score": line.selected_score if include_answer else False,
                    "line_comment": line.line_comment if include_answer else "",
                })

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
            return request.render('M02_P0204_00.backend_interview_internal_page', values)

        except Exception as error:
            values = self._prepare_internal_values(
                request.env['hr.applicant.interview.evaluation'].browse(),
                error_message=self._friendly_error_message(error),
            )
            return request.render('M02_P0204_00.backend_interview_internal_page', values)

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
            eval_fallback = request.env['hr.applicant.interview.evaluation'].sudo().browse(evaluation_id)
            values = self._prepare_internal_values(
                eval_fallback,
                error_message=self._friendly_error_message(error),
            )
            return request.render('M02_P0204_00.backend_interview_internal_page', values)

    @http.route('/recruitment/interview/template-preview/<int:template_id>', type='http', auth='user', website=True)
    def backend_interview_template_preview(self, template_id, **kwargs):
        user = request.env.user
        if not user.has_group('hr_recruitment.group_hr_recruitment_user'):
            raise exceptions.AccessError(_("Ban khong co quyen xem preview Interview."))

        template = request.env['recruitment.interview.template'].sudo().browse(template_id)
        if not template.exists():
            raise exceptions.UserError(_("Khong tim thay mau Interview de preview."))

        template.with_user(user).check_access_rights('read')
        template.with_user(user).check_access_rule('read')

        preview_sections = self._prepare_section_rows(
            template.section_ids.filtered('is_active'),
            'is_active',
            include_answer=False,
        )
        values = self._prepare_preview_values(
            preview_title=f'{template.name} (Preview)',
            preview_intro_html=template.intro_html,
            preview_sections=preview_sections,
            back_url=f'/web#id={template.id}&model=recruitment.interview.template&view_type=form',
        )
        return request.render('M02_P0204_00.backend_interview_preview_page', values)

    @http.route('/recruitment/interview/job-preview/<int:job_id>', type='http', auth='user', website=True)
    def backend_interview_job_preview(self, job_id, **kwargs):
        user = request.env.user
        if not user.has_group('hr_recruitment.group_hr_recruitment_user'):
            raise exceptions.AccessError(_("Ban khong co quyen xem preview Interview."))

        job = request.env['hr.job'].sudo().browse(job_id)
        if not job.exists():
            raise exceptions.UserError(_("Khong tim thay Job Position de preview Interview."))

        job.with_user(user).check_access_rights('read')
        job.with_user(user).check_access_rule('read')

        if not (job.recruitment_type == 'store' and job.position_level == 'management'):
            raise exceptions.UserError(_("Chi ho tro preview Interview cho job Store + Management."))

        preview_sections = self._prepare_section_rows(
            job.interview_config_section_ids.filtered('is_active'),
            'is_active',
            include_answer=False,
        )
        values = self._prepare_preview_values(
            preview_title=f'{job.name} - Interview Preview',
            preview_intro_html=False,
            preview_sections=preview_sections,
            back_url=f'/web#id={job.id}&model=hr.job&view_type=form',
        )
        return request.render('M02_P0204_00.backend_interview_preview_page', values)
