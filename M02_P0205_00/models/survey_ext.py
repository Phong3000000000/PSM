# -*- coding: utf-8 -*-
from odoo import models, fields


class SurveySurvey(models.Model):
    _inherit = "survey.survey"

    is_pre_interview = fields.Boolean(
        string="Pre-interview Survey",
        default=False,
        help="Đánh dấu survey dùng cho vòng đánh giá trước phỏng vấn (pre-interview).",
    )


class SurveyQuestionAnswer(models.Model):
    _inherit = 'survey.question.answer'

    is_must_have = fields.Boolean(string='Must Have', default=False, help='Tiêu chí bắt buộc để tính điểm đạt (ví dụ: 80%)')
    is_nice_to_have = fields.Boolean(string='Nice to Have', default=False, help='Tiêu chí điểm cộng, không tính vào điểm đạt nhưng dùng để ưu tiên')


# NOTE: SurveyUserInput._mark_done() has been consolidated into M02_P0204_00.
# The dispatcher in 0204 calls applicant._handle_office_pre_interview_survey_done()
# when recruitment_type == 'office'. That method is defined in 0205/models/hr_applicant.py.
