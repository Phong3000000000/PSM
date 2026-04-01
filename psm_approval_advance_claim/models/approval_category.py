from odoo import fields, models

class ApprovalCategory(models.Model):
    _inherit = "approval.category"

    is_advance_claim = fields.Selection(
        [('yes', 'YES'), ('no', 'NO')],
        string="Is Advance Claim",
        default="no",
        required=True,
    )

    approver_type = fields.Selection(
        [
            ("user", "Specific User"),
            ("job", "Job Position"),
        ],
        string="Approver Type",
        required=True,
        default="user"
    )

    rule_ids = fields.One2many(
        "approval.category.rule",
        "category_id",
        string="Approval Rules"
    )

