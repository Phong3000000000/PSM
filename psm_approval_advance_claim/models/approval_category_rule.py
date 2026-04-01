from odoo import fields, models, api
from odoo.exceptions import ValidationError

class ApprovalCategoryRule(models.Model):
    _name = "approval.category.rule"
    _description = "Approval Category Rule"
    _order = "sequence, id"

    category_id = fields.Many2one(
        "approval.category",
        required=True,
        ondelete="cascade"
    )

    sequence = fields.Integer(default=10)

    # ===== CONDITION =====
    condition_field = fields.Selection(
        [("amount", "Amount")],
        required=True,
        default="amount"
    )

    condition_operator = fields.Selection(
        [
            (">", ">"),
            (">=", ">="),
            ("<", "<"),
            ("<=", "<="),
            ("=", "="),
        ],
        required=True,
        default=">"
    )

    condition_value = fields.Float(required=True)

    # ===== APPROVER CONFIG =====
    approver_user_id = fields.Many2one(
        "res.users",
        string="Approver User",
        compute="_compute_approver_user_id",
        store=True,
        readonly=True
    )

    approver_job_id = fields.Many2one(
        "hr.job",
        string="Approver Job Position"
    )

    # Computed field để dùng trong XML conditional
    approver_type = fields.Selection(
        related="category_id.approver_type",
        string="Approver Type",
        store=False
    )

    # =========================
    # COMPUTE – lấy approver từ job position
    # =========================
    @api.depends("approver_job_id")
    def _compute_approver_user_id(self):
        """Tự động lấy employee từ job position"""
        for rec in self:
            if rec.approver_job_id:
                # Lấy employee đang làm việc ở job position này
                employee = self.env["hr.employee"].search(
                    [
                        ("job_id", "=", rec.approver_job_id.id),
                        ("active", "=", True),
                    ],
                    limit=1,
                    order="create_date desc"
                )
                if employee and employee.user_id:
                    rec.approver_user_id = employee.user_id
                else:
                    rec.approver_user_id = False
            else:
                rec.approver_user_id = False

    # =========================
    # ONCHANGE – làm UI "đúng"
    # =========================
    @api.onchange("category_id")
    def _onchange_category_id(self):
        """Reset field không liên quan khi đổi category"""
        if self.category_id:
            if self.category_id.approver_type == "job":
                pass
            elif self.category_id.approver_type == "user":
                self.approver_job_id = False

    @api.onchange("approver_job_id")
    def _onchange_approver_job_id(self):
        """Khi chọn job position, tự động lấy approver user"""
        if self.approver_job_id and self.category_id.approver_type == "job":
            employee = self.env["hr.employee"].search(
                [
                    ("job_id", "=", self.approver_job_id.id),
                    ("active", "=", True),
                ],
                limit=1,
                order="create_date desc"
            )
            if employee and employee.user_id:
                self.approver_user_id = employee.user_id

    # =========================
    # CONSTRAINS – chặn sai
    # =========================
    @api.constrains("approver_user_id", "approver_job_id", "category_id")
    def _check_approver_target(self):
        for rec in self:
            if not rec.category_id:
                continue

            if rec.category_id.approver_type == "user":
                if not rec.approver_user_id:
                    raise ValidationError("Approver User is required.")
                if rec.approver_job_id:
                    raise ValidationError(
                        "Job Position must be empty when approver type is User."
                    )

            if rec.category_id.approver_type == "job":
                if not rec.approver_job_id:
                    raise ValidationError("Approver Job Position is required.")
