# -*- coding: utf-8 -*-
from odoo import models, fields


class HrDisciplineRejectWizard(models.TransientModel):
    _name = "hr.discipline.reject.wizard"
    _description = "Reject Explanation Wizard"

    record_id = fields.Many2one("hr.discipline.record", required=True)
    rejection_reason = fields.Text(string="Lý do từ chối", required=True)

    def action_confirm_reject(self):
        """Confirm rejection and send email to employee"""
        self.ensure_one()
        record = self.record_id

        # Mark current explanation as rejected
        if record.active_explanation_id:
            record.active_explanation_id.write(
                {
                    "state": "rejected",
                    "rejection_reason": self.rejection_reason,
                    "reviewed_date": fields.Datetime.now(),
                    "reviewed_by": self.env.uid,
                }
            )

        # Change record state back to waiting
        record.state = "waiting_explanation"

        # Send rejection email
        template = self.env.ref(
            "M02_P0215_00.email_template_explanation_rejected",
            raise_if_not_found=False,
        )
        if template:
            template.with_context(rejection_reason=self.rejection_reason).send_mail(
                record.id, force_send=True
            )

        # Create activity for employee
        if record.employee_id.user_id:
            record.activity_schedule(
                "mail.mail_activity_data_todo",
                user_id=record.employee_id.user_id.id,
                summary="Yêu cầu viết lại tường trình",
                note=f"Tường trình của bạn đã bị từ chối. Lý do: {self.rejection_reason}",
            )

        # Post message to chatter
        record.message_post(
            body=f"<strong>Tường trình đã bị từ chối</strong><br/>Lý do: {self.rejection_reason}",
            subject="Explanation Rejected",
        )

        return {"type": "ir.actions.act_window_close"}
