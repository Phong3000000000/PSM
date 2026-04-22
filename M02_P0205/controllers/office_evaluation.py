# -*- coding: utf-8 -*-
from odoo import http, _, exceptions
from odoo.http import request


class OfficeEvaluationController(http.Controller):
    """Page-based evaluation controller for office interview evaluations.

    Follows the same UX pattern as M02_P0204's backend_interview controller:
    - GET  renders the evaluation form (editable or read-only based on state)
    - POST submits scores and transitions the eval to done
    """

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
        return _("Hệ thống chưa thể xử lý yêu cầu lúc này. Vui lòng thử lại.")

    def _get_evaluation_with_access(self, evaluation_id):
        """Load evaluation, verify user has access via the applicant."""
        evaluation = request.env['x_psm_applicant_evaluation'].sudo().browse(evaluation_id)
        if not evaluation.exists():
            raise exceptions.UserError(_("Không tìm thấy phiếu đánh giá."))
        # Access check: user must be internal
        if request.env.user.share:
            raise exceptions.AccessError(_("Bạn không có quyền truy cập trang này."))
        return evaluation

    def _prepare_values(self, evaluation, success_message=False, error_message=False):
        """Build template rendering values."""
        if not evaluation or not evaluation.exists():
            return {
                'evaluation': evaluation,
                'sections': [],
                'is_readonly': True,
                'success_message': success_message,
                'error_message': error_message,
            }

        # Group evaluation_item_ids by section_code for structured display
        sections = []
        section_map = {}
        for line in evaluation.evaluation_item_ids.sorted('sequence'):
            sec_code = line.section_code or 'other'
            if sec_code not in section_map:
                section_map[sec_code] = {
                    'code': sec_code,
                    'name': dict(evaluation.EVALUATION_SECTION_SELECTION).get(sec_code, sec_code),
                    'lines': [],
                }
                sections.append(section_map[sec_code])
            section_map[sec_code]['lines'].append(line)

        # Determine readonly: done state or user is not the interviewer
        is_done = evaluation.recommendation in ('pass', 'fail') and evaluation.scored_line_count > 0
        is_owner = evaluation.interviewer_id == request.env.user
        is_readonly = is_done or not is_owner

        # Applicant info for display
        applicant = evaluation.applicant_id
        round_label = dict(evaluation._fields['interview_round'].selection).get(
            evaluation.interview_round, f'Vòng {evaluation.interview_round}'
        )

        # Interview date for this round
        date_field = f'x_psm_0205_interview_date_{evaluation.interview_round}'
        interview_date = getattr(applicant, date_field, False) if applicant else False

        return {
            'evaluation': evaluation,
            'applicant': applicant,
            'sections': sections,
            'is_readonly': is_readonly,
            'is_done': is_done,
            'round_label': round_label,
            'interview_date': interview_date,
            'success_message': success_message,
            'error_message': error_message,
        }

    def _write_answers(self, evaluation, post):
        """Save scores and text from the form POST data."""
        updates = {}
        final_comment = self._clean_text(post.get('final_comment'))
        if final_comment is not False:
            updates['final_comment'] = final_comment
        onboard_time = self._clean_text(post.get('onboard_time'))
        if onboard_time is not False:
            updates['onboard_time'] = onboard_time

        if updates:
            evaluation.sudo().write(updates)

        # Update each scored line
        for line in evaluation.evaluation_item_ids.filtered(
            lambda l: l.line_type == 'score' and l.is_scored
        ):
            score = self._parse_int(post.get(f'line_{line.id}_score'), min_value=1, max_value=5)
            note = self._clean_text(post.get(f'line_{line.id}_note'))
            line_vals = {}
            if score:
                line_vals['score_value'] = str(score)
            if note is not False:
                line_vals['note'] = note
            if line_vals:
                line.sudo().write(line_vals)

    @http.route(
        '/recruitment/office-interview/evaluation/<int:evaluation_id>',
        type='http', auth='user', website=True,
    )
    def office_evaluation_form(self, evaluation_id, success=None, **kwargs):
        """Render the office evaluation page."""
        try:
            evaluation = self._get_evaluation_with_access(evaluation_id)
            values = self._prepare_values(
                evaluation,
                success_message=_("Lưu đánh giá thành công.") if success else False,
            )
            return request.render('M02_P0205.office_evaluation_page', values)
        except Exception as error:
            values = self._prepare_values(
                request.env['x_psm_applicant_evaluation'].browse(),
                error_message=self._friendly_error_message(error),
            )
            return request.render('M02_P0205.office_evaluation_page', values)

    @http.route(
        '/recruitment/office-interview/evaluation/<int:evaluation_id>/submit',
        type='http', auth='user', methods=['POST'], website=True,
    )
    def office_evaluation_submit(self, evaluation_id, **post):
        """Handle form submission — save answers."""
        try:
            evaluation = self._get_evaluation_with_access(evaluation_id)

            is_done = evaluation.recommendation in ('pass', 'fail') and evaluation.scored_line_count > 0
            if is_done:
                raise exceptions.UserError(_("Phiếu đánh giá đã hoàn tất và không thể chỉnh sửa."))
            if evaluation.interviewer_id != request.env.user:
                raise exceptions.AccessError(_("Chỉ người phỏng vấn mới được phép nộp đánh giá."))

            self._write_answers(evaluation, post)
            return request.redirect(
                f'/recruitment/office-interview/evaluation/{evaluation.id}?success=1'
            )
        except Exception as error:
            eval_fallback = request.env['x_psm_applicant_evaluation'].sudo().browse(evaluation_id)
            values = self._prepare_values(
                eval_fallback,
                error_message=self._friendly_error_message(error),
            )
            return request.render('M02_P0205.office_evaluation_page', values)
