from odoo import models, fields


class HrDisciplineAction(models.Model):
    _name = "hr.discipline.action"
    _description = "Discipline Action"
    _order = "sequence, id"

    name = fields.Char(string="Action Name", required=True)
    sequence = fields.Integer(string="Sequence", default=10)
    level = fields.Selection(
        [("store", "Store Level"), ("company", "Company Level")],
        string="Level",
        required=True,
        default="store",
        help="Store Level: RGM decides. Company Level: HR & CEO decides.",
    )

    form_code = fields.Selection(
        [
            ("feedback", "Feedback"),
            ("counselling_1", "Counselling 1st"),
            ("counselling_2", "Counselling 2nd"),
            ("discipline", "Discipline (Termination/Penalty)"),
        ],
        string="Form Code",
        help="Used to map with the checkbox on the physical form.",
    )

    has_penalty = fields.Boolean(
        string="Has Penalty",
        default=False,
        help="Check if this action involves financial penalty or compensation.",
    )

    requires_finance_check = fields.Boolean(
        string="Requires Finance Check?",
        default=False,
        help="If checked, the process must go through Finance for compensation valuation.",
    )

    improvement_period = fields.Integer(
        string="Period (Days)",
        default=30,
        help="Number of days for improvement period.",
    )

    validity_months = fields.Integer(
        string="Validity (Months)",
        default=1,
        help="Period (in months) during which this action counts towards escalation.",
    )
    next_action_id = fields.Many2one(
        "hr.discipline.action",
        string="Next Action (Escalation)",
        help="The next level of action if a repeat offense occurs within the validity period.",
    )
    allowed_job_ids = fields.Many2many(
        "hr.job",
        string="Allowed Jobs",
        help="Job positions allowed to execute this action (e.g., MIC, RGM).",
    )
