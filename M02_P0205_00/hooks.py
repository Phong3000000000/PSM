# -*- coding: utf-8 -*-
import logging

_logger = logging.getLogger(__name__)


def post_init_hook(env):
    """Cleanup legacy interview evaluations that still use 'consider'."""
    Evaluation = env['hr.applicant.evaluation'].sudo()
    legacy_evaluations = Evaluation.search([('recommendation', '=', 'consider')])
    if not legacy_evaluations:
        _logger.info("0205 migration: no legacy 'consider' evaluations found.")
        return

    applicants = legacy_evaluations.mapped('applicant_id')
    rounds_by_applicant = {}
    for evaluation in legacy_evaluations:
        if not evaluation.applicant_id:
            continue
        rounds_by_applicant.setdefault(evaluation.applicant_id.id, set()).add(evaluation.interview_round)

    for applicant in applicants:
        applicant_evals = legacy_evaluations.filtered(lambda rec: rec.applicant_id == applicant)
        if not applicant_evals:
            continue
        round_list = sorted({int(rec.interview_round) for rec in applicant_evals if rec.interview_round and rec.interview_round.isdigit()})
        interviewer_list = ', '.join(applicant_evals.mapped('interviewer_id.display_name'))
        applicant.message_post(
            body=(
                "Dữ liệu đánh giá cũ có trạng thái 'consider' đã được dọn khi cập nhật module 0205. "
                "Các đánh giá này đã bị xóa để hồ sơ quay về trạng thái chờ đánh giá lại. "
                "Vòng bị ảnh hưởng: %s. Người đánh giá liên quan: %s."
            ) % (
                ', '.join(str(round_no) for round_no in round_list) or 'N/A',
                interviewer_list or 'N/A',
            )
        )

    count = len(legacy_evaluations)
    legacy_evaluations.unlink()

    for applicant in applicants:
        for interview_round in rounds_by_applicant.get(applicant.id, set()):
            applicant._update_interview_round_outcome(interview_round)

    _logger.info(
        "0205 migration: removed %s legacy 'consider' evaluations across %s applicants.",
        count,
        len(applicants),
    )

    legacy_line_evaluations = Evaluation.search([('evaluation_item_ids', '=', False)])
    if legacy_line_evaluations:
        _logger.info(
            "0205 migration: backfilling line-based evaluation structure for %s legacy records.",
            len(legacy_line_evaluations),
        )
        legacy_line_evaluations._migrate_legacy_scores_to_lines()
