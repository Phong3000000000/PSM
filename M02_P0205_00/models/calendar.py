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
