"""
Extend HR Payslip for Referral Bonus Integration
"""

from odoo import models, fields, api
import logging

_logger = logging.getLogger(__name__)


class HrPayslip(models.Model):
    _inherit = 'hr.payslip'

    referral_bonus_ids = fields.One2many(
        'employee.referral.submission',
        compute='_compute_referral_bonus',
        string='Thưởng giới thiệu'
    )
    
    referral_bonus_total = fields.Float(
        compute='_compute_referral_bonus',
        string='Tổng thưởng giới thiệu'
    )
    
    @api.depends('employee_id', 'input_line_ids')
    def _compute_referral_bonus(self):
        for rec in self:
            # Find referral submissions where this employee is the referrer
            # and bonus is linked to this payslip
            submissions = self.env['employee.referral.submission'].search([
                ('referrer_id', '=', rec.employee_id.id),
                ('bonus_eligible', '=', True),
                ('payslip_input_id.payslip_id', '=', rec.id),
            ])
            
            rec.referral_bonus_ids = submissions
            rec.referral_bonus_total = sum(submissions.mapped('bonus_amount'))
    
    def action_payslip_done(self):
        """Override to mark referral bonuses as paid when payslip is done"""
        result = super().action_payslip_done()
        
        for rec in self:
            # Find and mark referral bonuses as paid
            submissions = self.env['employee.referral.submission'].search([
                ('referrer_id', '=', rec.employee_id.id),
                ('bonus_eligible', '=', True),
                ('bonus_paid', '=', False),
                ('payslip_input_id.payslip_id', '=', rec.id),
            ])
            
            if submissions:
                submissions.write({
                    'bonus_paid': True,
                    'bonus_paid_date': fields.Date.today()
                })
                
                _logger.info(f"Marked {len(submissions)} referral bonuses as paid for {rec.employee_id.name}")
        
        return result
