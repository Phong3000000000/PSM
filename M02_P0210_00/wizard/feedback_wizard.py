from odoo import models, fields, api

class OpsFeedbackWizard(models.TransientModel):
    """Wizard for L&D and Employee feedback"""
    _name = 'mcd.ops.feedback.wizard'
    _description = 'OPS Feedback Wizard'

    process_id = fields.Many2one('mcd.ops.capacity.process', string='Process')
    schedule_id = fields.Many2one('mcd.manager.schedule', string='Manager Schedule')
    
    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        active_id = self.env.context.get('active_id')
        active_model = self.env.context.get('active_model')
        
        if active_model == 'mcd.ops.capacity.process':
            res['process_id'] = active_id
        elif active_model == 'mcd.manager.schedule':
            res['schedule_id'] = active_id
            
        return res
    
    feedback_type = fields.Selection([
        ('lnd', 'L&D Training Effectiveness'),
        ('employee', 'Employee Course Feedback')
    ], string='Feedback Type', required=True)
    
    feedback = fields.Text(string='Feedback', required=True)

    def action_confirm(self):
        """Confirm the feedback and proceed to next step"""
        self.ensure_one()
        
        if self.process_id:
            if self.feedback_type == 'lnd':
                self.process_id.action_b12_complete(lnd_feedback=self.feedback)
            elif self.feedback_type == 'employee':
                self.process_id.action_b13_complete(employee_feedback=self.feedback)
        
        elif self.schedule_id:
            self.schedule_id.submit_feedback(self.feedback_type, self.feedback)
        
        return {'type': 'ir.actions.act_window_close'}
