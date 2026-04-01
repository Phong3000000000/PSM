# -*- coding: utf-8 -*-
import random
from odoo import models, api

class AppraisalAskFeedback(models.TransientModel):
    _inherit = 'appraisal.ask.feedback'

    @api.model
    def default_get(self, fields):
        res = super(AppraisalAskFeedback, self).default_get(fields)
        

        # Only proceed if we are in the context of an appraisal
        if 'appraisal_id' in res:
            appraisal = self.env['hr.appraisal'].browse(res['appraisal_id'])
        elif self.env.context.get('active_model') == 'hr.appraisal' and self.env.context.get('active_id'):
            appraisal = self.env['hr.appraisal'].browse(self.env.context.get('active_id'))
        else:
            return res

        # Check if this appraisal is a Performance Manager OPS appraisal
        if not appraisal.is_performance_manager_ops:
            return res

        employee = appraisal.employee_id
        if not employee:
            return res

        selected_employees = self.env['hr.employee']

        # 1. Select 1 Manager (Direct Parent)
        if employee.parent_id:
            selected_employees |= employee.parent_id

        # 2. Select 1 Random Subordinate
        subordinates = employee.child_ids
        if subordinates:
            selected_employees |= random.choice(subordinates)

        # 3. Select 1 Random Colleague (Same Parent, excluding self)
        if employee.parent_id:
            colleagues = self.env['hr.employee'].search([
                ('parent_id', '=', employee.parent_id.id),
                ('id', '!=', employee.id)
            ])
            # Exclude already selected (though unlikely to be manager/subordinate overlap in standard tree, but good practice)
            colleagues -= selected_employees
            
            if colleagues:
                selected_employees |= random.choice(colleagues)

        # Update employee_ids in the result
        if selected_employees:
            # If there were already employees (e.g. from context), we append or replace? 
            # Usually default_get provides the initial state. The requirement implies "Auto fill", so we set it.
            # existing_ids = res.get('employee_ids', [])
            # if isinstance(existing_ids, list) and existing_ids and isinstance(existing_ids[0], (int, tuple)):
                 # Handle Odoo command format if necessary, but usually default_get returns ids list for many2many if standard
                 # Actually for many2many default_get might return [(6, 0, ids)]
            # Let's simple utilize the ORM ids list which Odoo usually accepts in default_get for M2M if it's a list if int.
            # However, safer to use Command format or just list of IDs.
            
            res['employee_ids'] = [(6, 0, selected_employees.ids)]
            

        return res


    def _prepare_survey_anwers(self, employees):
        """
        Override to ALWAYS create new survey inputs, even if one exists.
        This allows multiple feedback requests to the same person for the same appraisal
        to generate distinct survey responses (e.g., 2 requests = 4 inputs if 2 people each).
        """
        answers = self.env['survey.user_input']
        
        # Sudo is required to access employee fields like contract_type_id if the user is not an HR Manager
        for employee in employees.sudo():
            partner = employee.work_contact_id or employee.user_id.partner_id
            email = employee.work_email or employee.user_id.partner_id.email
            
            # Unconditionally create a new answer
            answers |= self.survey_template_id.sudo()._create_answer(
                partner=partner, 
                email=email, 
                check_attempts=False, 
                deadline=self.deadline
            )
            
        return answers
