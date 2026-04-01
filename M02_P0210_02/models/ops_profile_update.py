from odoo import models, fields


class OpsProfileUpdate(models.Model):
    """OPS Capacity Profile Update Records (B12-B16 Audit Trail)"""
    _name = 'mcd.ops.profile.update'
    _description = 'OPS Profile Update Record'
    _order = 'create_date desc'

    process_id = fields.Many2one('mcd.ops.capacity.process', string='Process', required=True, ondelete='cascade')
    employee_id = fields.Many2one(related='process_id.employee_id', string='Employee', store=True)
    
    # Level Change
    old_level = fields.Char(string='Previous Level')
    new_level = fields.Char(string='New Level')
    
    # B12: L&D Feedback
    lnd_feedback = fields.Text(string='B12: L&D Training Effectiveness')
    
    # B13: Employee Feedback
    employee_feedback = fields.Text(string='B13: Employee Course Feedback')
    
    # B14: Profile Update
    skill_granted_id = fields.Many2one('hr.skill', string='B14: Skill Granted')
    
    # B15: Permission Update
    permission_updated = fields.Boolean(string='B15: Permissions Updated', default=True)
    group_added_id = fields.Many2one('res.groups', string='Group Added')
    
    # B16: Budget Update
    budget_recorded = fields.Float(string='B16: Training Cost')
    
    update_date = fields.Datetime(string='Update Date', default=fields.Datetime.now)
