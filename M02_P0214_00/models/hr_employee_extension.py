# -*- coding: utf-8 -*-
from odoo import models, fields


class HrEmployeeRSTExtension(models.Model):
    """Extend hr.employee with RST identification"""
    _inherit = 'hr.employee'

    is_rst_employee = fields.Boolean(
        string="Is RST Employee",
        default=False,
        help="Check this if the employee is part of RST (Resignation & Turnover Support) team"
    )
