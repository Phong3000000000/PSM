from odoo import models, fields


class HrDisciplineViolationCategory(models.Model):
    _name = "hr.discipline.violation.category"
    _description = "Discipline Violation Category"

    name = fields.Char(string="Category Name", required=True)
    code = fields.Char(string="Code")
