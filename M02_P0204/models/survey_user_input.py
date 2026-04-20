# -*- coding: utf-8 -*-
"""
Kế thừa survey.user_input để tự động đánh giá ứng viên
khi họ hoàn thành survey (_mark_done).

Luồng:
  - Không đạt (scoring_success=False)  → Reject
  - Đạt (scoring_success=True)
      - Có câu is_mandatory_correct=True mà trả lời SAI → Under Review (24h)
    - Tất cả câu phải đúng → Interview flow trực tiếp theo pipeline hiện tại
"""

from odoo import models, api, fields
import logging

_logger = logging.getLogger(__name__)


class SurveyUserInput(models.Model):
    _inherit = "survey.user_input"

    def _mark_done(self):
        """Override _mark_done để tự động đánh giá ứng viên sau khi hoàn thành survey."""
        result = super()._mark_done()
        try:
            self.sudo()._dispatch_recruitment_survey_done()
        except Exception as e:
            _logger.error(
                "[SURVEY_AUTO] Lỗi khi tự động đánh giá ứng viên cho user_input ids=%s: %s",
                self.ids, str(e),
            )
        return result

    def _split_mandatory_question_failures(self, user_input):
        """
        Tách lỗi câu 'phải đúng' thành 2 nhóm:
        - review_failed: sai nhưng chỉ đưa Under Review
        - reject_failed: sai và phải Reject ngay
        """
        mandatory_questions = user_input.survey_id.question_ids.filtered(
            lambda q: q.x_psm_0204_is_mandatory_correct and q.is_scored_question
        )
        if not mandatory_questions:
            return [], []

        review_failed = []
        reject_failed = []

        for question in mandatory_questions:
            q_lines = user_input.user_input_line_ids.filtered(
                lambda l, q=question: l.question_id == q and not l.skipped
            )
            is_wrong = (not q_lines) or any(not l.answer_is_correct for l in q_lines)
            if not is_wrong:
                continue

            question_label = question.title or question.question
            if getattr(question, "x_psm_0204_is_reject_when_wrong", False):
                reject_failed.append(question_label)
            else:
                review_failed.append(question_label)

        return review_failed, reject_failed

    def _check_mandatory_questions_failed(self, user_input):
        """
        Kiểm tra xem ứng viên có sai câu nào bị đánh dấu is_mandatory_correct không.
        Trả về: (has_fail: bool, failed_questions: list[str])
        """
        review_failed, reject_failed = self._split_mandatory_question_failures(user_input)
        failed = review_failed + reject_failed
        return bool(failed), failed

    def _dispatch_recruitment_survey_done(self):
        """Dispatcher: route survey completion to office or store handler."""
        Applicant = self.env["hr.applicant"].sudo()
        for user_input in self:
            applicant = Applicant.search(
                [("survey_user_input_id", "=", user_input.id)], limit=1
            )
            if not applicant:
                _logger.info("[SURVEY_AUTO] Không tìm thấy applicant cho user_input id=%s", user_input.id)
                continue
            if applicant.recruitment_type == 'office' and hasattr(applicant, '_handle_office_pre_interview_survey_done'):
                applicant._handle_office_pre_interview_survey_done(user_input)
            else:
                self._handle_store_pre_interview_survey_done(applicant, user_input)

    def _handle_store_pre_interview_survey_done(self, applicant, user_input):
        """
        Store-specific survey auto-evaluation.
        Formerly _auto_evaluate_applicants(), now receives a single applicant+user_input.
        """
        from werkzeug.urls import url_encode

        # Tạo link result cho admin/HR xem lại
        survey = user_input.survey_id.sudo()
        if not survey.access_token:
            survey.write({'access_token': survey._get_default_access_token()})
        survey_print_url = survey.get_print_url()
        query_string = url_encode({'answer_token': user_input.access_token, 'review': True})
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url') or ''
        base_url = base_url.rstrip('/')
        review_url = f"{survey_print_url}?{query_string}"
        if base_url:
            review_url = f"{base_url}{review_url}"

        applicant.write({'survey_result_url': review_url})

        Stage = self.env["hr.recruitment.stage"].sudo()
        stage_type = applicant._get_pipeline_stage_type()
        if not stage_type:
            _logger.warning(
                "[SURVEY_AUTO] Missing stage family for applicant id=%s (recruitment_type=%s, position_level=%s)",
                applicant.id,
                applicant.recruitment_type,
                applicant.position_level,
            )
            return

        # Chỉ kiểm tra câu bắt buộc (is_mandatory_correct), bỏ qua điểm số tổng.
        # Tách rõ sai cần Under Review và sai phải Reject ngay.
        failed_review_questions, failed_reject_questions = self._split_mandatory_question_failures(user_input)

        if failed_reject_questions:
            target_name = "Reject"
            domain = [("name", "=", target_name)]
            domain.append(("recruitment_type", "=", stage_type))
            target_stage = Stage.search(domain, limit=1)

            reject_reason = "Tu dong loai do sai cau 'Loai khi sai': %s" % ", ".join(failed_reject_questions)
            applicant_vals = {
                'survey_under_review_date': False,
                'x_psm_0205_document_approval_status': 'refused',
                'reject_reason': reject_reason,
            }
            if target_stage:
                applicant_vals['stage_id'] = target_stage.id
            applicant.write(applicant_vals)

            _logger.info(
                "[SURVEY_AUTO] %s -> 'Reject' (reject_when_wrong: %s)",
                applicant.partner_name,
                failed_reject_questions,
            )
            return

        if failed_review_questions:
            # Sai câu bắt buộc → Under Review
            target_name = "Under Review"
            domain = [("name", "=", target_name)]
            domain.append(("recruitment_type", "=", stage_type))
            target_stage = Stage.search(domain, limit=1)

            if target_stage:
                applicant.stage_id = target_stage
                applicant.survey_under_review_date = fields.Datetime.now()
                q_list = ", ".join(f"<i>{q}</i>" for q in failed_review_questions)
                _logger.info(
                    "[SURVEY_AUTO] %s → 'Under Review' (mandatory fail: %s)",
                    applicant.partner_name,
                    failed_review_questions,
                )
            else:
                _logger.warning(
                    "[SURVEY_AUTO] Không tìm thấy stage 'Under Review' cho pipeline '%s'",
                    stage_type,
                )
            return

        # Không sai câu bắt buộc → tiếp tục pipeline bình thường
        if applicant.recruitment_type == 'store' and applicant.position_level == 'staff':
            target_name = "Interview & OJE"
            domain = [("name", "=", "Interview & OJE")]
        elif applicant.recruitment_type == 'store' and applicant.position_level == 'management':
            target_name = "Interview"
            domain = [("name", "=", "Interview")]
        else:
            target_name = "Screening"
            domain = [("name", "=", "Screening")]

        domain.append(("recruitment_type", "=", stage_type))

        target_stage = Stage.search(domain, limit=1)

        if target_stage:
            applicant.stage_id = target_stage
            _logger.info(
                "[SURVEY_AUTO] %s → stage '%s' (passed mandatory check)",
                applicant.partner_name, target_stage.name,
            )

            # Auto-book lịch PV ngay sau khi pass survey nếu đã vào stage Interview
            if applicant.recruitment_type == 'store' and 'interview' in (target_stage.name or '').lower():
                try:
                    booking_result = applicant.action_auto_book_interview_from_survey()
                    _logger.info(
                        "[SURVEY_AUTO] Auto-book result applicant id=%s: %s",
                        applicant.id, booking_result,
                    )
                except Exception as booking_err:
                    _logger.error(
                        "[SURVEY_AUTO] Auto-book failed applicant id=%s: %s",
                        applicant.id, booking_err,
                    )
        else:
            _logger.warning(
                "[SURVEY_AUTO] Không tìm thấy stage '%s' cho pipeline '%s'",
                target_name, stage_type,
            )


class SurveyUserInputLine(models.Model):
    _inherit = 'survey.user_input.line'

    x_psm_0204_is_mandatory_correct = fields.Boolean(
        oldname='is_mandatory_correct',
        related='question_id.x_psm_0204_is_mandatory_correct',
        string="Phải đúng",
        help="Đánh dấu câu hỏi này có bắt buộc phải làm đúng hay không"
    )

    x_psm_0204_is_reject_when_wrong = fields.Boolean(
        oldname='is_reject_when_wrong',
        related='question_id.x_psm_0204_is_reject_when_wrong',
        string="Loại khi sai",
        help="Nếu sai câu này thì ứng viên sẽ bị Reject ngay.",
    )
