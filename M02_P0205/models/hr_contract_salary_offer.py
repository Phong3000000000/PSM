# -*- coding: utf-8 -*-
from odoo import models, _


class HrContractSalaryOfferP0205(models.Model):
    _inherit = 'hr.contract.salary.offer'

    # -------------------------------------------------------------------------
    # Helpers
    # -------------------------------------------------------------------------

    def _x_psm_is_office_applicant(self):
        """Return True when the offer is linked to an office applicant of M02_P0205."""
        self.ensure_one()
        applicant = self.applicant_id
        if not applicant:
            return False
        recruitment_type = (
            applicant.x_psm_0205_recruitment_type
            if 'x_psm_0205_recruitment_type' in applicant._fields
            else False
        )
        return recruitment_type == 'office'

    def _x_psm_0205_sync_applicant_to_hired(self):
        """Move the linked office applicant to stage_office_hired."""
        self.ensure_one()
        hired_stage = self.env.ref('M02_P0205.stage_office_hired', raise_if_not_found=False)
        if not hired_stage:
            return
        applicant = self.applicant_id
        if applicant and applicant.stage_id != hired_stage:
            applicant.sudo().write({'stage_id': hired_stage.id})
            applicant.sudo().message_post(
                body=_("Offer fully signed – applicant moved to Hired stage by offer #%d.") % self.id
            )

    def _x_psm_0205_sync_applicant_to_reject(self):
        """Move the linked office applicant to the Reject stage."""
        self.ensure_one()
        # Try to find the reject stage; fall back to first archived/refuse stage.
        reject_stage = self.env.ref('M02_P0205.stage_office_reject', raise_if_not_found=False)
        if not reject_stage:
            reject_stage = self.env['hr.recruitment.stage'].search(
                [('name', 'ilike', 'reject')], limit=1
            )
        if not reject_stage:
            return
        applicant = self.applicant_id
        if applicant and applicant.stage_id != reject_stage:
            applicant.sudo().write({'stage_id': reject_stage.id})
            applicant.sudo().message_post(
                body=_("Offer refused – applicant moved to Reject stage by offer #%d.") % self.id
            )

    # -------------------------------------------------------------------------
    # Override write to hook on state changes
    # -------------------------------------------------------------------------

    def write(self, vals):
        res = super().write(vals)
        if 'state' not in vals:
            return res
        new_state = vals['state']
        for offer in self:
            if not offer._x_psm_is_office_applicant():
                continue
            if new_state == 'full_signed':
                offer._x_psm_0205_sync_applicant_to_hired()
            elif new_state == 'refused':
                offer._x_psm_0205_sync_applicant_to_reject()
        return res

    # -------------------------------------------------------------------------
    # Override Send By Email — choose branded template for office applicants
    # -------------------------------------------------------------------------

    def action_send_by_email(self):
        """For office applicants of M02_P0205, load the branded offer template.
        All other context keys mirror the standard implementation exactly."""
        self.ensure_one()

        # Determine the right template ID
        if self._x_psm_is_office_applicant():
            template = self.env.ref(
                'M02_P0205.email_offer_salary_package_office',
                raise_if_not_found=False,
            )
            default_template_id = template.id if template else False
        elif self.applicant_id:
            try:
                default_template_id = self.env.ref(
                    'hr_contract_salary.mail_template_send_offer_applicant'
                ).id
            except ValueError:
                default_template_id = False
        else:
            try:
                default_template_id = self.env.ref(
                    'hr_contract_salary.mail_template_send_offer'
                ).id
            except ValueError:
                default_template_id = False

        # Build compose context — identical keys to the standard method
        ctx = {
            'default_composition_mode': 'comment',
            'default_email_layout_xmlid': 'mail.mail_notification_light',
            'default_model': 'hr.contract.salary.offer',
            'default_res_ids': self.ids,
            'default_template_id': default_template_id,
            'offer_id': self.id,
            'access_token': self.access_token,
            'validity_end': self.offer_end_date,
        }
        return {
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'mail.compose.message',
            'views': [[False, 'form']],
            'target': 'new',
            'context': ctx,
        }
