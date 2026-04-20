# -*- coding: utf-8 -*-
from odoo import models, fields


class SurveySurvey(models.Model):
    _inherit = "survey.survey"

    x_psm_0205_is_pre_interview = fields.Boolean(
        string="Khảo sát trước phỏng vấn",
        default=False,
        help="Đánh dấu survey dùng cho vòng đánh giá trước phỏng vấn (pre-interview).",
    )


class SurveyQuestionAnswer(models.Model):
    _inherit = 'survey.question.answer'

    x_psm_0205_is_must_have = fields.Boolean(
        string='Tiêu chí bắt buộc',
        default=False,
        help='Tiêu chí bắt buộc để tính điểm đạt, ví dụ ngưỡng 80%.',
    )
    x_psm_0205_is_nice_to_have = fields.Boolean(
        string='Tiêu chí cộng điểm',
        default=False,
        help='Tiêu chí cộng điểm, không tính vào điểm đạt nhưng dùng để ưu tiên.',
    )


# NOTE: SurveyUserInput._mark_done() has been consolidated into M02_P0204.
# The dispatcher in 0204 calls applicant._handle_office_pre_interview_survey_done()
# when x_psm_0205_recruitment_type == 'office'. That method is defined in 0205/models/hr_applicant.py.
