# -*- coding: utf-8 -*-
from odoo import models, fields

class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    x_job_level = fields.Selection([
        ('crew', 'Crew'),
        ('leader', 'Leader'),
        ('manager', 'Manager'),
        ('store_manager', 'Store Manager')
    ], string='Job Level', default='crew')
    
    x_team_function = fields.Selection([
        ('kitchen', 'Kitchen'),
        ('service', 'Service'),
        ('security', 'Security'),
        ('management', 'Management')
    ], string='Team Function')

