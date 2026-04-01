# -*- coding: utf-8 -*-
"""
Model: Survey Extension
Mô tả: Thêm field is_pre_interview cho survey,
       is_mandatory_correct cho câu hỏi (nếu sai → Under Review)
"""

from odoo import models, fields


class SurveySurvey(models.Model):
    """Extend Survey để thêm cờ is_pre_interview"""
    _inherit = 'survey.survey'

    is_pre_interview = fields.Boolean(
        string="Khảo Sát Trước PV",
        default=False,
        help="Đánh dấu survey dùng để gửi cho ứng viên trước phỏng vấn"
    )

    is_oje_evaluation = fields.Boolean(
        string="Phiếu Đánh Giá OJE",
        default=False,
        help="Đánh dấu là phiếu đánh giá OJE dành cho Quản lý điền",
    )


class SurveyQuestion(models.Model):
    """Extend câu hỏi để đánh dấu câu 'không thể sai'"""
    _inherit = 'survey.question'

    is_mandatory_correct = fields.Boolean(
        string="Không Thể Sai",
        default=False,
        help=(
            "Nếu câu này được đánh dấu và ứng viên trả lời SAI — "
            "hệ thống sẽ đánh dấu là không đạt tiêu chí bắt buộc "
            "(Store đưa vào Under Review, Office báo cảnh báo trên log)."
        )
    )
