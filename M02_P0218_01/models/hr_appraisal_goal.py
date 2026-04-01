# -*- coding: utf-8 -*-

from odoo import models, fields, api


class HrAppraisalGoal(models.Model):
    _inherit = 'hr.appraisal.goal'

    goal_type = fields.Selection(
        [
            ('store', 'Store Goals achievement'),
            ('individual', 'Individual Goals achievement')
        ],
        string='Goal Type',
        default='individual',
        help='Type of goal: Store level or Individual level achievement'
    )
    
    score = fields.Float(
        string='Điểm',
        compute='_compute_score',
        store=True,
        help='Score out of 4 based on progression (0% = 0, 25% = 1, 50% = 2, 75% = 3, 100% = 4)'
    )
    
    @api.depends('progression')
    def _compute_score(self):
        """Compute score based on progression percentage."""
        progression_to_score = {
            '000': 0.0,  # 0%
            '025': 1.0,  # 25%
            '050': 2.0,  # 50%
            '075': 3.0,  # 75%
            '100': 4.0,  # 100%
        }
        for goal in self:
            goal.score = progression_to_score.get(goal.progression, 0.0)
    
    @api.model
    def default_get(self, fields_list):
        """Override to auto-fill employee_ids and manager_ids from appraisal context."""
        res = super(HrAppraisalGoal, self).default_get(fields_list)
        
        # Check if we're creating a goal from an appraisal context
        appraisal_id = self.env.context.get('default_appraisal_id')
        
        if appraisal_id:
            appraisal = self.env['hr.appraisal'].browse(appraisal_id)
            
            # Fill employee_ids with appraisal's employee_id
            if 'employee_ids' in fields_list and appraisal.employee_id:
                res['employee_ids'] = [(6, 0, [appraisal.employee_id.id])]
            
            # Fill manager_ids with appraisal's manager_ids
            if 'manager_ids' in fields_list and appraisal.manager_ids:
                res['manager_ids'] = [(6, 0, appraisal.manager_ids.ids)]
        
        return res
    
    def _recompute_related_appraisals(self):
        """Trigger recomputation of average goal scores in related appraisals."""
        # Get all unique employees from this goal
        employee_ids = self.mapped('employee_ids')
        if employee_ids:
            # Find all appraisals for these employees
            appraisals = self.env['hr.appraisal'].search([
                ('employee_id', 'in', employee_ids.ids)
            ])
            if appraisals:
                # Force recompute of goal scores
                appraisals._compute_goal_scores()
    
    @api.model_create_multi
    def create(self, vals_list):
        """Override create to trigger appraisal score recompute."""
        goals = super(HrAppraisalGoal, self).create(vals_list)
        goals._recompute_related_appraisals()
        return goals
    
    def write(self, vals):
        """Override write to trigger appraisal score recompute when relevant fields change."""
        # Check if we're modifying fields that affect appraisal scores
        score_affecting_fields = {'score', 'goal_type', 'employee_ids', 'progression'}
        if any(field in vals for field in score_affecting_fields):
            # Get employees before write
            old_employees = self.mapped('employee_ids')
            
        result = super(HrAppraisalGoal, self).write(vals)
        
        # Trigger recompute if score-affecting fields were changed
        if any(field in vals for field in score_affecting_fields):
            # Recompute for old and new employees (in case employee_ids changed)
            self._recompute_related_appraisals()
            if 'employee_ids' in vals and old_employees:
                # Also recompute for old employees if they were changed
                old_appraisals = self.env['hr.appraisal'].search([
                    ('employee_id', 'in', old_employees.ids)
                ])
                if old_appraisals:
                    old_appraisals._compute_goal_scores()
        
        return result
    
    def unlink(self):
        """Override unlink to trigger appraisal score recompute."""
        # Store employees before deletion
        employee_ids = self.mapped('employee_ids')
        result = super(HrAppraisalGoal, self).unlink()
        
        # Recompute appraisals for affected employees
        if employee_ids:
            appraisals = self.env['hr.appraisal'].search([
                ('employee_id', 'in', employee_ids.ids)
            ])
            if appraisals:
                appraisals._compute_goal_scores()
        
        return result
