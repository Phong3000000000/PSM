# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request
import logging

_logger = logging.getLogger(__name__)


class PortalResignation(http.Controller):
    @http.route(["/my/resignation/ops"], type="http", auth="user", website=True)
    def portal_resignation_form(self, **kw):
        """
        Hiển thị form yêu cầu nghỉ việc hoặc Trạng thái đơn đang xử lý
        """
        partner = request.env.user.partner_id
        employee = (
            request.env["hr.employee"]
            .sudo()
            .search([
                '|',
                ("user_id", "=", request.env.user.id),
                ("work_contact_id", "=", request.env.user.partner_id.id)
            ], limit=1)
        )

        # Tìm đơn nghỉ việc gần nhất của User này
        category = request.env.ref("M02_P0213_00.approval_category_resignation").sudo()
        resignation_request = request.env['approval.request'].sudo().search([
            ('request_owner_id', '=', request.env.user.id),
            ('category_id', '=', category.id)
        ], order='create_date desc', limit=1)

        activities = []
        survey_url = False
        if resignation_request:
            # Lấy chỉ Approval activity từ resignation request (không lấy từ hr.employee)
            # Sử dụng with_context(active_test=False) và domain explicit để lấy cả các mục đã xong
            activities = request.env['mail.activity'].sudo().with_context(active_test=False).search([
                ('active', 'in', [True, False]),
                ('res_model', '=', 'approval.request'), 
                ('res_id', '=', resignation_request.id),
            ], order='date_deadline asc')
            
            # Lấy Link Khảo sát Exit Interview nếu chưa hoàn thành
            if resignation_request.request_status in ['approved', 'done'] and not resignation_request.exit_survey_completed:
                survey = request.env.ref("M02_P0213_00.survey_exit_interview", raise_if_not_found=False).sudo()
                if survey:
                    partner = request.env.user.partner_id
                    user_input = request.env["survey.user_input"].sudo().search([
                        ("survey_id", "=", survey.id),
                        ("partner_id", "=", partner.id),
                    ], order="create_date desc", limit=1)
                    # Tự động tạo user_input nếu chưa có (HR chưa gửi email khảo sát)
                    if not user_input:
                        user_input = request.env["survey.user_input"].sudo().create({
                            "survey_id": survey.id,
                            "partner_id": partner.id,
                            "email": partner.email,
                        })
                        if not resignation_request.exit_survey_user_input_id:
                            resignation_request.sudo().write({"exit_survey_user_input_id": user_input.id})
                    survey_url = user_input.get_start_url()
        

        # Kiểm tra xem có vừa gửi thành công không
        success = kw.get('success')

        # Lấy danh sách lý do nghỉ việc để hiển thị trên form
        resignation_types = request.env['hr.departure.reason'].sudo().search([])

        return request.render(
            "M02_P0213_00.resignation_portal_template",
            {
                "partner": partner,
                "employee": employee,
                "success": success,
                "resignation_request": resignation_request,
                "activities": activities,
                "survey_url": survey_url,
                "resignation_types": resignation_types,
            },
        )

    @http.route(["/my/resignation/ops/activity/done"], type="http", auth="user", methods=["POST"], website=True, csrf=True)
    def portal_activity_done(self, **post):
        """
        Đánh dấu hoàn thành công việc từ Portal
        """
        activity_id = int(post.get('activity_id', 0))
        if not activity_id:
            return request.redirect("/my/resignation/ops")

        activity = request.env['mail.activity'].sudo().browse(activity_id)

        # Kiểm tra tính hợp lệ: Activity phải thuộc về user hiện tại
        if activity.exists() and activity.user_id == request.env.user:
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
        Xử lý submit yêu cầu nghỉ việc
        """
        partner = request.env.user.partner_id
        employee = (
            request.env["hr.employee"]
            .sudo()
            .search([
                '|',
                ("user_id", "=", request.env.user.id),
                ("work_contact_id", "=", request.env.user.partner_id.id)
            ], limit=1)
        )

        # Lấy category nghỉ việc - sử dụng sudo() để bypass quyền đọc category portal
        category = request.env.ref("M02_P0213_00.approval_category_resignation").sudo()

        # Chuẩn bị dữ liệu
        vals = {
            "name": f"Yêu cầu nghỉ việc - {partner.name}",
            "category_id": category.id,
            "partner_id": partner.id,
            "resignation_reason_id": int(post.get("resignation_type_id")) if post.get("resignation_type_id") else False,
            "resignation_reason": post.get("resignation_reason"),
            "resignation_date": post.get("resignation_date") or False,
            "employee_id": employee.id if employee else False,
            "request_owner_id": request.env.user.id,
        }

        # Thêm Line Manager làm người duyệt
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

        # Tạo approval request (giữ ở trạng thái "To Submit")
        approval_request = request.env["approval.request"].sudo().create(vals)

        # Tự động confirm để chuyển sang trạng thái Submitted (pending)
        approval_request.sudo().action_confirm()

        return request.redirect("/my/resignation/ops?success=1")
