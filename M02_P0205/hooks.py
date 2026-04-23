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


def _needs_custom_survey_rebind(job, survey, usage):
    if not survey:
        return True
    if survey.x_psm_0204_is_runtime_isolated_copy:
        return True
    if survey.x_psm_survey_usage != usage:
        return True
    if survey.x_psm_0204_owner_job_id and survey.x_psm_0204_owner_job_id != job:
        return True
    if not survey.x_psm_0204_owner_job_id:
        return True
    return False


def _backfill_office_job_custom_surveys(env):
    jobs = env['hr.job'].sudo().search([('recruitment_type', '=', 'office')])
    if not jobs:
        return

    rebound_pre = 0
    rebound_interview = 0
    missing_pre = []
    missing_interview = []

    for job in jobs:
        if not job.department_id:
            continue

        pre_source = job._x_psm_find_default_survey('pre_interview')
        if pre_source:
            if _needs_custom_survey_rebind(job, job.survey_id.sudo(), 'pre_interview'):
                job._x_psm_ensure_custom_survey_binding('pre_interview', source_survey=pre_source)
                rebound_pre += 1
        else:
            missing_pre.append(job.display_name)

        if not job._is_interview_template_supported():
            continue

        interview_source = job._x_psm_find_default_survey('interview')
        if interview_source:
            if _needs_custom_survey_rebind(job, job.x_psm_interview_survey_id.sudo(), 'interview'):
                job._x_psm_ensure_custom_survey_binding('interview', source_survey=interview_source)
                rebound_interview += 1
        else:
            missing_interview.append(job.display_name)

    _logger.info(
        "0205 survey backfill: rebound %s office application surveys and %s office interview surveys.",
        rebound_pre,
        rebound_interview,
    )
    if missing_pre:
        _logger.warning(
            "0205 survey backfill: missing application master survey for office jobs: %s",
            ", ".join(missing_pre),
        )
    if missing_interview:
        _logger.warning(
            "0205 survey backfill: missing interview master for office jobs: %s",
            ", ".join(missing_interview),
        )


def post_init_hook(env):
    """Cleanup legacy interview evaluations and map legacy groups on install."""
    _migrate_legacy_groups(env)
    _backfill_office_job_custom_surveys(env)
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
