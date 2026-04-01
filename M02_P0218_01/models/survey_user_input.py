# -*- coding: utf-8 -*-
from odoo import models, api, fields

class SurveyUserInput(models.Model):
    _inherit = 'survey.user_input'
    
    appraisal_id = fields.Many2one(
        'hr.appraisal',
        string='Related Appraisal',
        ondelete='set null',
        help='The appraisal this survey response belongs to'
    )
    
    matrix_average_score = fields.Float(
        string='Matrix Average Score',
        compute='_compute_scoring_values',
        store=True,
        help='Average score per row for matrix questions (total score / number of rows)'
    )

    @api.depends('user_input_line_ids.answer_score', 'user_input_line_ids.question_id', 'predefined_question_ids.answer_score')
    def _compute_scoring_values(self):
        """Override to include matrix questions in total_possible_score calculation and compute average."""
        for user_input in self:
            # sum(multi-choice question scores) + sum(simple answer_type scores) + sum(matrix scores)
            total_possible_score = 0
            total_matrix_rows = 0  # Track total number of matrix rows
            
            for question in user_input.predefined_question_ids:
                if question.question_type == 'simple_choice':
                    total_possible_score += max([score for score in question.mapped('suggested_answer_ids.answer_score') if score > 0], default=0)
                elif question.question_type == 'multiple_choice':
                    total_possible_score += sum(score for score in question.mapped('suggested_answer_ids.answer_score') if score > 0)
                elif question.question_type == 'matrix':
                    # For matrix: number of rows × max column score
                    max_column_score = max([score for score in question.mapped('suggested_answer_ids.answer_score') if score > 0], default=0)
                    row_count = len(question.matrix_row_ids)
                    total_possible_score += max_column_score * row_count
                    total_matrix_rows += row_count  # Count matrix rows
                elif question.is_scored_question:
                    total_possible_score += question.answer_score

            # Calculate scoring percentage
            if total_possible_score == 0:
                user_input.scoring_percentage = 0
                user_input.scoring_total = 0
            else:
                score_total = sum(user_input.user_input_line_ids.mapped('answer_score'))
                user_input.scoring_total = score_total
                score_percentage = (score_total / total_possible_score) * 100
                user_input.scoring_percentage = round(score_percentage, 2) if score_percentage > 0 else 0
            
            # Calculate matrix average score (average per row)
            if total_matrix_rows > 0:
                # Get score from matrix lines only
                matrix_lines = user_input.user_input_line_ids.filtered(lambda l: l.matrix_row_id)
                matrix_total_score = sum(matrix_lines.mapped('answer_score'))
                user_input.matrix_average_score = round(matrix_total_score / total_matrix_rows, 2)
            else:
                user_input.matrix_average_score = 0.0
