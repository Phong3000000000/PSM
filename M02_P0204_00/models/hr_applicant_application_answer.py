# -*- coding: utf-8 -*-
from odoo import models, fields, api

class HrApplicantApplicationAnswerLine(models.Model):
    _name = 'hr.applicant.application.answer.line'
    _description = 'Lịch sử trả lời biểu mẫu ứng tuyển'
    _order = 'section, sequence, id'

    applicant_id = fields.Many2one('hr.applicant', string='Ứng viên', ondelete='cascade', required=True)
    master_field_id = fields.Many2one('recruitment.application.field.master', string='Trường biểu mẫu')
    
    section = fields.Selection([
        ('basic_info', 'Thông tin cơ bản'),
        ('other_info', 'Các thông tin khác'),
        ('supplementary_question', 'Câu hỏi bổ sung'),
        ('internal_question', 'Câu hỏi nội bộ'),
    ], string='Phân nhóm')
    
    sequence = fields.Integer('Thứ tự', default=10)
    
    field_label = fields.Char('Câu hỏi (Snapshot)', required=True)
    field_type = fields.Char('Loại (Snapshot)')
    
    applicant_answer_text = fields.Char('Trả lời của ứng viên')
    expected_answer_text = fields.Char('Đáp án phải đúng')
    
    is_answer_must_match = fields.Boolean('Phải đúng')
    is_answer_correct = fields.Boolean('Kết quả đúng', default=True)
