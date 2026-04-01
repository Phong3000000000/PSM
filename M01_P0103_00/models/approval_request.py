import logging
from odoo import api, Command, fields, models, _
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class ApprovalRequest(models.Model):
    _inherit = 'approval.request'

    # === Related field for easier visibility control in views ===
    is_advance_claim = fields.Selection(
        related='category_id.is_advance_claim',
        string='Is Advance Claim',
        store=True,
        readonly=True
    )

    # === Link to Travel Request ===

    travel_request_id = fields.Many2one(
        'approval.request',
        string='Travel Request',
        help='Link to the travel request that created this advance claim',
        ondelete='set null',
    )

    # === Advance Type ===
    advance_type = fields.Selection([
        ('advance', 'Advance Payment'),  # Ứng trước
        ('reimbursement', 'Reimbursement'),  # Hoàn ứng
    ], string='Advance Type', default='advance', tracking=True)

    payment_mode = fields.Selection([
        ('own_account', 'Employee (to reimburse)'),
        ('company_account', 'Company')
    ], string='Paid By', default='own_account', tracking=True)

    # === Payment Method & Bank Account ===

    # Selectable payment method lines (for domain)
    selectable_payment_method_line_ids = fields.Many2many(
        comodel_name='account.payment.method.line',
        compute='_compute_selectable_payment_method_line_ids'
    )

    payment_method_line_id = fields.Many2one(
        comodel_name='account.payment.method.line',
        string="Payment Method",
        compute='_compute_payment_method_line_id',
        store=True,
        readonly=False,
        domain="[('id', 'in', selectable_payment_method_line_ids)]",
        help="The payment method used when the advance is paid by the company.",
    )

    employee_id = fields.Many2one(
        'hr.employee',
        string='Employee',
        compute='_compute_employee_id',
        store=True
    )

    # === Bank Info for Payment (Simple Input Fields) ===
    bank_name = fields.Char(
        string='Bank Name',
        help='Enter bank name for transfer'
    )
    
    account_number = fields.Char(
        string='Account Number',
        help='Enter account number for transfer'
    )

    # === Budget Check Status ===
    budget_check_status = fields.Selection([
        ('draft', 'Draft'),
        ('in_budget', 'In Budget'),
        ('out_of_budget', 'Out of Budget')
    ], string='Budget Status', default='draft', tracking=True, readonly=True)

    # === Linked Expenses ===
    expense_ids = fields.One2many(
        'hr.expense',
        'advance_request_id',
        string='Related Expenses'
    )
    
    expense_count = fields.Integer(
        string='Expense Count',
        compute='_compute_expense_count'
    )

    @api.depends('company_id')
    def _compute_selectable_payment_method_line_ids(self):
        """Compute available payment methods for the company - same logic as hr_expense"""
        for request in self:
            if request.company_id:
                # First check if company has specific allowed payment methods
                allowed_method_line_ids = request.company_id.company_expense_allowed_payment_method_line_ids
                if allowed_method_line_ids:
                    request.selectable_payment_method_line_ids = allowed_method_line_ids
                else:
                    # Search all outbound payment methods for the company
                    request.selectable_payment_method_line_ids = self.env['account.payment.method.line'].search([
                        # The journal is the source of the payment method line company
                        *self.env['account.journal']._check_company_domain(request.company_id),
                        ('payment_type', '=', 'outbound'),
                    ])
            else:
                request.selectable_payment_method_line_ids = False

    @api.depends('company_id', 'is_advance_claim')
    def _compute_payment_method_line_id(self):
        """Auto-select first available payment method for advance claims"""
        for request in self:
            if request.is_advance_claim == 'yes' and request.selectable_payment_method_line_ids:
                if not request.payment_method_line_id or request.payment_method_line_id not in request.selectable_payment_method_line_ids:
                    request.payment_method_line_id = request.selectable_payment_method_line_ids[0]
            else:
                request.payment_method_line_id = False

    @api.depends('request_owner_id')
    def _compute_employee_id(self):
        """Get employee from request owner"""
        for rec in self:
            rec.employee_id = self.env['hr.employee'].search([
                ('user_id', '=', rec.request_owner_id.id)
            ], limit=1)

    @api.depends('expense_ids')
    def _compute_expense_count(self):
        """Count linked expenses"""
        for rec in self:
            rec.expense_count = len(rec.expense_ids)

    # === Auto Budget Check on Create ===
    @api.model_create_multi
    def create(self, vals_list):
        """Auto check budget when creating request"""
        records = super().create(vals_list)
        
        for record in records:
            # Auto check budget for advance claims
            if record.is_advance_claim == 'yes':
                record._auto_check_budget()
        
        return records

    def _auto_check_budget(self):
        """Auto check budget and update status - placeholder returns True"""
        self.ensure_one()
        
        # Call budget check function (currently always returns True)
        if self._check_budget():
            self.budget_check_status = 'in_budget'
        else:
            self.budget_check_status = 'out_of_budget'

    def _check_budget(self):
        """Budget check logic - placeholder always returns True"""
        return True

    # Override để support logic rule-based approvals

    
    @api.depends('category_id', 'request_owner_id', 'amount')
    def _compute_approver_ids(self):
        """
        Override logic để:
        1. Xử lý manager_approval nếu cần
        2. Nếu category có approver_type = 'job' và rule_ids:
           - Tìm rule phù hợp dựa trên amount và condition
           - Lấy approver từ job position được chỉ định trong rule
        3. Nếu category có approver_type = 'user':
           - Lấy approver từ category.approver_ids (logic gốc)
        """
        for request in self:
            users_to_category_approver = {}
            approver_id_vals = [Command.clear()]
            added_user_ids = set()  # Track user IDs đã được thêm để tránh duplicate

            # ===== BƯỚC 1: Xử lý manager_approval =====
            if request.category_id.manager_approval:
                employee = self.env['hr.employee'].search(
                    [('user_id', '=', request.request_owner_id.id)],
                    limit=1
                )
                if employee and employee.parent_id and employee.parent_id.user_id:
                    manager_user_id = employee.parent_id.user_id.id
                    manager_required = request.category_id.manager_approval == 'required'
                    approver_id_vals.append(Command.create({
                        'user_id': manager_user_id,
                        'status': 'new',
                        'required': manager_required,
                        'sequence': 9,  # Manager luôn first
                    }))
                    added_user_ids.add(manager_user_id)  # Track manager đã được thêm
                    if manager_user_id in users_to_category_approver:
                        users_to_category_approver.pop(manager_user_id)

            # ===== BƯỚC 2: Xử lý rule-based approvals (Job Position Type) =====
            if request.category_id.approver_type == 'job' and request.category_id.rule_ids:
                # Tìm các rule phù hợp dựa trên condition
                matching_rules = self._get_matching_rules(request)
                
                for rule in matching_rules:
                    if rule.approver_user_id:
                        user_id = rule.approver_user_id.id
                        # Chỉ thêm nếu chưa có trong danh sách
                        if user_id not in added_user_ids:
                            approver_id_vals.append(Command.create({
                                'user_id': user_id,
                                'status': 'new',
                                'required': True,  # Rule-based approver luôn required
                                'sequence': rule.sequence,
                            }))
                            added_user_ids.add(user_id)

            # ===== BƯỚC 3: Xử lý user-based approvals (User Type) =====
            elif request.category_id.approver_type == 'user':
                for approver in request.category_id.approver_ids:
                    users_to_category_approver[approver.user_id.id] = approver

                for user_id in users_to_category_approver:
                    approver = users_to_category_approver[user_id]
                    approver_id_vals.append(Command.create({
                        'user_id': user_id,
                        'status': 'new',
                        'required': approver.required,
                        'sequence': approver.sequence,
                    }))

            request.update({'approver_ids': approver_id_vals})

    def _get_matching_rules(self, request):
        """
        Tìm tất cả rule phù hợp dựa trên condition_field, condition_operator, condition_value
        
        Ví dụ:
        - Rule: amount >= 20000000 → CFO
        - Rule: amount >= 100000000 → CEO
        
        Nếu amount = 100000000:
        - Trùng rule 1 (>= 20000000) → thêm CFO
        - Trùng rule 2 (>= 100000000) → thêm CEO
        """
        matching_rules = self.env['approval.category.rule']
        
        if not request.amount:
            return matching_rules

        for rule in request.category_id.rule_ids:
            if rule.condition_field == 'amount':
                if self._evaluate_condition(request.amount, rule.condition_operator, rule.condition_value):
                    matching_rules |= rule

        return matching_rules.sorted(key=lambda r: r.sequence)

    @staticmethod
    def _evaluate_condition(value, operator, condition_value):
        """
        Đánh giá điều kiện
        value: giá trị cần kiểm tra (ví dụ: amount)
        operator: >, >=, <, <=, =
        condition_value: giá trị so sánh
        """
        if operator == '>':
            return value > condition_value
        elif operator == '>=':
            return value >= condition_value
        elif operator == '<':
            return value < condition_value
        elif operator == '<=':
            return value <= condition_value
        elif operator == '=':
            return value == condition_value
        return False

    # === Auto-create HR Expense on Approval ===
    def action_approve(self, approver=None):
        """Override to auto-create expense when advance claim approved"""
        result = super().action_approve(approver=approver)
        
        # Auto-create expense for approved advance claims
        for request in self:
            if request.is_advance_claim == 'yes' and request.request_status == 'approved':
                request._create_hr_expense()
        
        return result

    def _create_hr_expense(self):
        """Create hr.expense from approved advance claim"""
        self.ensure_one()
        
        # Get product ID 2 (Accommodation)
        product = self.env['product.product'].search([('id', '=', 2)], limit=1)
        if not product:
            _logger.warning(f"Product ID 2 not found for advance claim {self.name}")
            return
        
        # Create expense
        expense_vals = {
            'name': f"Advance: {self.name}",
            'product_id': product.id,
            'employee_id': self.employee_id.id,
            'payment_mode': self.payment_mode,
            'total_amount_currency': self.amount,
            'payment_method_line_id': self.payment_method_line_id.id if self.payment_method_line_id else False,
            'date': fields.Date.today(),
            'advance_request_id': self.id,  # Link back to approval request
        }
        
        expense = self.env['hr.expense'].create(expense_vals)
        _logger.info(f"Created expense {expense.id} for advance claim {self.name}")
        
        return expense

    def action_view_expenses(self):
        """Open linked expenses"""
        self.ensure_one()
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Expenses'),
            'res_model': 'hr.expense',
            'view_mode': 'list,form',
            'domain': [('id', 'in', self.expense_ids.ids)],
            'context': {
                'default_advance_request_id': self.id,
                'default_employee_id': self.employee_id.id,
            }
        }

