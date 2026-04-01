# -*- coding: utf-8 -*-
"""
Model: Survey Extension
Mô tả: Thêm field is_pre_interview để đánh dấu survey dùng trước phỏng vấn
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
