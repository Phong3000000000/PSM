# -*- coding: utf-8 -*-
from datetime import timezone
from zoneinfo import ZoneInfo

from odoo import fields, http
from odoo.http import request


class InterviewSlotController(http.Controller):
    def _format_event_start_for_display(self, event):
        start = fields.Datetime.to_datetime(event.start)
        if not start:
            return ''
        if start.tzinfo is None:
            start = start.replace(tzinfo=timezone.utc)
        tz_name = request.context.get('tz') or 'Asia/Ho_Chi_Minh'
        try:
            local_dt = start.astimezone(ZoneInfo(tz_name))
        except Exception:
            local_dt = start.astimezone(ZoneInfo('Asia/Ho_Chi_Minh'))
        return local_dt.strftime('%Y-%m-%d %H:%M')

    @http.route('/interview/choose/<string:token>/<int:event_id>', type='http', auth='public', website=True)
    def interview_choose(self, token, event_id, **kw):
        applicant = request.env['hr.applicant'].sudo().search([('x_psm_0205_interview_slot_token', '=', token)], limit=1)
        if not applicant:
            return request.render('M02_P0205.psm_interview_slot_invalid')

        event = request.env['calendar.event'].sudo().browse(event_id)
        if not event.exists() or event.applicant_id.id != applicant.id:
            return request.render('M02_P0205.psm_interview_slot_invalid')

        applicant.write({
            'x_psm_0205_interview_date_1': event.start,
            'x_psm_0205_interview_slot_event_id': event.id,
        })

        return request.render('M02_P0205.psm_interview_slot_confirm', {
            'applicant': applicant,
            'event': event,
            'event_start_display': self._format_event_start_for_display(event),
        })
