from odoo import models, api
import logging

_logger = logging.getLogger(__name__)


class SurveyUserInput(models.Model):
    _inherit = "survey.user_input"

    def write(self, vals):
        res = super(SurveyUserInput, self).write(vals)
        if "state" in vals and vals["state"] == "done":
            self._check_and_mark_exit_interview_done()
        return res

    def _check_and_mark_exit_interview_done(self):
        # Activity Summary to find
        ACTIVITY_SUMMARY = "Hoàn thành Exit Interview"

        exit_survey = self.env.ref(
            "M02_P0214_00.survey_exit_interview", raise_if_not_found=False
        )

        for user_input in self:
            # Check if this is the exit survey
            if exit_survey and user_input.survey_id == exit_survey:
                # Find employee linked to this participant
                employee = False
                if user_input.partner_id:
                    employee = self.env["hr.employee"].search(
                        [("work_contact_id", "=", user_input.partner_id.id)], limit=1
                    )
                    if not employee:
                        # Fallback: check if partner is user's partner
                        user = self.env["res.users"].search(
                            [("partner_id", "=", user_input.partner_id.id)], limit=1
                        )
                        if user:
                            employee = self.env["hr.employee"].search(
                                [("user_id", "=", user.id)], limit=1
                            )
                elif user_input.email:
                    # Fallback by email
                    employee = self.env["hr.employee"].search(
                        [("work_email", "=", user_input.email)], limit=1
                    )

                if employee:
                    # Find and mark activity done
                    activities = self.env["mail.activity"].search(
                        [
                            ("res_model", "=", "hr.employee"),
                            ("res_id", "=", employee.id),
                            ("summary", "=", ACTIVITY_SUMMARY),
                            ("active", "=", True),  # Only active ones
                        ]
                    )
                    # Fix: use action_done() correctly
                    if activities:
                        # action_done returns/handles feedback and archiving
                        activities.action_done()
                    
                    # === AUTO SEND BHXH EMAIL ===
                    # Tìm resignation request của nhân viên
                    rst_category = self.env.ref("M02_P0214_00.approval_category_resignation", raise_if_not_found=False)
                    if rst_category:
                        resignation_request = self.env['approval.request'].search([
                            ('employee_id', '=', employee.id),
                            ('category_id', '=', rst_category.id),
                            ('request_status', '=', 'approved'),
                        ], order='create_date desc', limit=1)
                        
                        if resignation_request:
                            # Kiểm tra cách khác: tự đếm xem còn bao nhiêu activity active
                            pending_count = self.env['mail.activity'].search_count([
                                ('active', '=', True),
                                '|',
                                '&', ('res_model', '=', 'approval.request'), ('res_id', '=', resignation_request.id),
                                '&', ('res_model', '=', 'hr.employee'), ('res_id', '=', employee.id),
                            ])
                            
                            # Gửi email BHXH nếu:
                            # 1. Exit Interview hoàn thành (cái này đang là True vì survey.state='done')
                            # 2. Tất cả công việc Offboarding hoàn thành (pending_count == 0)
                            if pending_count == 0:
                                try:
                                    resignation_request.action_send_social_insurance()
                                except Exception as e:
                                    _logger.warning(f"Failed to auto-send BHXH email for resignation request {resignation_request.id}: {str(e)}")
