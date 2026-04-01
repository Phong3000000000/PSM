from odoo import models, fields


class HrDisciplineViolationType(models.Model):
    _name = "hr.discipline.violation.type"
    _description = "Discipline Violation Type"

    name = fields.Char(string="Violation Name", required=True)
    category_id = fields.Many2one(
        "hr.discipline.violation.category", string="Category", required=True
    )
    severity = fields.Selection(
        [
            ("minor", "Store Level (Nhẹ)"),
            ("major", "Company Level (Nặng)"),
        ],
        string="Mức độ hành vi",
        default="minor",
        required=True,
        help="Phân loại mức độ vi phạm để xác định cấp xử lý và quy trình.",
    )

    improvement_period = fields.Integer(
        string="Improvement Period (Days)",
        default=30,
        help="Period to check for repeat offenses.",
    )
    max_repeats = fields.Integer(
        string="Max Repeats",
        default=3,
        help="Maximum number of allowed repeats within the period before escalation.",
    )
