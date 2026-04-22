from odoo import models, fields

class TravelAdminConfig(models.Model):
    _name = 'x_psm_travel_admin_config'
    _description = 'Travel Admin Configuration'
    _rec_name = 'x_psm_user_id'
    
    x_psm_user_id = fields.Many2one('res.users', string='Administrator', required=True)
    x_psm_active = fields.Boolean(default=True)
