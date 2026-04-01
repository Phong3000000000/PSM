# -*- coding: utf-8 -*-

from odoo import models, fields, api


class HrAppraisal(models.Model):
    _inherit = 'hr.appraisal'

    is_performance_manager_ops = fields.Boolean(
        string='Is Performance Manager OPS',
        default=False,
        help='Marks if this appraisal is for a Performance Manager in Operations'
    )

    appraisal_type = fields.Selection([
        ('ops_manager', 'OPS Manager'),
    ], string='Appraisal Type', default='ops_manager',
       help='Type of appraisal evaluation'
    )
    
    survey_response_ids = fields.One2many(
        'survey.user_input',
        'appraisal_id',
        string='Survey Responses',
        help='All survey responses related to this appraisal'
    )
    
    average_matrix_score = fields.Float(
        string='Average Matrix Score(BEST Score)',
        compute='_compute_average_matrix_score',
        store=True,
        help='Average of matrix_average_score from all related survey responses'
    )
    
    @api.depends('survey_response_ids.matrix_average_score')
    def _compute_average_matrix_score(self):
        """Calculate the average matrix score from all survey responses."""
        for appraisal in self:
            survey_responses = appraisal.survey_response_ids
            if survey_responses:
                # Filter out responses with 0 score (optional - depends on requirements)
                scores = survey_responses.mapped('matrix_average_score')
                # Calculate average of all scores
                appraisal.average_matrix_score = round(sum(scores) / len(scores), 2) if scores else 0.0
            else:
                appraisal.average_matrix_score = 0.0
    
    def action_open_goals(self):
        """Override to pass appraisal context for auto-filling employee_ids and manager_ids in goals."""
        result = super(HrAppraisal, self).action_open_goals()
        
        # Add appraisal context to auto-fill employee_ids and manager_ids
        if result.get('context'):
            result['context'].update({
                'default_appraisal_id': self.id,
                'default_employee_ids': [(6, 0, [self.employee_id.id])] if self.employee_id else False,
                'default_manager_ids': [(6, 0, self.manager_ids.ids)] if self.manager_ids else False,
            })
        else:
            result['context'] = {
                'default_appraisal_id': self.id,
                'default_employee_ids': [(6, 0, [self.employee_id.id])] if self.employee_id else False,
                'default_manager_ids': [(6, 0, self.manager_ids.ids)] if self.manager_ids else False,
            }
        
        return result
    
    average_store_goal_score = fields.Float(
        string='Điểm TB Mục Tiêu Cửa Hàng',
        compute='_compute_goal_scores',
        store=True,
        help='Average score of Store type goals'
    )
    
    average_individual_goal_score = fields.Float(
        string='Điểm TB Mục Tiêu Cá Nhân',
        compute='_compute_goal_scores',
        store=True,
        help='Average score of Individual type goals'
    )
    
    performance_rating = fields.Float(
        string='Performance Rating',
        compute='_compute_performance_rating',
        store=True,
        help='Overall performance rating: 50% Matrix Score + 25% Store Goals + 25% Individual Goals'
    )
    
    @api.depends('average_matrix_score', 'average_store_goal_score', 'average_individual_goal_score')
    def _compute_performance_rating(self):
        """Compute performance rating as weighted average of scores."""
        for appraisal in self:
            # Formula: 50% matrix + 25% store goals + 25% individual goals
            appraisal.performance_rating = (
                (appraisal.average_matrix_score * 0.5) +
                (appraisal.average_store_goal_score * 0.25) +
                (appraisal.average_individual_goal_score * 0.25)
            )
    
    @api.onchange('performance_rating')
    def _onchange_performance_rating(self):
        """Auto-select assessment_note (Final Rating) based on performance_rating."""
        if not self.performance_rating:
            return
        
        selected_note = self._get_assessment_note_for_rating(self.performance_rating)
        if selected_note:
            self.assessment_note = selected_note
    
    def _get_assessment_note_for_rating(self, rating_score):
        """Helper method to find appropriate assessment_note based on rating score."""
        if not rating_score:
            return False
        
        # Get all appraisal notes with scores, ordered by score descending
        notes = self.env['hr.appraisal.note'].search([
            ('score', '!=', False)
        ], order='score desc')
        
        # Find the appropriate rating level
        # Logic: Find the highest score threshold that is <= performance_rating
        selected_note = False
        for note in notes:
            if rating_score >= note.score:
                selected_note = note
                break
        
        # If no match found (performance_rating < all thresholds), select lowest
        if not selected_note and notes:
            selected_note = notes[-1]  # Get the one with lowest score
        
        return selected_note
    
    def write(self, vals):
        """Override write to auto-update assessment_note when performance_rating changes."""
        result = super(HrAppraisal, self).write(vals)
        
        # Auto-update assessment_note when performance_rating is computed
        for appraisal in self:
            if appraisal.performance_rating and not vals.get('assessment_note'):
                # Only auto-set if user didn't explicitly set assessment_note
                selected_note = appraisal._get_assessment_note_for_rating(appraisal.performance_rating)
                if selected_note and selected_note != appraisal.assessment_note:
                    super(HrAppraisal, appraisal).write({'assessment_note': selected_note.id})
        
        return result
    
    @api.depends('employee_id')
    def _compute_goal_scores(self):
        """Compute average scores for store and individual goals."""
        for appraisal in self:
            if not appraisal.employee_id:
                appraisal.average_store_goal_score = 0.0
                appraisal.average_individual_goal_score = 0.0
                continue
            
            # Get all goals for this employee
            goals = self.env['hr.appraisal.goal'].search([
                ('employee_ids', '=', appraisal.employee_id.id),
                ('child_ids', '=', False)  # Only parent goals
            ])
            
            # Calculate average for store goals
            store_goals = goals.filtered(lambda g: g.goal_type == 'store')
            if store_goals:
                appraisal.average_store_goal_score = sum(store_goals.mapped('score')) / len(store_goals)
            else:
                appraisal.average_store_goal_score = 0.0
            
            # Calculate average for individual goals
            individual_goals = goals.filtered(lambda g: g.goal_type == 'individual')
            if individual_goals:
                appraisal.average_individual_goal_score = sum(individual_goals.mapped('score')) / len(individual_goals)
            else:
                appraisal.average_individual_goal_score = 0.0

