# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)


class ApprovalCategory(models.Model):
    _inherit = 'approval.category'

    is_offboarding = fields.Boolean(
        string='Is Offboarding',
        default=False,
        help='Đánh dấu category này là yêu cầu nghỉ việc (offboarding)'
    )


class ResignationRequest(models.Model):
    _inherit = "approval.request"

    # === Resignation Fields ===
    resignation_reason = fields.Text(string="Lý do nghỉ việc")
    resignation_reason_id = fields.Many2one("hr.departure.reason", string="Loại nghỉ việc")
    resignation_date = fields.Date(string="Ngày nghỉ dự kiến")
    request_status = fields.Selection(
        selection_add=[
            ("done", "Done"),
        ],
        ondelete={"done": "set default"},
    )

    is_rehire = fields.Boolean(
        string="Tái tuyển",
        default=False,
        copy=False,
    )
    is_blacklisted = fields.Boolean(
        string="Blacklist",
        default=False,
        copy=False,
    )

    # Link to employee -> Standardized field
    employee_id = fields.Many2one(
        "hr.employee",
        string="Nhân viên yêu cầu nghỉ việc",
        compute="_compute_employee_id",
        store=True,
    )

    # Related fields for display
    # Related fields for display
    resignation_employee_name = fields.Char(
        related="employee_id.name", string="Họ tên nhân viên", readonly=True
    )
    resignation_manager_name = fields.Char(
        related="employee_id.parent_id.name",
        string="Line Manager",
        readonly=True,
    )
    resignation_department = fields.Char(
        related="employee_id.department_id.name",
        string="Phòng ban",
        readonly=True,
    )
    job_id = fields.Many2one(
        related="employee_id.job_id",
        string="Chức vụ",
        readonly=True,
    )

    # Employee activities (for offboarding tracking) - includes done activities
    employee_activity_ids = fields.Many2many(
        "mail.activity",
        compute="_compute_employee_activity_ids",
        string="Quá trình nghỉ việc",
        compute_sudo=True,
        context={'active_test': False},
    )

    # Check if employee has completed exit interview survey
    exit_survey_completed = fields.Boolean(
        string="Đã làm khảo sát",
        compute="_compute_exit_survey_completed",
        store=False,
        compute_sudo=True,
    )

    all_activities_completed = fields.Boolean(
        string="Đã hoàn thành mọi công việc",
        compute="_compute_all_activities_completed",
        store=False,
    )

    type_contract = fields.Char(
        string="Loại hợp đồng", compute="_compute_type_contract", store=False
    )

    resignation_owner_email = fields.Char(
        related="request_owner_id.email", string="Email người yêu cầu", readonly=True
    )
    is_plan_launched = fields.Boolean(
        string="Đã Launch Plan", default=False, copy=False
    )

    adecco_notification_sent = fields.Boolean(
        string="Đã gửi Adecco", default=False, copy=False
    )

    exit_survey_user_input_id = fields.Many2one(
        'survey.user_input',
        string='Exit Survey User Input',
        copy=False,
        help='Lưu user_input đã dùng để gửi email khảo sát nghỉ việc, portal sẽ dùng chính link này.',
    )

    def action_withdraw(self):
        """
        Override action_withdraw to prevent withdrawing Resignation requests
        after they have been approved or refused.
        """
        for request in self:
            # Kiểm tra nếu Category là "Resignation" (hoặc ID cụ thể)
            # Và trạng thái đang là Approved hoặc Refused
            if (
                request.category_id.name == "Yêu cầu nghỉ việc "
                and request.request_status in ["approved", "refused"]
            ):
                raise UserError(
                    _(
                        "Bạn không thể rút lại yêu cầu Thôi việc (Resignation) sau khi đã được Phê duyệt hoặc Từ chối."
                    )
                )

        # Nếu không thỏa điều kiện trên, chạy logic gốc của Odoo
        return super(ResignationRequest, self).action_withdraw()

    # Override action_cancel to block the Cancel button
    def action_cancel(self):
        for request in self:
            if (
                request.category_id.name == "Yêu cầu nghỉ việc "
                and request.request_status in ["approved", "refused"]
            ):
                raise UserError(
                    _("Không thể hủy yêu cầu này khi đã có kết quả cuối cùng.")
                )
        return super(ResignationRequest, self).action_cancel()

    def action_send_adecco_notification(self):
        self.ensure_one()
        if not self.employee_id:
            return

        template = self.env.ref(
            "M02_P0213_00.email_template_adecco_notification",
            raise_if_not_found=False,
        )

        if template:
            template.send_mail(self.employee_id.id, force_send=True)
            self.sudo().write({'adecco_notification_sent': True})
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": "Thành công",
                    "message": "Đã gửi thông báo cho Adecco.",
                    "type": "success",
                    "next": {"type": "ir.actions.client", "tag": "soft_reload"},
                },
            }
        else:
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": "Lỗi",
                    "message": "Không tìm thấy Email Template Adecco.",
                    "type": "danger",
                },
            }

    @api.depends("employee_id")
    def _compute_type_contract(self):
        for request in self:
            contract_name = ""
            employee = request.employee_id.sudo()
            if employee:
                # Debug logging
                # _logger.info(f"DEBUG CONTRACT: Employee {employee.name} (ID: {employee.id})")
                contract_type = False
                # Ưu tiên lấy từ contract_id (hợp đồng đang chạy)
                if hasattr(employee, "contract_id") and employee.contract_id:
                    if hasattr(employee.contract_id.sudo(), "contract_type_id"):
                        contract_type = employee.contract_id.sudo().contract_type_id

                # Fallback: lấy từ field trên employee (nếu có)
                if (
                    not contract_type
                    and hasattr(employee, "contract_type_id")
                    and employee.sudo().contract_type_id
                ):
                    contract_type = employee.sudo().contract_type_id

                if contract_type:
                    # _logger.info(f"DEBUG CONTRACT: Type found {contract_type.name}")
                    contract_name = contract_type.name

            request.type_contract = contract_name

    @api.depends("employee_id", "employee_activity_ids", "is_plan_launched")
    def _compute_all_activities_completed(self):
        for request in self:
            if not request.is_plan_launched:
                request.all_activities_completed = False
                continue

            # Đếm các activity còn active (chưa done) trên approval.request và hr.employee
            pending_count = self.env["mail.activity"].sudo().search_count([
                ("active", "=", True),
                "|",
                "&", ("res_model", "=", "approval.request"), ("res_id", "=", request.id),
                "&", ("res_model", "=", "hr.employee"), ("res_id", "=", request.employee_id.id if request.employee_id else 0),
            ])
            request.all_activities_completed = (pending_count == 0)

    def action_send_social_insurance(self):
        self.ensure_one()
        if not self.resignation_employee_id:
            return

        template = self.env.ref(
            "M02_P0213_00.email_template_social_insurance",
            raise_if_not_found=False,
        )

        if template:
            template.send_mail(self.employee_id.id, force_send=True)
            self.action_done()
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": "Thành công",
                    "message": "Đã gửi thông tin BHXH qua email.",
                    "type": "success",
                },
            }
        else:
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": "Lỗi",
                    "message": "Không tìm thấy Email Template BHXH.",
                    "type": "danger",
                },
            }

    @api.depends("request_owner_id")
    def _compute_exit_survey_completed(self):
        """Check if request_owner has completed exit interview survey"""
        survey = self.env.ref(
            "M02_P0214_00.survey_exit_interview", raise_if_not_found=False
        ).sudo()
        for request in self:
            completed = False
            if survey and request.request_owner_id:
                # Search for completed survey response by email or partner
                user_input = self.env["survey.user_input"].sudo().search(
                    [
                        ("survey_id", "=", survey.id),
                        ("state", "=", "done"),
                        "|",
                        ("email", "=", request.request_owner_id.email),
                        ("partner_id", "=", request.request_owner_id.partner_id.id),
                    ],
                    limit=1,
                )
                completed = bool(user_input)
            request.exit_survey_completed = completed

    def action_view_survey_results(self):
        """
        Open the survey.user_input form for the completed exit survey.
        """
        self.ensure_one()
        survey = (
            self.env.ref("M02_P0214_00.survey_exit_interview", raise_if_not_found=False)
            .sudo()
        )
        if not survey:
            return

        user_inputs = self.env["survey.user_input"].sudo().search(
            [
                ("survey_id", "=", survey.id),
                ("state", "=", "done"),
                "|",
                ("email", "=", self.request_owner_id.email),
                ("partner_id", "=", self.request_owner_id.partner_id.id),
            ]
        )

        if not user_inputs:
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": "Thông báo",
                    "message": "Không tìm thấy kết quả khảo sát đã hoàn thành.",
                    "type": "warning",
                },
            }

        # If multiple, show list. If one, show form.
        action = {
            "name": "Kết quả khảo sát",
            "type": "ir.actions.act_window",
            "res_model": "survey.user_input",
            "context": {"create": False},
        }
        if len(user_inputs) == 1:
            action.update(
                {
                    "view_mode": "form",
                    "res_id": user_inputs.id,
                }
            )
        else:
            action.update(
                {
                    "view_mode": "list,form",
                    "domain": [("id", "in", user_inputs.ids)],
                }
            )
        return action

    # Danh sách activity có res_name trùng tên nhân viên/owner
    # Dùng Many2many cho list computed không có inverse field
    owner_related_activity_ids = fields.Many2many(
        "mail.activity",
        compute="_compute_owner_related_activity_ids",
        string="Hoạt động liên quan (Res Name)",
    )

    @api.depends("employee_id")
    def _compute_owner_related_activity_ids(self):
        # Dùng sudo + active_test=False để search, sau đó browse với env thường
        ActivitySudo = self.env["mail.activity"].sudo().with_context(active_test=False)
        Activity = self.env["mail.activity"].with_context(active_test=False)
        for request in self:
            activities = Activity.browse([])
            if request.employee_id:
                # Search với sudo để bypass access rules
                activity_ids = ActivitySudo.search(
                    [
                        ("res_model", "=", "hr.employee"),
                        ("res_id", "=", request.employee_id.id),
                        ("active", "in", [True, False]),
                    ]
                ).ids
                _logger.info(
                    f"OWNER ACTIVITIES: Employee ID={request.employee_id.id}, Found {len(activity_ids)} activity IDs: {activity_ids}"
                )
                # Browse với env thường để gán vào field
                activities = Activity.browse(activity_ids)
            request.owner_related_activity_ids = activities

    @api.depends("employee_id")
    def _compute_employee_activity_ids(self):
        """Compute activities (active + done) on approval.request and hr.employee"""
        ActivitySudo = self.env["mail.activity"].sudo().with_context(active_test=False)
        for request in self:
            if not request.id or not request.employee_id:
                request.employee_activity_ids = ActivitySudo.browse([])
                continue

            # Dùng SQL để bypass mọi bộ lọc active=False của Odoo
            self.env.cr.execute("""
                SELECT id FROM mail_activity
                WHERE (res_model = 'approval.request' AND res_id = %s)
                   OR (res_model = 'hr.employee' AND res_id = %s)
            """, (request.id, request.employee_id.id))

            activity_ids = [r[0] for r in self.env.cr.fetchall()]
            request.employee_activity_ids = ActivitySudo.browse(activity_ids).with_context(active_test=False)

    @api.depends('request_owner_id', 'partner_id')
    def _compute_employee_id(self):
        for request in self:
            employee = False
            # 1. Partner First
            if request.partner_id:
                employee = self.env["hr.employee"].search(
                    [
                        (
                            "work_contact_id",
                            "=",
                            request.partner_id.id,
                        )
                    ],
                    limit=1,
                )
            # 2. User Fallback
            if not employee and request.request_owner_id:
                employee = self.env["hr.employee"].search(
                    [("user_id", "=", request.request_owner_id.id)], limit=1
                )
            
            request.employee_id = employee.id if employee else False

    def action_approve(self, approver=None):
        """
        Override: Xử lý khi duyệt yêu cầu nghỉ việc
        """
        res = super(ResignationRequest, self).action_approve(approver)

        category_id = self.env.ref(
            "M02_P0213_00.approval_category_resignation",
            raise_if_not_found=False,
        )

        # Lấy plan offboarding
        plan = self.env.ref(
            "M02_P0213_00.offboarding_activity_plan",
            raise_if_not_found=False,
        )

        for request in self:
            if category_id and request.category_id == category_id:
                request.action_send_exit_survey()

                # Schedule "To Do" activity for the request owner
                # if request.request_owner_id:
                #     request.activity_schedule(
                #         "mail.mail_activity_data_todo",
                #         user_id=request.request_owner_id.id,
                #         summary="Hoàn tất thủ tục nghỉ việc",
                #         note="Yêu cầu nghỉ việc đã được duyệt. Vui lòng thực hiện các công việc bàn giao và khảo sát.",
                #     )

                # Tự động launch offboarding plan
                if plan and request.employee_id:
                    request._schedule_offboarding_activities(plan)
                    request.sudo().write({'is_plan_launched': True})

        return res

    def _schedule_offboarding_activities(self, plan):
        """
        Tự động tạo activities từ offboarding plan khi Manager approve.
        """
        self.ensure_one()
        from dateutil.relativedelta import relativedelta

        employee_user = self.employee_id.user_id or self.request_owner_id
        manager_user = self.employee_id.parent_id.user_id
        date_today = fields.Date.today()

        for template in plan.template_ids:
            # Xác định người phụ trách
            if template.responsible_type == 'employee':
                responsible = employee_user
            elif template.responsible_type == 'manager':
                responsible = manager_user
            elif template.responsible_type == 'on_demand':
                responsible = template.responsible_id or self.env['res.users'].search([('login', '=', 'it_rst')], limit=1) or self.env.user
            else:
                responsible = self.env.user

            if not responsible:
                responsible = self.env.user

            # Tính deadline
            date_deadline = date_today
            if template.delay_count > 0:
                delta = (
                    relativedelta(days=template.delay_count) if template.delay_unit == 'days'
                    else relativedelta(weeks=template.delay_count) if template.delay_unit == 'weeks'
                    else relativedelta(months=template.delay_count)
                )
                date_deadline = date_today + delta

            try:
                self.env['mail.activity'].sudo().create({
                    'res_model_id': self.env['ir.model']._get_id('approval.request'),
                    'res_id': self.id,
                    'activity_type_id': template.activity_type_id.id,
                    'summary': template.summary,
                    'note': template.note,
                    'user_id': responsible.id,
                    'date_deadline': date_deadline,
                    'automated': True,
                    'active': True,
                })
            except Exception as e:
                _logger.error(
                    f"[OPS] Error creating offboarding activity from template {template.id}: {str(e)}",
                    exc_info=True,
                )

    def action_launch_plan(self):
        """
        Mở wizard Launch Plan với context là hr.employee
        """

        self.ensure_one()
        self.ensure_one()
        if not self.employee_id:
            return False
        self.is_plan_launched = True
        # Lấy action plan_wizard_action từ module hr
        action = self.env.ref("hr.plan_wizard_action").sudo().read()[0]

        # Thay đổi context để wizard nhận employee thay vì approval.request
        action["context"] = {
            "active_model": "hr.employee",
            "active_id": self.employee_id.id,
            "active_ids": [self.employee_id.id],
            "plan_mode": True,
        }

        return action

    def action_send_exit_survey(self):
        """
        Override: Gửi email chứa link khảo sát Exit Interview (Template M14)
        """
        self.ensure_one()

        # Lấy survey Exit Interview
        survey = self.env.ref(
            "M02_P0214_00.survey_exit_interview", raise_if_not_found=False
        )
        if not survey:
            return super().action_send_exit_survey() # Fallback or error

        # Lấy email của request owner
        partner = self.request_owner_id.partner_id
        if not partner or not partner.email:
             return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": "Lỗi",
                    "message": "Không tìm thấy email của người yêu cầu!",
                    "type": "danger",
                },
            }

        # Tạo survey user_input (invitation) cho người này
        user_input = self.env["survey.user_input"].create(
            {
                "survey_id": survey.id,
                "partner_id": partner.id,
                "email": partner.email,
            }
        )

        # Lấy link survey
        survey_url = user_input.get_start_url()
        base_url = self.env["ir.config_parameter"].sudo().get_param("web.base.url")
        full_survey_url = base_url + survey_url

        # Lấy email template
        template = self.env.ref(
            "M02_P0214_00.email_template_exit_survey",
            raise_if_not_found=False,
        )

        if template:
            # Gửi email bằng template
            template.with_context(survey_url=full_survey_url).send_mail(
                self.id, force_send=True, email_values={"email_to": partner.email}
            )
        else:
            # Fallback to super logic (manual email) if template missing
            return super().action_send_exit_survey()

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": "Thành công",
                "message": f"Đã gửi email khảo sát đến {partner.email}",
                "type": "success",
            },
        }

    def action_done(self):
        """
        Hoàn tất quy trình nghỉ việc:
        - Kiểm tra exit_survey_completed và all_activities_completed
        - Chuyển trạng thái sang 'done'
        - Vô hiệu hóa tài khoản portal/internal của nhân viên
        """
        for request in self:
            if not request.exit_survey_completed:
                raise UserError(
                    _("Vui lòng hoàn thành khảo sát Nghỉ việc trước khi Hoàn tất quy trình.")
                )
            if not request.all_activities_completed:
                raise UserError(
                    _("Vui lòng hoàn thành tất cả công việc Offboarding trước khi Hoàn tất quy trình.")
                )

        self.sudo().write({"request_status": "done"})

        for request in self:
            request_sudo = request.sudo()

            # Tìm user cần vô hiệu hóa
            user_to_deactivate = False

            # Ưu tiên 1: employee.user_id
            if request_sudo.employee_id and request_sudo.employee_id.user_id:
                user_to_deactivate = request_sudo.employee_id.user_id

            # Ưu tiên 2: request_owner_id (portal user)
            if not user_to_deactivate and request_sudo.request_owner_id:
                user_to_deactivate = request_sudo.request_owner_id

            if user_to_deactivate and user_to_deactivate.active:
                is_portal = user_to_deactivate.has_group('base.group_portal')
                is_internal = user_to_deactivate.has_group('base.group_user')
                if (is_portal or is_internal) and not user_to_deactivate.has_group('base.group_system'):
                    try:
                        user_to_deactivate.write({'active': False})
                        request.message_post(
                            body=f"✅ Hệ thống: Đã vô hiệu hóa tài khoản Portal/User: "
                                 f"{user_to_deactivate.name} ({user_to_deactivate.login})"
                        )
                    except Exception as e:
                        _logger.error(
                            f"OPS 0213: Failed to deactivate user {user_to_deactivate.id}: {str(e)}"
                        )

            # Tự động hoàn thành các activity To-Do còn lại của request_owner
            if request_sudo.request_owner_id:
                todo_type = self.env.ref(
                    "mail.mail_activity_data_todo", raise_if_not_found=False
                )
                domain = [
                    ("res_model", "=", "approval.request"),
                    ("res_id", "=", request.id),
                    ("user_id", "=", request_sudo.request_owner_id.id),
                ]
                if todo_type:
                    domain.append(("activity_type_id", "=", todo_type.id))
                activities = self.env["mail.activity"].search(domain)
                if activities:
                    activities.action_feedback(
                        feedback="Đã hoàn thành thủ tục nghỉ việc."
                    )

    def action_rehire(self):
        """Đánh dấu nhân viên được tái tuyển dụng."""
        self.ensure_one()
        self.sudo().write({"is_rehire": True})
        self.message_post(body="✅ Đã đánh dấu: Tái tuyển")
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": "Tái tuyển",
                "message": "Đã đánh dấu nhân viên đủ điều kiện tái tuyển.",
                "type": "success",
                "next": {"type": "ir.actions.client", "tag": "soft_reload"},
            },
        }

    def action_blacklist(self):
        """Đánh dấu nhân viên vào danh sách đen."""
        self.ensure_one()
        self.sudo().write({"is_blacklisted": True})
        self.message_post(body="🚫 Đã đánh dấu: Blacklist")
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": "Blacklist",
                "message": "Đã đưa nhân viên vào danh sách đen.",
                "type": "warning",
                "next": {"type": "ir.actions.client", "tag": "soft_reload"},
            },
        }

    @api.model
    def _cron_send_offboarding_reminders(self):
        """
        RST Reminders & Automatic Deadline Extensions:
        1. Tìm các đơn RST trạng thái 'Approved'.
        2. Tìm các công việc (mail.activity) của đơn đó bị trễ hạn hơn 3 ngày.
        3. Phân loại người phụ trách:
           - Nếu là Nhân viên (Owner): Gửi template Employee.
           - Nếu là IT/Admin/HR/Manager: Gửi template Dept.
        4. Tự động cộng thêm 4 ngày vào Due Date cho các công việc này.
        """
        rst_category = self.env.ref("M02_P0213_00.approval_category_resignation", raise_if_not_found=False)
        if not rst_category:
            return

        emp_template = self.env.ref("M02_P0213_00.email_template_offboarding_reminder", raise_if_not_found=False)
        dept_template = self.env.ref("M02_P0213_00.email_template_dept_offboarding_reminder", raise_if_not_found=False)

        requests = self.search([
            ("category_id", "=", rst_category.id),
            ("request_status", "=", "approved"),
        ])

        # Ngưỡng trễ hạn: Bất cứ công việc nào có hạn nhỏ hơn ngày hôm nay
        today = fields.Date.today()

        for req in requests:
            # Tìm activities chưa xong trên cả đơn và nhân viên
            # Lưu ý dùng sudo() để quét qua mọi record của user khác
            pending_activities = self.env["mail.activity"].sudo().search([
                ('active', '=', True),
                ('date_deadline', '<', today),
                '|',
                '&', ('res_model', '=', 'approval.request'), ('res_id', '=', req.id),
                '&', ('res_model', '=', 'hr.employee'), ('res_id', '=', req.employee_id.id if req.employee_id else 0),
            ])

            if not pending_activities:
                continue

            # Nhóm công việc theo người phụ trách (user_id)
            users_to_remind = pending_activities.mapped('user_id')

            for user in users_to_remind:
                user_acts = pending_activities.filtered(lambda a: a.user_id == user)
                email_to = user.partner_id.email or user.email
                if not email_to:
                    _logger.warning(f"OFFBOARDING CRON: Bỏ qua {user.name} vì không có email.")
                    continue

                try:
                    if user == req.request_owner_id:
                        # Nhắc nhở Nhân viên (áp dụng tương tự)
                        if emp_template:
                            emp_template.send_mail(req.id, force_send=True)
                    else:
                        # Nhắc nhở Phòng ban (IT, Admin, HR, Manager...)
                        if dept_template:
                            dept_template.send_mail(req.id, force_send=True, email_values={'email_to': email_to})

                    # 5. Logic gia hạn: Cộng thêm 4 ngày cho Due Date của các task này
                    for act in user_acts:
                        old_date = act.date_deadline
                        new_date = old_date + timedelta(days=4)
                        act.write({'date_deadline': new_date})

                except Exception as e:
                    _logger.error(f"OFFBOARDING CRON ERROR: Lỗi xử lý cho {user.name}: {str(e)}")

    def action_manual_reminder_extension(self):
        """Kích hoạt thủ công việc nhắc nhở và gia hạn cho ĐƠN NÀY"""
        self.ensure_one()
        if self.request_status != 'approved':
            raise UserError(_("Chỉ có thể nhắc nhở các đơn đang ở trạng thái Approved."))

        today = fields.Date.today()
        # Tìm các activity trễ hạn của đơn này
        pending_activities = self.env["mail.activity"].sudo().search([
            ('active', '=', True),
            ('date_deadline', '<', today),
            '|',
            '&', ('res_model', '=', 'approval.request'), ('res_id', '=', self.id),
            '&', ('res_model', '=', 'hr.employee'), ('res_id', '=', self.employee_id.id if self.employee_id else 0),
        ])

        if not pending_activities:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Thông báo'),
                    'message': _('Không có công việc nào bị trễ hạn để xử lý.'),
                    'type': 'warning',
                    'sticky': False,
                }
            }

        emp_template = self.env.ref("M02_P0213_00.email_template_offboarding_reminder", raise_if_not_found=False)
        dept_template = self.env.ref("M02_P0213_00.email_template_dept_offboarding_reminder", raise_if_not_found=False)

        users_to_remind = pending_activities.mapped('user_id')
        for user in users_to_remind:
            user_acts = pending_activities.filtered(lambda a: a.user_id == user)
            email_to = user.partner_id.email or user.email
            if not email_to: continue

            if user == self.request_owner_id:
                if emp_template: emp_template.send_mail(self.id, force_send=True)
            else:
                if dept_template: dept_template.send_mail(self.id, force_send=True, email_values={'email_to': email_to})

            for act in user_acts:
                act.write({'date_deadline': act.date_deadline + timedelta(days=4)})

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Thành công'),
                'message': _('Đã gửi nhắc nhở và gia hạn cho %s công việc trễ hạn.') % len(pending_activities),
                'type': 'success',
                'sticky': False,
            }
        }
