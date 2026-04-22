# -*- coding: utf-8 -*-
from odoo import _, exceptions, fields, http
from odoo.http import request


class OfficeEvaluationController(http.Controller):
    """Custom office interview evaluation page using the 0204 interaction pattern."""

    def _get_applicant_backend_url(self, evaluation):
        applicant = evaluation.applicant_id
        return f"/web#id={applicant.id}&model=hr.applicant&view_type=form"

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
        evaluation = request.env["x_psm_applicant_evaluation"].sudo().browse(evaluation_id)
        if not evaluation.exists():
            raise exceptions.UserError(_("Khong tim thay phieu danh gia Interview."))
        if request.env.user.share:
            raise exceptions.AccessError(_("Ban khong co quyen truy cap trang nay."))
        return evaluation

    def _build_row(self, line):
        is_question = line.line_type == "score" and line.is_scored
        selected_score = False
        if line.score_value and str(line.score_value).isdigit():
            selected_score = int(line.score_value)
        return {
            "display_type": "question" if is_question else "subheader",
            "label": line.item_label if not is_question else "",
            "question_text": line.item_label if is_question else "",
            "skillset_group": False,
            "skillset_show_left": False,
            "skillset_left": "",
            "skillset_right": line.item_label if is_question else "",
            "skillset_rowspan": 0,
            "line_id": line.id,
            "selected_score": selected_score,
            "line_comment": line.note or "",
        }

    def _prepare_sections(self, evaluation):
        sections = []
        ordered_lines = evaluation.evaluation_item_ids.sorted("sequence")
        section_name_map = dict(evaluation.EVALUATION_SECTION_SELECTION or [])
        used_codes = set()

        for section_code, section_name in evaluation.EVALUATION_SECTION_SELECTION:
            section_lines = ordered_lines.filtered(lambda line, code=section_code: line.section_code == code)
            if not section_lines:
                continue
            used_codes.add(section_code)
            sections.append(
                {
                    "name": section_name,
                    "rows": [self._build_row(line) for line in section_lines],
                }
            )

        for section_code in ordered_lines.mapped("section_code"):
            if section_code in used_codes:
                continue
            section_lines = ordered_lines.filtered(lambda line, code=section_code: line.section_code == code)
            if not section_lines:
                continue
            sections.append(
                {
                    "name": section_name_map.get(section_code, section_code or _("Section")),
                    "rows": [self._build_row(line) for line in section_lines],
                }
            )

        return sections

    def _prepare_summary(self, evaluation):
        question_lines = evaluation.evaluation_item_ids.filtered(
            lambda line: line.line_type == "score" and line.is_scored
        )
        counts = {score: 0 for score in range(1, 6)}
        complete = bool(question_lines)

        for line in question_lines:
            score_value = int(line.score_value) if line.score_value and str(line.score_value).isdigit() else 0
            if score_value not in counts:
                complete = False
                continue
            counts[score_value] += 1

        rated_line_count = sum(counts.values())
        weighted_total = sum(score * count for score, count in counts.items())
        final_score = (weighted_total / rated_line_count) if rated_line_count else 0.0
        result = "pass" if rated_line_count and final_score >= 3.0 else "reject"

        return {
            "score_1_count": counts[1],
            "score_2_count": counts[2],
            "score_3_count": counts[3],
            "score_4_count": counts[4],
            "score_5_count": counts[5],
            "weighted_total": weighted_total,
            "rated_line_count": rated_line_count,
            "final_score": final_score,
            "result": result,
            "is_complete": complete and rated_line_count == len(question_lines),
        }

    def _prepare_values(self, evaluation, success_message=False, error_message=False):
        if not evaluation or not evaluation.exists():
            return {
                "evaluation": evaluation,
                "prepared_sections": [],
                "summary": {},
                "is_readonly": True,
                "success_message": success_message,
                "error_message": error_message,
                "preview_mode": False,
                "interview_date": "",
            }

        summary = self._prepare_summary(evaluation)
        is_owner = evaluation.interviewer_id == request.env.user
        is_readonly = evaluation.state == "done" or not is_owner

        interview_dt = evaluation.interview_date
        if interview_dt:
            interview_dt = fields.Date.to_date(interview_dt)
        interview_date = interview_dt.strftime("%Y-%m-%d") if interview_dt else ""

        return {
            "evaluation": evaluation,
            "prepared_sections": self._prepare_sections(evaluation),
            "summary": summary,
            "is_readonly": is_readonly,
            "success_message": success_message,
            "error_message": error_message,
            "preview_mode": False,
            "interview_date": interview_date,
            "back_url": self._get_applicant_backend_url(evaluation),
        }

    def _write_answers(self, evaluation, post):
        evaluation.sudo().write(
            {
                "onboard_time": self._clean_text(post.get("onboard_time")),
                "final_comment": self._clean_text(post.get("overall_note")),
                "state": "in_progress",
            }
        )

        updates = []
        missing_required = False
        for line in evaluation.evaluation_item_ids.filtered(lambda rec: rec.line_type == "score" and rec.is_scored):
            score = self._parse_int(post.get(f"line_{line.id}_score"), min_value=1, max_value=5)
            note = self._clean_text(post.get(f"line_{line.id}_comment"))
            if not score:
                missing_required = True
            updates.append((line, score, note))

        if missing_required:
            raise exceptions.UserError(_("Vui long chon diem 1..5 cho tat ca dong Question."))

        for line, score, note in updates:
            line.sudo().write(
                {
                    "score_value": str(score),
                    "note": note,
                }
            )

    @http.route(
        "/recruitment/office-interview/evaluation/<int:evaluation_id>",
        type="http",
        auth="user",
        website=True,
    )
    def office_evaluation_form(self, evaluation_id, success=None, **kwargs):
        try:
            evaluation = self._get_evaluation_with_access(evaluation_id)
            values = self._prepare_values(
                evaluation,
                success_message=_("Luu danh gia Interview thanh cong.") if success else False,
            )
            return request.render("M02_P0205.office_evaluation_page", values)
        except Exception as error:
            values = self._prepare_values(
                request.env["x_psm_applicant_evaluation"].browse(),
                error_message=self._friendly_error_message(error),
            )
            return request.render("M02_P0205.office_evaluation_page", values)

    @http.route(
        "/recruitment/office-interview/evaluation/<int:evaluation_id>/submit",
        type="http",
        auth="user",
        methods=["POST"],
        website=True,
    )
    def office_evaluation_submit(self, evaluation_id, **post):
        try:
            evaluation = self._get_evaluation_with_access(evaluation_id)
            if evaluation.state == "done":
                raise exceptions.UserError(_("Phieu Interview da nop va bi khoa chinh sua."))
            if evaluation.interviewer_id != request.env.user:
                raise exceptions.AccessError(_("Chi nguoi phong van moi duoc phep nop danh gia."))

            self._write_answers(evaluation, post)
            evaluation.sudo().action_submit()
            return request.redirect(self._get_applicant_backend_url(evaluation))
        except Exception as error:
            evaluation = request.env["x_psm_applicant_evaluation"].sudo().browse(evaluation_id)
            values = self._prepare_values(
                evaluation,
                error_message=self._friendly_error_message(error),
            )
            return request.render("M02_P0205.office_evaluation_page", values)
