# -*- coding: utf-8 -*-
from odoo import models, api
from odoo.tools import float_is_zero

class SurveyUserInputLine(models.Model):
    _inherit = 'survey.user_input.line'

    @api.depends('answer_type', 'value_text_box', 'value_numerical_box', 'value_date', 'value_datetime',
                 'suggested_answer_id', 'user_input_id', 'matrix_row_id')
    def _compute_answer_score(self):
        """Override to add matrix question scoring support.
        
        For matrix questions:
        - Each row selection contributes to the score
        - The score comes from the selected column answer (suggested_answer_id)
        """
        # Call super first to handle existing question types
        super(SurveyUserInputLine, self)._compute_answer_score()
        
        # Add matrix question scoring
        for line in self:
            if line.question_id.question_type == 'matrix' and line.answer_type == 'suggestion':
                if line.suggested_answer_id and line.matrix_row_id:
                    # Score comes from the column (suggested_answer_id)
                    line.answer_score = line.suggested_answer_id.answer_score or 0.0
                    # Matrix questions don't use is_correct, so keep it as False
                    # unless you want to implement a specific logic
                    line.answer_is_correct = line.answer_score > 0
