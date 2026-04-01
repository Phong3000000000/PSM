# -*- coding: utf-8 -*-
from odoo import models, fields, api

class HrPayrollStructureType(models.Model):
    _inherit = 'hr.payroll.structure.type'

    # Requirement 1.2: Department (Applied For)
    # "Ensure each department uses the correct salary structure"
    x_department_ids = fields.Many2many('hr.department', string='Applied Departments',
        help="Departments that should use this Structure Type by default.")

