# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request


class SurveyInterviewSlotController(http.Controller):
    """Realtime slot status endpoint used by survey page question Q14."""

    @http.route(
        '/recruitment/interview/slot_status/<string:survey_token>/<string:answer_token>',
        type='http', auth='public', website=True, csrf=False
    )
    def interview_slot_status(self, survey_token, answer_token, **kwargs):
        survey = request.env['survey.survey'].sudo().search([
            ('access_token', '=', survey_token)
        ], limit=1)
        user_input = request.env['survey.user_input'].sudo().search([
            ('survey_id', '=', survey.id),
            ('access_token', '=', answer_token),
        ], limit=1)
        applicant = request.env['hr.applicant'].sudo().search([
            ('survey_user_input_id', '=', user_input.id)
        ], limit=1)

        payload = {
            'ok': False,
            'schedule_id': False,
            'remaining': {'1': 0, '2': 0, '3': 0},
            'max_candidates': {'1': 0, '2': 0, '3': 0},
        }

        if applicant and applicant.interview_schedule_id:
            schedule = applicant.interview_schedule_id.sudo()
            remaining = schedule._get_slot_remaining_map()
            payload.update({
                'ok': True,
                'schedule_id': schedule.id,
                'remaining': {
                    '1': remaining.get(1, 0),
                    '2': remaining.get(2, 0),
                    '3': remaining.get(3, 0),
                },
                'max_candidates': {
                    '1': schedule.max_candidates_slot_1,
                    '2': schedule.max_candidates_slot_2,
                    '3': schedule.max_candidates_slot_3,
                },
            })

        return request.make_json_response(payload)
