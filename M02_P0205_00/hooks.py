# -*- coding: utf-8 -*-
import logging

from .models.res_company import GROUP_XMLID_MAPPINGS

_logger = logging.getLogger(__name__)


def _migrate_legacy_groups(env):
    """Map users from legacy 0205 flow groups into standardized group codes."""
    for legacy_xmlid, standardized_xmlid in GROUP_XMLID_MAPPINGS.items():
        legacy_group = env.ref(legacy_xmlid, raise_if_not_found=False)
        standardized_group = env.ref(standardized_xmlid, raise_if_not_found=False)
        if not legacy_group or not standardized_group:
            continue
        missing_users = legacy_group.users - standardized_group.users
        if missing_users:
            standardized_group.write({'users': [(4, user.id) for user in missing_users]})
            _logger.info(
                "0205 security migration: mapped %s users from %s to %s.",
                len(missing_users),
                legacy_xmlid,
                standardized_xmlid,
            )


def post_init_hook(env):
    """Cleanup legacy interview evaluations and map legacy groups on install."""
    _migrate_legacy_groups(env)
    Evaluation = env['x_psm_applicant_evaluation'].sudo()
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
