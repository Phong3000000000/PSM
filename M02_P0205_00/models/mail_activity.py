# -*- coding: utf-8 -*-
from odoo import models


class MailActivity(models.Model):
    _inherit = "mail.activity"

    def action_done(self, *args, **kwargs):
        applicants_to_mark = []
        for activity in self:
            if activity.res_model == "hr.applicant" and activity.res_id:
                summary = (activity.summary or "").upper()
                if "CV" in summary and "PASS" in summary:
                    applicants_to_mark.append(activity.res_id)

        res = super().action_done(*args, **kwargs)

        if applicants_to_mark:
            self.env["hr.applicant"].browse(applicants_to_mark).sudo().write({
                "cv_checked": True,
            })
        return res
