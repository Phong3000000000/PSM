# -*- coding: utf-8 -*-

from odoo import models, fields

class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    salary_increase_history_ids = fields.One2many(
        'salary.increase.plan.line',
        'employee_id',
        string='Lịch sử tăng lương',
        domain=[('is_applied', '=', True)]
    )
