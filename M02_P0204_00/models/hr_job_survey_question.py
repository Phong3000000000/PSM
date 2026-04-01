# -*- coding: utf-8 -*-
from odoo import models, fields, api

class HrJobSurveyQuestion(models.Model):
    _name = 'hr.job.survey.question'
    _description = 'Cấu hình câu hỏi khảo sát theo Job Position'
    _order = 'sequence, id'

    job_id = fields.Many2one('hr.job', string='Vị trí tuyển dụng', required=True, ondelete='cascade')
    master_question_id = fields.Many2one(
        'survey.question', string='Câu Hỏi Gốc', required=True, ondelete='cascade'
    )
    
    is_selected = fields.Boolean('Chọn', default=False)
    is_required = fields.Boolean(
        'Bắt Buộc', default=False,
        help='Nếu ứng viên trả lời sai câu này, hệ thống sẽ tự động chuyển sang trạng thái xem xét hoặc từ chối.'
    )
    min_score = fields.Float('Điểm Tối Thiểu', default=0.0)

    # Related fields for display
    question_title = fields.Char(related='master_question_id.title', readonly=True, string='Nội dung câu hỏi')
    question_type = fields.Selection(related='master_question_id.question_type', readonly=True, string='Loại câu hỏi')
    sequence = fields.Integer(related='master_question_id.sequence', store=True, string='Thứ tự')
