# -*- coding: utf-8 -*-

from odoo import models, fields, api


class SalaryIncreasePlanLine(models.Model):
    _name = 'salary.increase.plan.line'
    _description = 'Salary Increase Plan Line'
    _order = 'performance_rating desc, employee_id'
    
    employee_id = fields.Many2one(
        'hr.employee',
        string='Employee',
        required=True,
        readonly=True
    )
    
    department_id = fields.Many2one(
        'hr.department',
        string='Department',
        related='employee_id.department_id',
        store=True,
        readonly=True
    )
    
    job_id = fields.Many2one(
        'hr.job',
        string='Job Position',
        related='employee_id.job_id',
        store=True,
        readonly=True
    )
    
    appraisal_id = fields.Many2one(
        'hr.appraisal',
        string='Appraisal',
        readonly=True
    )
    
    performance_rating = fields.Float(
        string='Performance Rating',
        readonly=True,
        digits=(3, 2)
    )
    
    assessment_note = fields.Char(
        string='Final Rating',
        readonly=True
    )
    
    increase_percentage = fields.Float(
        string='Salary Increase (%)',
        digits=(5, 2),
        group_operator='avg'
    )

    increase_percentage_final = fields.Float(
        string='Final Salary Increase (%)',
        digits=(5, 2),
        group_operator='avg',
        help='Final approved salary increase percentage. Pre-filled from recommended value and can be adjusted.'
    )

    old_wage = fields.Monetary(
        string='Mức lương cũ',
        currency_field='currency_id',
        readonly=True,
        help='Mức lương trước khi tăng'
    )
    
    new_wage = fields.Monetary(
        string='Mức lương mới',
        currency_field='currency_id',
        readonly=True,
        help='Mức lương sau khi tăng'
    )

    is_applied = fields.Boolean(
        string='Đã áp dụng',
        default=False,
        readonly=True,
        help='Đánh dấu trạng thái lương mới đã được cập nhật vào hồ sơ nhân viên hay chưa'
    )

    wage_difference = fields.Monetary(
        string='Mức tăng',
        currency_field='currency_id',
        compute='_compute_wage_difference',
        store=True,
        help='Chênh lệch giữa lương mới và lương cũ'
    )

    @api.depends('old_wage', 'new_wage')
    def _compute_wage_difference(self):
        for rec in self:
            if rec.old_wage and rec.new_wage:
                rec.wage_difference = rec.new_wage - rec.old_wage
            else:
                rec.wage_difference = 0.0

    currency_id = fields.Many2one(
        'res.currency',
        related='employee_id.company_id.currency_id',
        string='Currency',
        readonly=True
    )

    @api.onchange('increase_percentage')
    def _onchange_increase_percentage(self):
        for rec in self:
            if not rec.increase_percentage_final:
                rec.increase_percentage_final = rec.increase_percentage
    
    create_date = fields.Datetime(
        string='Generated On',
        readonly=True
    )
    
    approval_request_id = fields.Many2one(
        'approval.request',
        string='Approval Request',
        readonly=True
    )

    plan_type = fields.Selection([
        ('ops', 'OPS'),
        ('rst', 'RST'),
    ], string='Plan Type', default='ops',
       help='Type of salary increase plan: OPS (Store departments) or RST (Non-store departments)'
    )
    
    @api.model
    def action_generate_plan(self):
        """Generate salary increase plan lines from appraisals."""
        
        # Delete only OPS lines to refresh (keep RST lines intact)
        self.search([('plan_type', '=', 'ops')]).unlink()
        
        # Get only OPS appraisals (is_performance_manager_ops = True) with performance rating
        appraisals = self.env['hr.appraisal'].search([
            ('performance_rating', '>', 0),
            ('is_performance_manager_ops', '=', True),
        ])
        
        # Create plan lines
        for appraisal in appraisals:
            employee = appraisal.employee_id
            if not employee:
                continue
            
            # Get recommended increase percentage from config
            increase_pct = self.env['salary.increase.config'].get_increase_for_rating(
                appraisal.performance_rating
            )
            
            self.create({
                'employee_id': employee.id,
                'appraisal_id': appraisal.id,
                'performance_rating': appraisal.performance_rating,
                'assessment_note': appraisal.assessment_note.name if appraisal.assessment_note else '',
                'increase_percentage': increase_pct,
                'increase_percentage_final': increase_pct,
                'plan_type': 'ops',
            })
        
        # Return action to show the list view filtered by OPS
        return {
            'type': 'ir.actions.act_window',
            'name': 'Salary Increase Plan (OPS)',
            'res_model': 'salary.increase.plan.line',
            'view_mode': 'list,form',
            'domain': [('plan_type', '=', 'ops')],
            'target': 'current',
            'context': self.env.context,
        }
    
    def action_submit_to_approval(self):
        """Submit salary increase plan to approval workflow."""
        # Get only OPS lines
        lines = self.search([('plan_type', '=', 'ops')])
        
        if not lines:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': 'No OPS salary increase plan found. Please generate a plan first.',
                    'type': 'warning',
                    'sticky': False,
                }
            }
        
        # Build HTML table for approval request description
        html_content = """
        <div style="font-family: Arial, sans-serif;">
            <h3>Salary Increase Plan (OPS)</h3>
            <p>Total Employees: <strong>%s</strong></p>
            <p>Average Increase: <strong>%.2f%%</strong></p>
            <br/>
            <table style="border-collapse: collapse; width: 100%%;">
                <thead>
                    <tr style="background-color: #f2f2f2;">
                        <th style="border: 1px solid #ddd; padding: 8px; text-align: left;">Employee</th>
                        <th style="border: 1px solid #ddd; padding: 8px; text-align: left;">Department</th>
                        <th style="border: 1px solid #ddd; padding: 8px; text-align: left;">Job</th>
                        <th style="border: 1px solid #ddd; padding: 8px; text-align: center;">Performance Rating</th>
                        <th style="border: 1px solid #ddd; padding: 8px; text-align: left;">Final Rating</th>
                        <th style="border: 1px solid #ddd; padding: 8px; text-align: right;">Salary Increase (%%)</th>
                    </tr>
                </thead>
                <tbody>
                    %s
                </tbody>
            </table>
        </div>
        """ % (
            len(lines),
            sum(lines.mapped('increase_percentage_final')) / len(lines) *100 if lines else 0,
            ''.join([
                """
                <tr>
                    <td style="border: 1px solid #ddd; padding: 8px;">%s</td>
                    <td style="border: 1px solid #ddd; padding: 8px;">%s</td>
                    <td style="border: 1px solid #ddd; padding: 8px;">%s</td>
                    <td style="border: 1px solid #ddd; padding: 8px; text-align: center;">%.2f</td>
                    <td style="border: 1px solid #ddd; padding: 8px;">%s</td>
                    <td style="border: 1px solid #ddd; padding: 8px; text-align: right;">%.2f%%</td>
                </tr>
                """ % (
                    line.employee_id.name,
                    line.department_id.name or '',
                    line.job_id.name or '',
                    line.performance_rating,
                    line.assessment_note or '',
                    line.increase_percentage_final *100
                )
                for line in lines
            ])
        )
        
        # Get approval category
        category = self.env.ref('M02_P0218_01.approval_category_salary_increase', raise_if_not_found=False)
        if not category:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': 'Approval category not found. Please check module configuration.',
                    'type': 'danger',
                    'sticky': True,
                }
            }
        
        # Create approval request
        today = fields.Date.today()
        approval_name = f'Salary Increase Plan OPS - {today}'
        approval = self.env['approval.request'].create({
            'name': approval_name,
            'category_id': category.id,
            'request_owner_id': self.env.user.id,
            'reason': html_content,
            'date': fields.Datetime.now(),
        })
        # Force the name after creation because approval.request.create()
        # overrides name with a sequence when category.automated_sequence is True
        if approval.name != approval_name:
            approval.sudo().write({'name': approval_name})
        
        # Link approval to plan lines (for email notification later)
        lines.write({'approval_request_id': approval.id})
        
        # Submit for approval
        try:
            approval.action_confirm()
        except Exception as e:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': f'Error submitting approval: {str(e)}',
                    'type': 'danger',
                    'sticky': True,
                }
            }
        
        # Return action to open the approval request
        return {
            'type': 'ir.actions.act_window',
            'name': 'Salary Increase Approval',
            'res_model': 'approval.request',
            'res_id': approval.id,
            'view_mode': 'form',
            'target': 'current',
        }
    
    def _send_notification_email(self):
        """Send notification email to employee about salary increase approval.
        
        Returns:
            str: 'success', 'no_email', or 'failed'
        """
        self.ensure_one()
        
        # Check if employee has email
        if not self.employee_id.work_email:
            return 'no_email'
        
        # Get email template
        template = self.env.ref('M02_P0218_01.email_template_salary_increase_approved', raise_if_not_found=False)
        if not template:
            return 'failed'
        
        # Send email
        try:
            template.send_mail(self.id, force_send=True)
            return 'success'
        except Exception as e:
            return 'failed'

