# -*- coding: utf-8 -*-
from odoo import models, fields


class ResCompany(models.Model):
    _inherit = "res.company"

    ceo_id = fields.Many2one(
        "hr.employee",
        string="CEO",
        help="Giám đốc điều hành chịu trách nhiệm của công ty.",
    )
