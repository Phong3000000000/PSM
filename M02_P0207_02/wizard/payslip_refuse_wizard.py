# -*- coding: utf-8 -*-
from odoo import models, fields, api, _


class PayslipRefuseWizard(models.TransientModel):
    _name = 'payslip.refuse.wizard'
    _description = 'Payslip Refuse Reason Wizard'

    payslip_id = fields.Many2one('hr.payslip', string='Payslip', required=True)
    reason = fields.Text(string='Refusal Reason', required=True)

    def action_confirm_refuse(self):
        self.ensure_one()
        payslip = self.payslip_id
        payslip.write({
            'x_approval_state': 'refused',
            'x_refusal_reason': self.reason,
            'state': 'draft',  # Reset payslip back to draft
        })
        # Log the reason in chatter
        payslip.message_post(
            body=_('Payslip refused. Reason: %s') % self.reason,
            message_type='notification',
        )

        # Reset the employee's Attendance Sheet back to draft so attendance can be re-confirmed
        attendance_sheets = self.env['hr.attendance.sheet'].search([
            ('employee_id', '=', payslip.employee_id.id),
            ('start_date', '<=', payslip.date_to),
            ('end_date', '>=', payslip.date_from),
        ])
        if attendance_sheets:
            # Delete draft work entries so they can be regenerated cleanly
            self.env['hr.work.entry'].search([
                ('employee_id', '=', payslip.employee_id.id),
                ('date', '>=', payslip.date_from),
                ('date', '<=', payslip.date_to),
                ('state', '=', 'draft'),
            ]).unlink()
            attendance_sheets.write({'state': 'draft'})
            attendance_sheets.message_post(
                body=_('Attendance Sheet reset to draft. Payslip was refused. Reason: %s') % self.reason,
                message_type='notification',
            )

        # Check if all payslips in the run are now handled (none pending)
        payslip._check_all_payslips_done()
        return {'type': 'ir.actions.act_window_close'}

