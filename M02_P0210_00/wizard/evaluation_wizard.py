from odoo import models, fields, api


class OpsEvaluationWizard(models.TransientModel):
    """Wizard for RGM/OC to evaluate employee at steps B9, B11, B19, B21, B24, B26, B28, B30, B32"""
    _name = 'mcd.ops.evaluation.wizard'
    _description = 'OPS Evaluation Wizard'

    process_id = fields.Many2one('mcd.ops.capacity.process', string='Process', 
                                  default=lambda self: self.env.context.get('active_id'))
    
    eval_type = fields.Selection([
        ('set_pet', 'B9: SET/PET'),
        ('slv', 'B11: SLV'),
        ('dm1_course', 'B19: DM1 Course Check'),
        ('3sv', 'B21: 3 System Verify'),
        ('dm2_course', 'B24: DM2 Course Check'),
        ('2sv', 'B26: 2 System Verify'),
        ('rgm_course', 'B28: RGM Course Check'),
        ('4sv', 'B30: 4 System Verify'),
        ('lff', 'B32: LFF Final')
    ], string='Evaluation Type', required=True)
    
    result = fields.Selection([
        ('pass', 'PASS'),
        ('fail', 'FAIL')
    ], string='Result', required=True, default='pass')
    
    fail_reason = fields.Text(string='Reason (if Failed)')
    notes = fields.Text(string='Additional Notes')

    def action_confirm(self):
        """Confirm the evaluation and trigger the appropriate action"""
        self.ensure_one()
        process = self.process_id
        passed = self.result == 'pass'
        fail_reason = self.fail_reason if not passed else None
        
        # Map eval_type to action methods
        action_map = {
            'set_pet': 'action_b9_evaluate',
            'slv': 'action_b11_evaluate',
            'dm1_course': 'action_b19_evaluate',
            '3sv': 'action_b21_evaluate',
            'dm2_course': 'action_b24_evaluate',
            '2sv': 'action_b26_evaluate',
            'rgm_course': 'action_b28_evaluate',
            '4sv': 'action_b30_evaluate',
            'lff': 'action_b32_evaluate'
        }
        
        method_name = action_map.get(self.eval_type)
        if method_name and hasattr(process, method_name):
            getattr(process, method_name)(passed=passed, fail_reason=fail_reason)
        
        return {'type': 'ir.actions.act_window_close'}
