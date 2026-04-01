# -*- coding: utf-8 -*-
from odoo import models, fields

class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    legal_name = fields.Char(string='Legal Name', help="Full legal name of the employee as shown in ID/Passport")
    private_phone = fields.Char(string='Private Phone', help="Private phone number of the employee")
    
