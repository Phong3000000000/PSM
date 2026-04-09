# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError
from datetime import timedelta
import logging

_logger = logging.getLogger(__name__)


class ResignationType(models.Model):
    _name = "resignation.type"
    _description = "Loại nghỉ việc"
    _order = "sequence, id"

    name = fields.Char(string="Tên loại nghỉ việc", required=True, translate=True)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)


class ResignationRequest(models.Model):
    _inherit = "approval.request"

    # === Resignation Fields ===
    resignation_date = fields.Date(string="Ngày nghỉ dự kiến/chính thức")
    resignation_date_formatted = fields.Char(
        string="Ngày nghỉ dự kiến",
        compute="_compute_resignation_date_formatted",
        store=False
    )
    resignation_type_id = fields.Many2one("resignation.type", string="Loại nghỉ việc (Legacy)", readonly=True)
    resignation_reason_id = fields.Many2one("hr.departure.reason", string="Lý do nghỉ việc")
    social_insurance_email_sent = fields.Boolean(
        string="Đã gửi Email BHXH",
        default=False,
        help="Đánh dấu email hướng dẫn BHXH đã được gửi tự động"
    )

    @api.depends('resignation_date')
    def _compute_resignation_date_formatted(self):
        """Format resignation_date as dd/MM/yyyy"""
        for request in self:
            if request.resignation_date:
                request.resignation_date_formatted = request.resignation_date.strftime('%d/%m/%Y')
            else:
                request.resignation_date_formatted = ''

    def action_confirm(self):
        """
        Override action_confirm to bypass strict manager validation for Resignation requests.
        The standard approval module raises a UserError if it thinks the manager is missing,
        even if we provided an approver manually.
        """
        rst_category = self.env.ref(
            "M02_P0214_00.approval_category_resignation",
            raise_if_not_found=False,
        )
        base_category = self.env.ref(
            "M02_P0213_00.approval_category_resignation",
            raise_if_not_found=False,
        )
        
        # Requests that are NOT resignation -> use standard logic
        resignation_categories = [cat.id for cat in [rst_category, base_category] if cat]
        others = self.filtered(lambda r: r.category_id.id not in resignation_categories)
        if others:
            super(ResignationRequest, others).action_confirm()
            
        # Requests that ARE resignation -> custom logic (skip strict manager check if approvers exist)
        resignations = self - others
        if resignations:
            # Check if it has approvers before forcing pending (Safety check)
            for request in resignations:
                if not request.approver_ids:
                    # Fallback to standard check if no approver added at all
                    # but usually our controller adds it.
                    pass 

            # Directly set status to pending (Submitted) to bypass the check
            # but we use sudo to ensure it sets correctly
            resignations.sudo().write({'request_status': 'pending'})
            
            # Manually trigger activity update for approvers (simulating standard behavior)
            for request in resignations:
                # Get approvers with status 'new' to create approval activities
                approvers_new = request.approver_ids.filtered(lambda a: a.status == 'new')
                if approvers_new:
                    # Create approval notification activities (this will trigger bell icon badge)
                    approvers_new._create_activity()
                    # Update their status to pending
                    approvers_new.sudo().write({'status': 'pending'})
                
                request.sudo().write({'date_confirmed': fields.Datetime.now()})






    def action_send_social_insurance(self):
        self.ensure_one()
        rst_category = self.env.ref(
            "M02_P0214_00.approval_category_resignation",
            raise_if_not_found=False,
        )

        # Non-RST requests must keep the OPS 0213 behavior.
        if not rst_category or self.category_id != rst_category:
            return super(ResignationRequest, self).action_send_social_insurance()
        
        # KIỂM TRA: Nếu đã gửi email BHXH rồi thì skip (tránh gửi lặp lại)
        if self.social_insurance_email_sent:
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": "Thông báo",
                    "message": "Email BHXH đã được gửi trước đó.",
                    "type": "warning",
                },
            }
        
        # Validation: Kiểm tra đã hoàn thành khảo sát và tất cả công việc
        if not self.exit_survey_completed:
            raise UserError(_("Vui lòng hoàn thành khảo sát Nghỉ việc trước khi gửi thông tin BHXH."))
        if not self.all_activities_completed:
            raise UserError(_("Vui lòng hoàn thành tất cả công việc Offboarding trước khi gửi thông tin BHXH."))
        
        if not self.employee_id:
            return

        template = self.env.ref(
            "M02_P0214_00.email_template_social_insurance",
            raise_if_not_found=False,
        )

        if template:
            # Gửi email từ template, sử dụng sudo() để đảm bảo Portal user trigger được
            template.sudo().send_mail(self.employee_id.id, force_send=True)
            
            # Đánh dấu đã gửi email BHXH để tránh gửi lặp lại
            self.sudo().write({'social_insurance_email_sent': True})
            
            # Log lại vào chatter của Đơn phê duyệt để HR biết email đã được gửi tự động
            self.sudo().message_post(
                body=_("Email hướng dẫn nhận BHXH/QĐNV đã được gửi đến %s. Đơn vẫn ở trạng thái Approved để HR rà soát trước khi Hoàn tất.") % self.employee_id.name
            )
            
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
        )
        survey = survey.sudo() if survey else self.env["survey.survey"]
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
        survey = self.env.ref(
            "M02_P0214_00.survey_exit_interview", raise_if_not_found=False
        )
        survey = survey.sudo() if survey else self.env["survey.survey"]
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
        # Dùng sudo + active_test=False để search, sau đó browse với sudo
        ActivitySudo = self.env["mail.activity"].sudo().with_context(active_test=False)
        for request in self:
            activities = ActivitySudo.browse([])
            if request.employee_id:
                # Search cho cả 2 res_model: hr.employee (cũ) và approval.request (mới)
                # để đảm bảo user thấy được tất cả checklist liên quan
                activity_ids = ActivitySudo.search(
                    [
                        ("res_model", "in", ["hr.employee", "approval.request"]),
                        "|",
                        "&", ("res_model", "=", "hr.employee"), ("res_id", "=", request.employee_id.id),
                        "&", ("res_model", "=", "approval.request"), ("res_id", "=", request.id),
                        ("active", "in", [True, False]),
                    ]
                ).ids

                # Browse sudo để tránh lỗi truy cập khi xem danh sách checklist
                activities = ActivitySudo.browse(activity_ids)
            request.owner_related_activity_ids = activities

    # Employee activities (for offboarding tracking) - includes done activities
    # Sử dụng tên trường riêng biệt cho RST để tránh xung đột với module 0213
    # Employee activities (for offboarding tracking) - includes done activities
    # Sử dụng tên trường riêng biệt cho RST để tránh xung đột với module 0213
    # Thêm context={'active_test': False} ngay trong định nghĩa field để Odoo luôn lấy cả record đã done
    rst_checklist_activity_ids = fields.Many2many(
        "mail.activity",
        compute="_compute_rst_checklist_activity_ids",
        string="Quá trình nghỉ việc (RST)",
        compute_sudo=True,
        context={'active_test': False},
    )

    @api.depends("employee_id")
    def _compute_rst_checklist_activity_ids(self):
        """Compute activities including archived (done) ones - RST Specific"""
        # Search với sudo và context active_test=False để quét toàn bộ DB
        ActivitySudo = self.env["mail.activity"].sudo().with_context(active_test=False)
        for request in self:
            # Skip if record not yet saved to DB (has NewId)
            if not request.id or isinstance(request.id, str) and not request.id.isdigit():
                request.rst_checklist_activity_ids = ActivitySudo.browse([])
                continue
            
            if not request.employee_id:
                request.rst_checklist_activity_ids = ActivitySudo.browse([])
                continue
            
            # Sử dụng SQL trực tiếp để lấy ID nhằm bypass mọi bộ lọc mặc định của Odoo
            # bao gồm cả các record đã bị marked active=False
            self.env.cr.execute("""
                SELECT id FROM mail_activity 
                WHERE (res_model = 'approval.request' AND res_id = %s)
                   OR (res_model = 'hr.employee' AND res_id = %s)
            """, (request.id, request.employee_id.id if request.employee_id else 0))
            
            activity_ids = [r[0] for r in self.env.cr.fetchall()]
            # Gán recordset (với context active_test=False) cho field Many2many
            request.rst_checklist_activity_ids = ActivitySudo.browse(activity_ids).with_context(active_test=False)

    @api.depends("employee_id", "is_plan_launched")
    def _compute_all_activities_completed(self):
        """
        Ghi đè logic: Mọi công việc hoàn thành khi không còn bất kỳ activity nào 
        đang chạy (Active) trên cả 2 mô hình (nhân viên hoặc đơn).
        """
        for request in self:
            if not request.is_plan_launched:
                # Nếu chưa chạy plan thì chưa thể coi là hoàn thành
                request.all_activities_completed = False
            else:
                # Kiểm tra xem còn bất kỳ activity nào chưa hoàn thành không
                # Chỉ đếm các activity đang hoạt động (active = True)
                pending_count = self.env["mail.activity"].sudo().search_count([
                    ("active", "=", True),
                    '|',
                    '&', ('res_model', '=', 'approval.request'), ('res_id', '=', request.id),
                    '&', ('res_model', '=', 'hr.employee'), ('res_id', '=', request.employee_id.id if request.employee_id else 0),
                ])
                # Nếu không còn đầu việc nào đang chạy (pending) -> Đã hoàn thành mọi công việc
                request.all_activities_completed = (pending_count == 0)

    @api.depends('request_owner_id', 'partner_id')
    def _compute_employee_id(self):
        for request in self:
            # If employee_id is already set (e.g. during create from controller), preserve it.
            if request.employee_id:
                continue

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

    def action_done(self):
        rst_category = self.env.ref(
            "M02_P0214_00.approval_category_resignation",
            raise_if_not_found=False,
        )

        # Keep the existing OPS 0213 logic for non-RST categories.
        non_rst_requests = self.filtered(
            lambda request: not rst_category or request.category_id != rst_category
        )
        if non_rst_requests:
            super(ResignationRequest, non_rst_requests).action_done()

        rst_requests = self.filtered(
            lambda request: rst_category and request.category_id == rst_category
        )
        if not rst_requests:
            return

        # Validation: Kiểm tra đã hoàn thành khảo sát và tất cả công việc trước khi Mark Done
        for request in rst_requests:
            if not request.exit_survey_completed:
                raise UserError(_("Vui lòng hoàn thành khảo sát Nghỉ việc trước khi Hoàn tất quy trình."))
            if not request.all_activities_completed:
                raise UserError(_("Vui lòng hoàn thành tất cả công việc Offboarding trước khi Hoàn tất quy trình."))
        
            if not request.social_insurance_email_sent:
                raise UserError(_("Vui lòng gửi Email hướng dẫn BHXH trước khi Hoàn tất quy trình."))

        rst_requests.sudo().write({"request_status": "done"})
        
        for request in rst_requests:
            # --- AUTOMATION STEP 21: Deactivate Portal User ---
            # Sử dụng sudo() để truy cập thông tin User và Employee 
            # vì các trường này có thể bị giới hạn quyền đối với user thông thường
            request_sudo = request.sudo()
            user_to_deactivate = False
            
            # Ưu tiên 1: Theo Employee ID (Nhân viên nội bộ liên kết cứng)
            if request_sudo.employee_id and request_sudo.employee_id.user_id:
                user_to_deactivate = request_sudo.employee_id.user_id
            
            # Ưu tiên 2: Theo Request Owner (Tài khoản Portal gửi đơn)
            # Nếu User là Portal User, thường sẽ không có link user_id trên employee
            if not user_to_deactivate and request_sudo.request_owner_id:
                user_to_deactivate = request_sudo.request_owner_id

            if user_to_deactivate and user_to_deactivate.active:
                # Kiểm tra xem đây có phải là Portal user không (hoặc là Employee)
                # Tránh vô hiệu hóa tài khoản quản trị nhầm
                is_portal = user_to_deactivate.has_group('base.group_portal')
                is_internal = user_to_deactivate.has_group('base.group_user')
                
                # Logic: Chỉ vô hiệu hóa nếu là Portal user hoặc Internal user thông thường 
                # (không phải Admin để tránh lock out)
                if (is_portal or is_internal) and not user_to_deactivate.has_group('base.group_system'):
                    _logger.info(f"OFFBOARDING AUTO: Deactivating user {user_to_deactivate.login} for request {request.id}")
                    try:
                        user_to_deactivate.write({'active': False})
                        request.message_post(body=f"✅ Hệ thống: Đã vô hiệu hóa tài khoản Portal/User: {user_to_deactivate.name}")
                    except Exception as e:
                        _logger.error(f"OFFBOARDING AUTO: Failed to deactivate user {user_to_deactivate.login}: {str(e)}")
                else:
                    _logger.warning(f"OFFBOARDING AUTO: Skip deactivating safe account {user_to_deactivate.login}")
            # --------------------------------------------------

            # Auto-complete related activities for the owner
            domain = [
                ("res_model", "=", "approval.request"),
                ("res_id", "=", request.id),
                ("user_id", "=", request.request_owner_id.id),
                (
                    "activity_type_id",
                    "=",
                    self.env.ref("mail.mail_activity_data_todo").id,
                ),
            ]
            activities = self.env["mail.activity"].search(domain)
            activities.action_feedback(feedback="Đã hoàn thành thủ tục nghỉ việc.")

    def action_approve(self, approver=None):
        """
        Override: Validate date and Launch Offboarding Plan automatically
        """
        # Step 5: Validate Date
        # Only for RST Resignation
        rst_category = self.env.ref("M02_P0214_00.approval_category_resignation", raise_if_not_found=False)
        for request in self:
            if rst_category and request.category_id == rst_category and not request.resignation_date:
                raise UserError(_("Vui lòng xác nhận 'Ngày nghỉ dự kiến' trước khi phê duyệt."))

        # Step 6: Approve (and trigger Step 8: Exit Survey via super)
        res = super(ResignationRequest, self).action_approve(approver)

        # Trigger Exit Survey for M14 Category (since super only handles M13 category)
        for request in self:
            if rst_category and request.category_id == rst_category:
                request.action_send_exit_survey()

        # Step 7: Launch Plan
        plan = self.env.ref("M02_P0214_00.offboarding_activity_plan_rst", raise_if_not_found=False)
        if plan:
            for request in self:
                if rst_category and request.category_id == rst_category and request.employee_id:
                    self._schedule_offboarding_activity(request, plan)
                    # Đánh dấu đã chạy plan để logic compute completion hoạt động đúng
                    request.sudo().write({'is_plan_launched': True})
        
        return res

    def action_send_exit_survey(self):
        """
        Override: Gửi email chứa link khảo sát Exit Interview (Template M14)
        """
        self.ensure_one()

        # Lấy survey Exit Interview (M14 data)
        survey = self.env.ref(
            "M02_P0214_00.survey_exit_interview", raise_if_not_found=False
        )
        if not survey:
            return super().action_send_exit_survey() # Fallback to M13 or error

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
        if not self.exit_survey_user_input_id:
            self.sudo().write({"exit_survey_user_input_id": user_input.id})

        # Lấy link survey
        survey_url = user_input.get_start_url()
        base_url = self.env["ir.config_parameter"].sudo().get_param("web.base.url")
        full_survey_url = base_url + survey_url

        # Lấy email template M14
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

    def _schedule_offboarding_activity(self, request, plan):
        """
        Helper to schedule activities from config plan
        """
        # Dictionary to map responsible types to users
        # responsible_type: employee, manager, other
        employee_user = request.employee_id.user_id or request.request_owner_id
        manager_user = request.employee_id.parent_id.user_id
        
        created_activities = []
        for template in plan.template_ids:
            # Determine Responsible
            responsible = False
            if template.responsible_type == 'employee':
                responsible = employee_user
            elif template.responsible_type == 'manager':
                responsible = manager_user
            elif template.responsible_type == 'other':
                # Try to use responsible_id if set
                if template.responsible_id:
                    responsible = template.responsible_id
                else:
                    # Fallback: Try to get first user from group based on summary
                    # For IT tasks
                    if 'IT' in template.summary or 'thiết bị' in template.summary.lower():
                        it_users = self.env['res.users'].search([('groups_id.name', '=', 'Technical Manager')], limit=1)
                        responsible = it_users[0] if it_users else False
                    # For Admin tasks
                    elif 'Admin' in template.summary or 'quản trị' in template.summary.lower():
                        admin_users = self.env['res.users'].search([('groups_id.name', '=', 'Access Rights')], limit=1)
                        responsible = admin_users[0] if admin_users else False
                    # For HR tasks
                    elif 'HR' in template.summary or 'nhân sự' in template.summary.lower():
                        hr_users = self.env['res.users'].search([('groups_id.name', '=', 'Human Resources / User')], limit=1)
                        responsible = hr_users[0] if hr_users else False
            
            # Fallback for 'on_demand' or missing users -> Assign to current user (Approver) or Admin
            if not responsible:
                responsible = self.env.user 
            
            # Use sudo to access mail.activity.plan.template if needed, 
            # but template is browsed from plan so standard rights should apply if plan is readable.
            
            # Calculate Deadline
            # Default: deadline is TODAY so activity shows in bell icon (not "Future")
            # If delay_count > 0, add that to today
            date_today = fields.Date.today()
            date_deadline = date_today  # Activities show today by default
            
            if template.delay_count > 0:
                from dateutil.relativedelta import relativedelta
                delta = relativedelta(days=template.delay_count) if template.delay_unit == 'days' else \
                        relativedelta(weeks=template.delay_count) if template.delay_unit == 'weeks' else \
                        relativedelta(months=template.delay_count)
                
                # If there's a delay, add it to today
                date_deadline = date_today + delta

            # Create Activity
            try:
                activity = self.env['mail.activity'].sudo().create({
                    'res_model_id': self.env['ir.model']._get_id('approval.request'),
                    'res_id': request.id,
                    'activity_type_id': template.activity_type_id.id,
                    'summary': template.summary,
                    'note': template.note,
                    'user_id': responsible.id,
                    'date_deadline': date_deadline,
                    'automated': True,
                    'active': True,  # ENSURE activity is active so it shows in bell icon
                })
                created_activities.append(activity)
            except Exception as e:
                _logger.error(f"[RST] Error creating offboarding activity from template {template.id}: {str(e)}", exc_info=True)
        
        # CRITICAL: Force flush to ensure activities are committed to DB immediately
        # This prevents race conditions where activities are not visible in bell icon until page refresh
        if created_activities:
            self.env.cr.commit()

    def action_checklist_completed(self):
        """
        Called when all offboarding activities are completed.
        Keep the request ready for HR to send Social Insurance instructions manually.
        """
        for request in self:
            message = _("✅ TOÀN BỘ CHECKLIST OFFBOARDING ĐÃ HOÀN THÀNH.")

            exit_survey = self.env.ref(
                "M02_P0214_00.survey_exit_interview", raise_if_not_found=False
            ).sudo()
            survey_completed = False
            if exit_survey and request.request_owner_id:
                user_input = self.env["survey.user_input"].sudo().search(
                    [
                        ("survey_id", "=", exit_survey.id),
                        ("state", "=", "done"),
                        "|",
                        ("email", "=", request.request_owner_id.email),
                        ("partner_id", "=", request.request_owner_id.partner_id.id),
                    ],
                    limit=1,
                )
                survey_completed = bool(user_input)

            pending_count = self.env["mail.activity"].search_count(
                [
                    ("active", "=", True),
                    "|",
                    "&",
                    ("res_model", "=", "approval.request"),
                    ("res_id", "=", request.id),
                    "&",
                    ("res_model", "=", "hr.employee"),
                    ("res_id", "=", request.employee_id.id if request.employee_id else 0),
                ]
            )
            activities_completed = pending_count == 0

            if survey_completed and activities_completed:
                if request.social_insurance_email_sent:
                    message += _(" Email BHXH đã được gửi.")
                else:
                    message += _(" HR có thể gửi hướng dẫn BHXH từ nút trên form.")
                request.message_post(body=message)
            else:
                missing = []
                if not survey_completed:
                    missing.append("Exit Interview")
                if not activities_completed:
                    missing.append("Công việc Offboarding")
                message += _(f" (Chờ hoàn thành: {', '.join(missing)})")
                request.message_post(body=message)

    @api.model
    def _cron_send_offboarding_reminders(self):
        """
        RST Reminders & Automatic Deadline Extensions:
        1. Tìm các đơn RST trạng thái 'Approved'.
        2. Tìm các công việc (`mail.activity`) của đơn đó đã quá hạn.
        3. Phân loại theo người phụ trách:
           - Nếu là Nhân viên (Owner): gửi template Employee.
           - Nếu là IT/Admin/HR/Manager: gửi template Dept.
        4. Tự động cộng thêm 4 ngày vào Due Date cho các công việc này.
        """
        rst_category = self.env.ref("M02_P0214_00.approval_category_resignation", raise_if_not_found=False)
        if not rst_category:
            return

        emp_template = self.env.ref("M02_P0214_00.email_template_offboarding_reminder", raise_if_not_found=False)
        dept_template = self.env.ref("M02_P0214_00.email_template_dept_offboarding_reminder", raise_if_not_found=False)

        requests = self.search([
            ("category_id", "=", rst_category.id),
            ("request_status", "=", "approved"),
        ])
        
        # Ngưỡng trễ hạn: bất kỳ công việc nào có hạn nhỏ hơn ngày hôm nay
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
                        # Nhắc nhở Nhân viên
                        if emp_template:
                            emp_template.send_mail(req.id, force_send=True)
                    else:
                        # Nhắc nhở Phòng ban (IT, Admin, HR, Manager...)
                        if dept_template:
                            dept_template.send_mail(req.id, force_send=True, email_values={'email_to': email_to})
                    
                    # Logic gia hạn: cộng thêm 4 ngày cho Due Date của các task này
                    for act in user_acts:
                        old_date = act.date_deadline
                        new_date = old_date + timedelta(days=4)
                        act.write({'date_deadline': new_date})

                except Exception as e:
                    _logger.error(f"OFFBOARDING CRON ERROR: Lỗi xử lý cho {user.name}: {str(e)}")

    def action_manual_reminder_extension(self):
        """Kích hoạt thủ công việc nhắc nhở và gia hạn cho đơn này."""
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

        emp_template = self.env.ref("M02_P0214_00.email_template_offboarding_reminder", raise_if_not_found=False)
        dept_template = self.env.ref("M02_P0214_00.email_template_dept_offboarding_reminder", raise_if_not_found=False)

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

    def action_view_my_activities(self):
        """Open My Activities view without default date filters"""
        return {
            'type': 'ir.actions.act_window',
            'name': 'My Activities',
            'res_model': 'mail.activity',
            'view_mode': 'list,kanban,calendar',
            'search_view_id': self.env.ref('mail.mail_activity_view_search').id,
            'context': {
                'search_default_filter_user_id_uid': 1,
            },
        }

    @api.model
    def action_pending_offboarding_subordinates(self):
        """
        Mở báo cáo: Đơn Offboarding RST chưa hoàn thành của nhân viên cấp dưới.
        Một đơn chưa hoàn thành = chưa hoàn thành khảo sát HOẶC chưa hoàn thành mọi công việc.
        Lọc theo:
        - Nhân viên cấp dưới trực tiếp + gián tiếp của manager hiện tại
        - Chỉ các đơn nghỉ việc RST đang ở trạng thái Approved
        """
        rst_category = self.env.ref(
            "M02_P0214_00.approval_category_resignation", raise_if_not_found=False
        )
        if not rst_category:
            raise UserError(_("Không tìm thấy category Quy trình nghỉ việc RST."))

        # Tìm nhân viên hiện tại (manager)
        current_employee = self.env['hr.employee'].search([
            ('user_id', '=', self.env.uid)
        ], limit=1)

        if not current_employee:
            raise UserError(_("Không tìm thấy hồ sơ nhân viên của bạn."))

        # Tìm tất cả nhân viên cấp dưới (trực tiếp + gián tiếp)
        all_subordinates = current_employee.child_ids
        queue = list(current_employee.child_ids)
        while queue:
            emp = queue.pop(0)
            children = emp.child_ids
            all_subordinates |= children
            queue.extend(children)
        subordinate_ids = all_subordinates.ids

        if not subordinate_ids:
            raise UserError(_("Bạn chưa có nhân viên cấp dưới nào."))

        # Tìm các đơn nghỉ việc RST đang Approved của nhân viên cấp dưới
        resignation_requests = self.sudo().search([
            ('category_id', '=', rst_category.id),
            ('request_status', '=', 'approved'),
            ('employee_id', 'in', subordinate_ids),
        ])

        # Lọc thêm: chỉ giữ đơn chưa hoàn thành (chưa khảo sát HOẶC chưa xong công việc)
        pending_requests = resignation_requests.filtered(
            lambda r: not r.exit_survey_completed or not r.all_activities_completed
        )

        if not pending_requests:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Thông báo'),
                    'message': _('Tất cả đơn nghỉ việc của nhân viên cấp dưới đã hoàn thành.'),
                    'type': 'info',
                    'sticky': False,
                }
            }

        return {
            'type': 'ir.actions.act_window',
            'name': _('Offboarding Report - Nhân viên cấp dưới'),
            'res_model': 'approval.request',
            'view_mode': 'list,form',
            'views': [
                (self.env.ref('M02_P0214_00.view_offboarding_report_tree').id, 'list'),
                (False, 'form'),
            ],
            'search_view_id': self.env.ref('M02_P0214_00.view_offboarding_report_search').id,
            'domain': [('id', 'in', pending_requests.ids)],
            'context': {
                'create': False,
                'search_default_groupby_reason': 1,
            },
        }






