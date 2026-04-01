# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from odoo.tools.safe_eval import safe_eval


class ApprovalWorkflow(models.Model):
    _name = "approval.workflow"
    _description = "Approval Workflow"
    _order = "company_id, model_id, sequence, id"

    name = fields.Char(required=True)
    active = fields.Boolean(default=True)
    sequence = fields.Integer(default=10)

    company_id = fields.Many2one("res.company", required=True, index=True)
    model_id = fields.Many2one("ir.model", required=True, index=True, ondelete="cascade")
    model = fields.Char(related="model_id.model", store=True, readonly=True)

    # Optional: limit workflow to specific actions. If empty => applies to any action hook.
    trigger_actions = fields.Char(
        help="Comma-separated technical action names to block, e.g. 'button_confirm,action_post'. "
             "If empty, workflow can be applied to any action hook."
    )

    # Amount condition (company currency)
    amount_field_name = fields.Char(default="amount_total", required=True)
    min_amount = fields.Monetary(currency_field="currency_id")
    max_amount = fields.Monetary(currency_field="currency_id")
    currency_id = fields.Many2one(
        "res.currency",
        related="company_id.currency_id",
        store=True,
        readonly=True,
    )

    # Domain condition on the target document
    domain_condition = fields.Text(
        help="Odoo domain (Python literal) applied to the target document. Example: [('partner_id', '!=', False)]"
    )

    step_ids = fields.One2many("approval.step", "workflow_id", string="Steps", copy=True)

    _sql_constraints = [
        ("name_company_model_uniq", "unique(name, company_id, model_id)",
         "Workflow name must be unique per company and model.")
    ]

    @api.constrains("min_amount", "max_amount")
    def _check_amount_bounds(self):
        for wf in self:
            if wf.min_amount and wf.max_amount and wf.min_amount > wf.max_amount:
                raise ValidationError(_("min_amount cannot be greater than max_amount."))

    def _trigger_allows(self, action_name: str) -> bool:
        """Return True if this workflow is allowed to apply for the action hook."""
        self.ensure_one()
        if not action_name:
            return True
        if not self.trigger_actions:
            return True
        allowed = [a.strip() for a in (self.trigger_actions or "").split(",") if a.strip()]
        return action_name in allowed

    def _get_record_amount_company_currency(self, record):
        """Get record amount in company currency. If field missing -> 0.0."""
        self.ensure_one()
        amount = 0.0
        field_name = self.amount_field_name or "amount_total"
        if hasattr(record, field_name):
            try:
                amount = float(getattr(record, field_name) or 0.0)
            except Exception:
                amount = 0.0

        # convert currency if record has currency_id and company currency differs
        rec_currency = getattr(record, "currency_id", False)
        if rec_currency and self.company_id.currency_id and rec_currency != self.company_id.currency_id:
            try:
                amount = rec_currency._convert(
                    amount,
                    self.company_id.currency_id,
                    self.company_id,
                    fields.Date.context_today(record),
                )
            except Exception:
                # fallback: keep raw amount
                pass
        return amount

    def _domain_matches(self, record) -> bool:
        """Evaluate workflow domain on the record (single record)."""
        self.ensure_one()
        if not self.domain_condition:
            return True
        try:
            dom = safe_eval(self.domain_condition, {"uid": self.env.uid, "user": self.env.user})
            if not isinstance(dom, (list, tuple)):
                return False
            return bool(record.filtered_domain(list(dom)))
        except Exception:
            return False

    def is_applicable(self, record, action_name: str = "") -> bool:
        """Decide if this workflow applies to the given record and action hook."""
        self.ensure_one()

        if not self.active:
            return False
        if record.company_id and record.company_id != self.company_id:
            return False
        if not self._trigger_allows(action_name):
            return False

        amount = self._get_record_amount_company_currency(record)
        if self.min_amount and amount < self.min_amount:
            return False
        if self.max_amount and amount > self.max_amount:
            return False

        if not self._domain_matches(record):
            return False

        return True


