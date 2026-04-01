from odoo import models, fields, api


class OpsEvaluation(models.Model):
    """OPS Capacity Evaluation Records (B9, B11, B19, B21, B24, B26, B28, B30, B32)"""
    _name = 'mcd.ops.evaluation'
    _description = 'OPS Capacity Evaluation'
    _order = 'eval_date desc'

    process_id = fields.Many2one('mcd.ops.capacity.process', string='Process', required=True, ondelete='cascade')
    employee_id = fields.Many2one(related='process_id.employee_id', string='Employee', store=True)
    
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
    
    evaluator_id = fields.Many2one('res.users', string='Evaluator', default=lambda self: self.env.uid)
    evaluator_role = fields.Selection([
        ('rgm', 'RGM'),
        ('oc', 'OC'),
        ('lnd', 'L&D')
    ], string='Evaluator Role', compute='_compute_evaluator_role', store=True)
    
    result = fields.Selection([
        ('pass', 'Pass'),
        ('fail', 'Fail')
    ], string='Result', required=True)
    
    fail_reason = fields.Text(string='Fail Reason')
    eval_date = fields.Datetime(string='Evaluation Date', default=fields.Datetime.now)
    notes = fields.Text(string='Notes')

    @api.depends('eval_type')
    def _compute_evaluator_role(self):
        """Determine evaluator role based on evaluation type"""
        oc_types = ['slv', '3sv', '2sv', '4sv', 'lff']
        for rec in self:
            if rec.eval_type in oc_types:
                rec.evaluator_role = 'oc'
            else:
                rec.evaluator_role = 'rgm'
