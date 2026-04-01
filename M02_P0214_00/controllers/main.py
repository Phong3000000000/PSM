# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request


class PortalResignationRST(http.Controller):
    @http.route(["/my/resignation"], type="http", auth="user", website=True)
    def portal_resignation_unified(self, **kw):
        """
        Unified resignation route - redirects based on is_rst_employee flag.
        If is_rst_employee=True → /my/resignation/rst (RST form)
        If is_rst_employee=False → /my/resignation/ops (OPS form from module 0213)
        """
        employee = request.env['hr.employee'].sudo().search([
            '|',
            ('user_id', '=', request.env.user.id),
            ('work_contact_id', '=', request.env.user.partner_id.id)
        ], limit=1)
        
        # Determine destination based on is_rst_employee field
        if employee and employee.is_rst_employee:
            return request.redirect("/my/resignation/rst")
        else:
            # Non-RST employees go to OPS form (module 0213)
            return request.redirect("/my/resignation/ops")

    @http.route(["/my/resignation/rst"], type="http", auth="user", website=True)
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
        category = request.env.ref("M02_P0214_00.approval_category_resignation").sudo()
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
                survey = request.env.ref("M02_P0214_00.survey_exit_interview", raise_if_not_found=False).sudo()
                if survey:
                    user_input = request.env["survey.user_input"].sudo().search([
                        ("survey_id", "=", survey.id),
                        ("partner_id", "=", request.env.user.partner_id.id),
                    ], order="create_date desc", limit=1)
                    if user_input:
                        survey_url = user_input.get_start_url()

        # Kiểm tra xem có vừa gửi thành công không
        success = kw.get('success')

        # Lấy danh sách lý do nghỉ việc để hiển thị trên form
        resignation_types = request.env['hr.departure.reason'].sudo().search([])
        import logging
        _logger = logging.getLogger(__name__)
        _logger.warning(f"DEBUG PORTAL: Found {len(resignation_types)} departure reasons: {resignation_types.mapped('name')}")

        return request.render(
            "M02_P0214_00.resignation_portal_template",
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

    @http.route(["/my/resignation/rst/activity/done"], type="http", auth="user", methods=["POST"], website=True, csrf=True)
    def portal_activity_done(self, **post):
        """
        Đánh dấu hoàn thành công việc từ Portal
        """
        activity_id = int(post.get('activity_id', 0))
        if not activity_id:
            return request.redirect("/my/resignation/rst")

        activity = request.env['mail.activity'].sudo().browse(activity_id)
        
        # Kiểm tra tính hợp lệ: Activity phải thuộc về user hiện tại và liên quan đến đơn nghỉ việc của họ
        if activity.exists() and activity.user_id == request.env.user:
            # Thực hiện Mark Done
            activity.sudo().action_feedback(feedback="Hoàn thành từ Portal")
            
        return request.redirect("/my/resignation/rst?activity_done=1")

    @http.route(
        ["/my/resignation/rst/submit"],
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
        category = request.env.ref("M02_P0214_00.approval_category_resignation").sudo()

        # Chuẩn bị dữ liệu
        vals = {
            "name": f"Yêu cầu nghỉ việc - {partner.name}",
            "category_id": category.id,
            "partner_id": partner.id,
            "resignation_reason_id": int(post.get("resignation_type_id")) if post.get("resignation_type_id") else False,
            "resignation_reason": post.get("resignation_reason"),
            "resignation_date": post.get("resignation_date"),
            "employee_id": employee.id if employee else False,
            "request_owner_id": request.env.user.id,
        }

        if employee and employee.parent_id and employee.parent_id.user_id:
            vals["approver_ids"] = [
                (
                    0,
                    0,
                    {
                        "user_id": employee.parent_id.user_id.id,
                        "status": "new",  # Start as 'new' so action_confirm() can process
                        "required": True,
                    },
                 )
            ]

        # Tạo approval request (giữ ở trạng thái "To Submit")
        approval_request = request.env["approval.request"].sudo().create(vals)

        # Tự động confirm để chuyển sang trạng thái Submitted (pending)
        approval_request.sudo().action_confirm()

        return request.redirect("/my/resignation/rst?success=1")