class ApprovalStep(models.Model):
    _name = "approval.step"
    _description = "Approval Step"
    _order = "workflow_id, sequence, id"

    name = fields.Char(required=True, default="Approval Step")
    workflow_id = fields.Many2one("approval.workflow", required=True, ondelete="cascade", index=True)
    sequence = fields.Integer(default=10, index=True)

    # Approver selection
    step_type = fields.Selection(
        [
            ("user", "User(s)"),
            ("group", "Group"),
            ("manager_chain", "Manager Chain"),
            ("field_based", "Field-based (res.users field)"),
        ],
        required=True,
        default="user",
    )

    user_ids = fields.Many2many("res.users", string="Approver Users")
    group_id = fields.Many2one("res.groups", string="Approver Group")

    # Manager chain config (simple, generic):
    manager_from_user_field_name = fields.Char(
        default="user_id",
        help="Name of a Many2one(res.users) field on the document used as the starting user for manager chain. "
             "Example: 'user_id', 'responsible_id'."
    )
    manager_levels = fields.Integer(default=1, help="How many levels up to include (1 = direct manager).")

    # Field-based approver
    user_field_id = fields.Many2one(
        "ir.model.fields",
        string="User Field",
        domain="[('model_id', '=', workflow_id.model_id), ('ttype', '=', 'many2one'), ('relation', '=', 'res.users')]",
        help="Pick a Many2one(res.users) field on the target model to resolve approver(s)."
    )

    # Optional conditions at step level
    min_amount = fields.Monetary(currency_field="currency_id")
    max_amount = fields.Monetary(currency_field="currency_id")
    currency_id = fields.Many2one(
        "res.currency",
        related="workflow_id.company_id.currency_id",
        store=True,
        readonly=True,
    )
    domain_condition = fields.Text(help="Extra domain condition for this step.")

    # Parallel flag:
    # - parallel=True  => ALL assigned approvers must approve this step.
    # - parallel=False => ANY ONE approval completes the step (others cancelled).
    parallel = fields.Boolean(default=False)

    @api.constrains("min_amount", "max_amount")
    def _check_amount_bounds(self):
        for st in self:
            if st.min_amount and st.max_amount and st.min_amount > st.max_amount:
                raise ValidationError(_("Step min_amount cannot be greater than max_amount."))

    def _domain_matches(self, record) -> bool:
        self.ensure_one()
        if not self.domain_condition:
            return True
        try:
            dom = safe_eval(self.domain_condition, {"uid": self.env.uid, "user": self.env.user})
            if not isinstance(dom, (list, tuple)):
                return False
            return bool(record.filtered_domain(list(dom)))
        except Exception:
            return False

    def is_applicable(self, record) -> bool:
        """Check step-level conditions."""
        self.ensure_one()
        wf = self.workflow_id
        amount = wf._get_record_amount_company_currency(record)
        if self.min_amount and amount < self.min_amount:
            return False
        if self.max_amount and amount > self.max_amount:
            return False
        if not self._domain_matches(record):
            return False
        return True

    def _resolve_manager_chain_users(self, start_user):
        """Resolve manager chain via HR employee hierarchy if available; fallback to conservative behavior."""
        self.ensure_one()
        if not start_user:
            return self.env["res.users"]

        users = self.env["res.users"]
        levels = max(int(self.manager_levels or 0), 0)
        if levels <= 0:
            return users

        Employee = self.env["hr.employee"].sudo() if "hr.employee" in self.env else None
        current_user = start_user
        for _i in range(levels):
            manager_user = None
            if Employee:
                emp = Employee.search([("user_id", "=", current_user.id)], limit=1)
                if emp and emp.parent_id and emp.parent_id.user_id:
                    manager_user = emp.parent_id.user_id
            if not manager_user:
                break
            users |= manager_user
            current_user = manager_user

        return users

    def get_approver_users(self, record):
        """Resolve actual approvers (res.users recordset) for this step."""
        self.ensure_one()
        if self.step_type == "user":
            return self.user_ids

        if self.step_type == "group":
            if not self.group_id:
                return self.env["res.users"]
            return self.env["res.users"].search([("groups_id", "in", self.group_id.id), ("share", "=", False)])

        if self.step_type == "field_based":
            if not self.user_field_id:
                return self.env["res.users"]
            field_name = self.user_field_id.name
            user = getattr(record, field_name, False)
            return user if user else self.env["res.users"]

        if self.step_type == "manager_chain":
            field_name = (self.manager_from_user_field_name or "user_id").strip()
            start_user = getattr(record, field_name, False) if hasattr(record, field_name) else False
            return self._resolve_manager_chain_users(start_user)

        return self.env["res.users"]
