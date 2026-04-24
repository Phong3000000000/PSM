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

    def _extract_submitted_answers(self, post):
        answers = {}
        for key, value in post.items():
            if key.startswith("line_") and key.endswith("_score"):
                try:
                    line_id = int(key.split("_")[1])
                    answers.setdefault(line_id, {})["selected_score"] = int(value) if value else False
                except ValueError:
                    pass
            elif key.startswith("line_") and key.endswith("_comment"):
                try:
                    line_id = int(key.split("_")[1])
                    answers.setdefault(line_id, {})["line_comment"] = self._clean_text(value)
                except ValueError:
                    pass
        return answers

    def _get_missing_required_line_ids(self, evaluation, submitted_answers):
        missing = []
        for line in evaluation.evaluation_item_ids:
            if getattr(line, 'display_type', 'question') != "question" or not line.is_scored:
                continue
            selected = submitted_answers.get(line.id, {}).get("selected_score") or line.score_value
            if not selected:
                missing.append(line.id)
        return missing

    # ── Row building (mirrors BackendInterviewController pattern) ──

    def _split_skillset_label(self, raw_label):
        if " - " not in raw_label:
            return False, raw_label
        left, right = raw_label.split(" - ", 1)
        left = (left or "").strip()
        right = (right or "").strip()
        if not left or not right:
            return False, raw_label
        return left, right

    def _build_row(self, line):
        """Build a template-ready row dict from an evaluation line record."""
        display_type = getattr(line, 'display_type', 'question') or 'question'
        group_kind = (getattr(line, 'x_psm_interview_group_kind', '') or '').strip()
        group_label = (getattr(line, 'x_psm_interview_group_label', '') or '').strip()

        is_question = display_type == 'question' and line.line_type == 'score' and line.is_scored
        is_subheader = display_type == 'subheader' or group_kind == 'subheader'

        selected_score = False
        if line.score_value and str(line.score_value).isdigit():
            selected_score = int(line.score_value)

        raw_label = line.item_label or ""

        if is_subheader:
            return {
                "display_type": "subheader",
                "label": raw_label,
                "question_text": "",
                "skillset_group": False,
                "skillset_show_left": False,
                "skillset_left": "",
                "skillset_right": "",
                "skillset_rowspan": 0,
                "line_id": line.id,
                "selected_score": selected_score,
                "line_comment": line.note or "",
                "x_psm_interview_group_kind": "subheader",
                "x_psm_interview_group_label": "",
            }

        # Question row — detect skillset grouping
        skillset_group = False
        skillset_left = ""
        skillset_right = raw_label

        if group_kind == "skillset_child" and group_label:
            skillset_group = True
            skillset_left = group_label
            split_left, split_right = self._split_skillset_label(raw_label)
            if split_left and split_right and split_left.lower() == group_label.lower():
                skillset_right = split_right
        elif group_kind == "skillset_child":
            split_left, split_right = self._split_skillset_label(raw_label)
            if split_left and split_right:
                skillset_group = True
                skillset_left = split_left
                skillset_right = split_right

        return {
            "display_type": "question" if is_question else "subheader",
            "label": "" if is_question else raw_label,
            "question_text": raw_label if is_question else "",
            "skillset_group": skillset_group,
            "skillset_show_left": False,
            "skillset_left": skillset_left,
            "skillset_right": skillset_right if skillset_group else (raw_label if is_question else ""),
            "skillset_rowspan": 0,
            "line_id": line.id,
            "selected_score": selected_score,
            "line_comment": line.note or "",
            "x_psm_interview_group_kind": group_kind or "question",
            "x_psm_interview_group_label": group_label if skillset_group else "",
        }

    def _aggregate_skillset_rowspans(self, rows):
        """Post-process rows to compute skillset rowspans (same logic as 0204)."""
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
        return rows

    def _prepare_sections(self, evaluation, submitted_answers=None, missing_line_ids=None):
        """Build sections grouped by section_name/section_code with skillset aggregation."""
        sections = []
        ordered_lines = evaluation.evaluation_item_ids.sorted("sequence")

        # Group lines by section key in order of first appearance.
        # Prefer section_name (dynamic from survey) over section_code (legacy hardcoded).
        section_order = []
        section_lines_map = {}
        section_display_names = {}
        section_name_map = dict(evaluation.EVALUATION_SECTION_SELECTION or [])

        for line in ordered_lines:
            # Use section_name when available (survey-loaded), else section_code
            key = line.section_name or line.section_code or 'default'
            if key not in section_lines_map:
                section_order.append(key)
                section_lines_map[key] = []
                # Resolve display name
                if line.section_name:
                    section_display_names[key] = line.section_name
                else:
                    section_display_names[key] = section_name_map.get(line.section_code) or line.section_code or 'Section'
            section_lines_map[key].append(line)

        for section_key in section_order:
            section_lines = section_lines_map[section_key]
            rows = []
            for line in section_lines:
                row = self._build_row(line)
                if submitted_answers and line.id in submitted_answers:
                    row["selected_score"] = submitted_answers[line.id].get("selected_score") or False
                    row["line_comment"] = submitted_answers[line.id].get("line_comment", row["line_comment"])
                
                if missing_line_ids and line.id in missing_line_ids:
                    row["is_missing_required"] = True
                else:
                    row["is_missing_required"] = False
                rows.append(row)
            
            rows = self._aggregate_skillset_rowspans(rows)

            sections.append({
                "name": section_display_names.get(section_key, section_key),
                "rows": rows,
            })

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

    def _prepare_values(self, evaluation, success_message=False, error_message=False, submitted_answers=None, missing_line_ids=None, submitted_post=None):
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
            "prepared_sections": self._prepare_sections(evaluation, submitted_answers, missing_line_ids),
            "summary": summary,
            "is_readonly": is_readonly,
            "success_message": success_message,
            "error_message": error_message,
            "preview_mode": False,
            "interview_date": interview_date,
            "back_url": self._get_applicant_backend_url(evaluation),
            "submitted_post": submitted_post or {},
        }

    def _write_answers(self, evaluation, post):
        updates = []
        missing_required = False
        for line in evaluation.evaluation_item_ids.filtered(lambda rec: rec.line_type == "score" and rec.is_scored):
            score = self._parse_int(post.get(f"line_{line.id}_score"), min_value=1, max_value=5)
            note = self._clean_text(post.get(f"line_{line.id}_comment"))
            if not score:
                missing_required = True
            updates.append((line, score, note))

        if missing_required:
            raise exceptions.UserError(_("Vui lòng chọn điểm (1-5) cho tất cả các tiêu chí đánh giá."))

        evaluation.sudo().write(
            {
                "onboard_time": self._clean_text(post.get("onboard_time")),
                "final_comment": self._clean_text(post.get("overall_note")),
                "state": "in_progress",
            }
        )

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
            if evaluation.exists():
                submitted_answers = self._extract_submitted_answers(post)
                missing_line_ids = self._get_missing_required_line_ids(evaluation, submitted_answers)
                values = self._prepare_values(
                    evaluation,
                    error_message=self._friendly_error_message(error),
                    submitted_answers=submitted_answers,
                    missing_line_ids=missing_line_ids,
                    submitted_post=post,
                )
            else:
                values = self._prepare_values(
                    evaluation,
                    error_message=self._friendly_error_message(error),
                )
            return request.render("M02_P0205.office_evaluation_page", values)
