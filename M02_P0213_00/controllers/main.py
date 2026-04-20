# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request



class PortalResignation(http.Controller):
    def _get_portal_employee(self):
        return (
            request.env["hr.employee"]
            .sudo()
            .search([
                '|',
                ("user_id", "=", request.env.user.id),
                ("work_contact_id", "=", request.env.user.partner_id.id),
            ], limit=1)
        )

    def _get_resignation_category(self):
        return request.env.ref(
            "M02_P0213_00.psm_0213_approval_category_resignation"
        ).sudo()

    def _get_latest_resignation_request(self, category):
        return request.env["approval.request"].sudo().search([
            ("request_owner_id", "=", request.env.user.id),
            ("category_id", "=", category.id),
        ], order="create_date desc", limit=1)

    def _get_owned_resignation_request_by_id(self, request_id):
        category = self._get_resignation_category()
        return request.env["approval.request"].sudo().search([
            ("id", "=", request_id),
            ("request_owner_id", "=", request.env.user.id),
            ("category_id", "=", category.id),
        ], limit=1)

    def _get_resignation_types(self):
        return request.env["hr.departure.reason"].sudo().search([])

    def _get_resignation_activities(self, resignation_request):
        return request.env["mail.activity"].sudo().with_context(active_test=False).search([
            ("active", "in", [True, False]),
            ("res_model", "=", "approval.request"),
            ("res_id", "=", resignation_request.id),
        ], order="date_deadline asc")

    def _get_or_create_exit_survey_url(self, resignation_request):
        if (
            not resignation_request
            or resignation_request.request_status not in ["approved", "done"]
            or resignation_request.x_psm_0213_exit_survey_completed
        ):
            return False

        survey = request.env.ref(
            "M02_P0213_00.psm_0213_survey_exit_interview",
            raise_if_not_found=False,
        )
        survey = survey.sudo() if survey else False
        if not survey:
            return False

        partner = request.env.user.partner_id
        user_input = request.env["survey.user_input"].sudo().search([
            ("survey_id", "=", survey.id),
            ("partner_id", "=", partner.id),
        ], order="create_date desc", limit=1)

        if not user_input:
            user_input = request.env["survey.user_input"].sudo().create({
                "survey_id": survey.id,
                "partner_id": partner.id,
                "email": partner.email,
            })
            if not resignation_request.x_psm_0213_exit_survey_user_input_id:
                resignation_request.sudo().write({
                    "x_psm_0213_exit_survey_user_input_id": user_input.id,
                })

        return user_input.get_start_url()

    @http.route(["/my/resignation/ops"], type="http", auth="user", website=True)
    def portal_resignation_form(self, **kw):
        """
        Hiển thị form yêu cầu nghỉ việc hoặc trạng thái đơn đang xử lý.
        """
        partner = request.env.user.partner_id
        employee = self._get_portal_employee()
        category = self._get_resignation_category()
        resignation_request = self._get_latest_resignation_request(category)

        activities = []
        survey_url = False
        if resignation_request:
            activities = self._get_resignation_activities(resignation_request)
            survey_url = self._get_or_create_exit_survey_url(resignation_request)

        return request.render(
            "M02_P0213_00.view_psm_0213_resignation_portal_template",
            {
                "partner": partner,
                "employee": employee,
                "success": kw.get("success"),
                "resignation_request": resignation_request,
                "activities": activities,
                "survey_url": survey_url,
                "resignation_types": self._get_resignation_types(),
            },
        )

    @http.route(
        ["/my/resignation/ops/activity/done"],
        type="http",
        auth="user",
        methods=["POST"],
        website=True,
        csrf=True,
    )
    def portal_activity_done(self, **post):
        """
        Đánh dấu hoàn thành công việc từ Portal.
        """
        activity_id = int(post.get("activity_id", 0))
        if not activity_id:
            return request.redirect("/my/resignation/ops")

        activity = request.env["mail.activity"].sudo().browse(activity_id)
        owned_request = False
        if activity.exists() and activity.res_model == "approval.request":
            owned_request = self._get_owned_resignation_request_by_id(activity.res_id)

        if owned_request and activity.user_id == request.env.user:
            activity.sudo().action_feedback(feedback="Hoàn thành từ Portal")

        return request.redirect("/my/resignation/ops?success=1")

    @http.route(
        ["/my/resignation/submit"],
        type="http",
        auth="user",
        methods=["POST"],
        website=True,
        csrf=True,
    )
    def portal_resignation_submit(self, **post):
        """
        Xử lý submit yêu cầu nghỉ việc.
        """
        partner = request.env.user.partner_id
        employee = self._get_portal_employee()
        category = self._get_resignation_category()

        vals = {
            "name": f"Yêu cầu nghỉ việc - {partner.name}",
            "category_id": category.id,
            "partner_id": partner.id,
            "x_psm_0213_resignation_reason_id": (
                int(post.get("resignation_type_id"))
                if post.get("resignation_type_id")
                else False
            ),
            "x_psm_0213_resignation_reason": post.get("resignation_reason"),
            "x_psm_0213_resignation_date": post.get("resignation_date") or False,
            "x_psm_0213_employee_id": employee.id if employee else False,
            "request_owner_id": request.env.user.id,
        }

        if employee and employee.parent_id and employee.parent_id.user_id:
            vals["approver_ids"] = [
                (
                    0,
                    0,
                    {
                        "user_id": employee.parent_id.user_id.id,
                        "status": "new",
                        "required": True,
                    },
                )
            ]

        approval_request = request.env["approval.request"].sudo().create(vals)
        approval_request.sudo().action_confirm()

        return request.redirect("/my/resignation/ops?success=1")
