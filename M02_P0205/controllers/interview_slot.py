# -*- coding: utf-8 -*-
from datetime import timezone
from zoneinfo import ZoneInfo

from odoo import fields, http, _
from odoo.http import request


ROUND_DATE_FIELD_MAP = {
    '1': 'x_psm_0205_interview_date_1',
    '2': 'x_psm_0205_interview_date_2',
    '3': 'x_psm_0205_interview_date_3',
    '4': 'x_psm_0205_interview_date_4',
}

ROUND_SLOT_EVENT_FIELD_MAP = {
    '1': 'x_psm_0205_interview_slot_event_id_1',
    '2': 'x_psm_0205_interview_slot_event_id_2',
    '3': 'x_psm_0205_interview_slot_event_id_3',
    '4': 'x_psm_0205_interview_slot_event_id_4',
}


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

        # Validate that the event has a valid interview round
        event_round = event.x_psm_0205_interview_round
        if not event_round or event_round not in ('1', '2', '3', '4'):
            return request.render('M02_P0205.psm_interview_slot_invalid')

        # Map round to the correct fields
        date_field = ROUND_DATE_FIELD_MAP.get(event_round)
        slot_event_field = ROUND_SLOT_EVENT_FIELD_MAP.get(event_round)
        if not date_field or not slot_event_field:
            return request.render('M02_P0205.psm_interview_slot_invalid')

        # Update round-specific date and slot event
        applicant.write({
            date_field: event.start,
            slot_event_field: event.id,
            'x_psm_0205_interview_slot_event_id': event.id,  # keep legacy field in sync
        })

        # Create confirmation activity for internal users
        round_label = f"Interview {event_round}"
        event_time_display = self._format_event_start_for_display(event)
        partner_name = applicant.partner_name or applicant.display_name or 'ứng viên'
        activity_summary = f"Ứng viên đã xác nhận lịch {round_label}"
        activity_note = (
            f"Ứng viên {partner_name} đã xác nhận lịch phỏng vấn {round_label} "
            f"vào lúc {event_time_display}."
        )
        try:
            activity_type = request.env.ref('mail.mail_activity_data_todo', raise_if_not_found=False)
            responsible_user = applicant.user_id or applicant.job_id.user_id
            if activity_type and responsible_user:
                applicant.activity_schedule(
                    act_type_xmlid='mail.mail_activity_data_todo',
                    summary=activity_summary,
                    note=activity_note,
                    user_id=responsible_user.id,
                )
        except Exception:
            pass  # Activity creation is best-effort, must not block slot confirmation

        return request.render('M02_P0205.psm_interview_slot_confirm', {
            'applicant': applicant,
            'event': event,
            'event_start_display': event_time_display,
        })
