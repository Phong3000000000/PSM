# -*- coding: utf-8 -*-
from odoo import api, fields, models, _

from .interview_round import INTERVIEW_ROUND_SELECTION


class CalendarEvent(models.Model):
    _inherit = 'calendar.event'

    @api.model
    def default_get(self, fields_list):
        context = dict(self.env.context)
        default_partner_ids = list(context.get('default_partner_ids') or [])

        creator_partner = self.env.user.partner_id
        if creator_partner and creator_partner.id not in default_partner_ids:
            default_partner_ids.append(creator_partner.id)

        applicant_id = context.get("default_applicant_id")
        interview_round = context.get("default_x_psm_0205_interview_round")

        if applicant_id and interview_round in ("1", "2", "3", "4"):
            applicant = self.env["hr.applicant"].browse(applicant_id)
            if applicant.exists():
                primary_user = applicant._get_primary_interviewer_user(interview_round)
                primary_partner = primary_user.partner_id if primary_user else False
                if primary_partner and primary_partner.id not in default_partner_ids:
                    default_partner_ids.append(primary_partner.id)

        context['default_partner_ids'] = default_partner_ids
        return super(CalendarEvent, self.with_context(context)).default_get(fields_list)

    x_psm_0205_round2_notification_sent = fields.Boolean(
        string='Thong bao vong 2 da gui',
        copy=False,
    )

    x_psm_0205_round3_notification_sent = fields.Boolean(
        string='Thong bao vong 3 da gui',
        copy=False,
    )

    x_psm_0205_round4_notification_sent = fields.Boolean(
        string='Thong bao vong 4 da gui',
        copy=False,
    )

    x_psm_0205_interview_round = fields.Selection(
        INTERVIEW_ROUND_SELECTION,
        string=_('Vong phong van'),
        help=_('Ghi nhan vong phong van ma lich nay thuoc ve.'),
        index=True,
    )
