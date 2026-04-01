# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class CreatePerformanceAppraisalWizard(models.TransientModel):
    _name = 'create.performance.appraisal.wizard'
    _description = 'Create Performance Manager OPS Appraisals'

    department_id = fields.Many2one(
        'hr.department',
        string='Department',
        required=True,
      #  default=lambda self: self.env.user.employee_id.department_id,
        help='Department to create appraisals for'
    )
    date_close = fields.Date(
        string='Appraisal Date',
        required=True,
        default=fields.Date.today,
        help='Closing date of the appraisal'
    )
    appraisal_template_id = fields.Many2one(
        'hr.appraisal.template',
        string='Appraisal Template',
        help='Template to use for the appraisals'
    )


    def action_create_appraisals(self):
        """Create appraisals for all managers in the selected department"""
        self.ensure_one()
        
        if not self.env.user.employee_id:
            raise UserError(_('You must be linked to an employee to create appraisals.'))
        
        target_job_codes = ['DM1', 'DM2', 'DM3']
        target_jobs = self.env['hr.job'].search([('code', 'in', target_job_codes)])
        
        employees = self.env['hr.employee'].search([
            ('department_id', '=', self.department_id.id),
            ('active', '=', True),
            ('job_id', 'in', target_jobs.ids)
        ])
        
        if not employees:
            raise UserError(_('No managers found in the selected department.'))
        
        created_appraisals = self.env['hr.appraisal']
        skipped_employees = []
        current_employee = self.env.user.employee_id
        
        for employee in employees:
            # Kiểm tra đã tồn tại appraisal cho nhân viên này chưa (cùng tháng/năm)
            existing = self.env['hr.appraisal'].search([
                ('employee_id', '=', employee.id),
                ('is_performance_manager_ops', '=', True),
                ('date_close', '>=', self.date_close.replace(day=1)),
                ('date_close', '<=', self.date_close),
            ], limit=1)
            
            if existing:
                skipped_employees.append(employee.name)
                continue
            
            # Create appraisal
            appraisal_vals = {
                'employee_id': employee.id,
                'manager_ids': [(6, 0, [current_employee.id])],
                'date_close': self.date_close,
                'is_performance_manager_ops': True,
            }
            
            if self.appraisal_template_id:
                appraisal_vals['appraisal_template_id'] = self.appraisal_template_id.id
            
            # if self.survey_ids:
            #     appraisal_vals['survey_ids'] = [(6, 0, self.survey_ids.ids)]
            
            appraisal = self.env['hr.appraisal'].create(appraisal_vals)
            created_appraisals |= appraisal
        
        if skipped_employees and not created_appraisals:
            raise UserError(_('Tất cả nhân viên đã có appraisal trong kỳ này: %s') % ', '.join(skipped_employees))
        
        # Return action to show created appraisals
        return {
            'type': 'ir.actions.act_window',
            'name': _('Created Appraisals'),
            'res_model': 'hr.appraisal',
            'view_mode': 'list,form',
            'domain': [('id', 'in', created_appraisals.ids)],
            'context': {
                'create': False,
            },
        }
