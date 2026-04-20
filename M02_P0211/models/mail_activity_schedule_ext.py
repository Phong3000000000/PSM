from odoo import models, fields, api, _
from odoo.exceptions import UserError


class MailActivityPlanTemplate(models.Model):
    _inherit = 'mail.activity.plan.template'

    x_psm_0211_responsible_role = fields.Selection([
        ('manager', 'Phụ trách Onboarding'),
        ('it', 'Phụ trách IT/Digital')
    ], string='Responsible Role (PSM)', default='manager', 
       help="Dùng để phân biệt người phụ trách trong kịch bản Onboarding của PSM.")


class MailActivitySchedule(models.TransientModel):
    _inherit = 'mail.activity.schedule'

    x_psm_0211_3P_email = fields.Char(
        string="Email thông báo", 
        compute='_compute_psm_0211_3p_email', store=True, readonly=False)

    x_psm_0211_bp_user_id = fields.Many2one(
        'res.users', string="Phụ trách Onboarding", 
        default=lambda self: self.env.user)

    @api.depends('res_ids', 'x_psm_0211_is_onboarding_plan')
    def _compute_psm_0211_3p_email(self):
        """Tự động chọn Email dựa trên loại nhân viên trong danh sách."""
        for rec in self: 
            email = False
            if rec.x_psm_0211_is_onboarding_plan:
                applied_on = rec._get_applied_on_records()
                # Nếu có bất kỳ nhân viên nào là khối RST (Office), ưu tiên dùng mail Good Day
                # (Thông thường bạn sẽ chạy Onboarding theo khối)
                x_psm_0211_staff_type = 'office' if any(e.x_psm_0211_staff_type == 'office' for e in applied_on) else 'ops'
                email = self.env['x_psm.hr.adecco.config'].sudo().get_x_psm_agency_email(x_psm_0211_staff_type=x_psm_0211_staff_type)
            rec.x_psm_0211_3P_email = email or self.env['x_psm.hr.adecco.config'].sudo().get_x_psm_adecco_email()
    x_psm_0211_is_onboarding_plan = fields.Boolean(compute='_compute_psm_0211_is_onboarding_plan')
    x_psm_0211_has_ops_employee = fields.Boolean(compute='_compute_psm_0211_has_ops_employee')
    x_psm_0211_has_office_employee = fields.Boolean(compute='_compute_psm_0211_has_office_employee')
    x_psm_0211_vsattp_survey_id = fields.Many2one(
        'survey.survey', string="Bài kiểm tra VSATTP",
        help="Chọn bài kiểm tra VSATTP sẽ được đính kèm trong email nhận việc gửi cho ứng viên.")

    @api.depends('plan_id', 'res_model', 'res_ids')
    def _compute_psm_0211_is_onboarding_plan(self):
        # XML IDs known for onboarding plans
        onboarding_xml_ids = [
            'hr.onboarding_plan',
            'M02_P0211.onboarding_plan_ext',
            'M02_P0212_00.onboarding_plan_rst'
        ]
        for rec in self:
            is_onboarding_name = rec.plan_id and 'onboarding' in rec.plan_id.name.lower()
            is_onboarding_xml = False
            if rec.plan_id:
                xml_id_data = rec.plan_id.get_metadata()[0].get('xmlid')
                is_onboarding_xml = xml_id_data in onboarding_xml_ids
            
            rec.x_psm_0211_is_onboarding_plan = bool(rec.res_model == 'hr.employee' and rec.plan_id and (is_onboarding_name or is_onboarding_xml))

    @api.depends('x_psm_0211_is_onboarding_plan', 'res_ids')
    def _compute_psm_0211_has_ops_employee(self):
        """Kiểm tra có nhân viên khối OPS trong danh sách không."""
        for rec in self:
            has_ops = False
            if rec.x_psm_0211_is_onboarding_plan:
                applied_on = rec._get_applied_on_records()
                if any(e.x_psm_0211_staff_type == 'ops' for e in applied_on):
                    has_ops = True
            rec.x_psm_0211_has_ops_employee = has_ops
    @api.depends('x_psm_0211_is_onboarding_plan', 'res_ids')
    def _compute_psm_0211_has_office_employee(self):
        """Kiểm tra có nhân viên khối RST (Office) trong danh sách không."""
        for rec in self:
            has_office = False
            if rec.x_psm_0211_is_onboarding_plan:
                applied_on = rec._get_applied_on_records()
                if any(e.x_psm_0211_staff_type == 'office' for e in applied_on):
                    has_office = True
            rec.x_psm_0211_has_office_employee = has_office

    def action_schedule_plan(self):
        # Validate: Phải chọn bài VSATTP nếu có nhân viên khối OPS
        if self.x_psm_0211_is_onboarding_plan and self.x_psm_0211_has_ops_employee and not self.x_psm_0211_vsattp_survey_id:
            raise UserError("Vui lòng chọn Bài kiểm tra VSATTP cho nhân viên khối OPS trước khi bấm Schedule!")

        if self.x_psm_0211_is_onboarding_plan:
            applied_on = self._get_applied_on_records()
            
            # --- Xử lý chống trùng lặp (Duplicate) ---
            # Nếu đã có các hoạt động của Plan này trên Record, xóa bỏ trước khi tạo mới
            activity_type_ids = self.plan_id.template_ids.mapped('activity_type_id').ids
            existing_activities = self.env['mail.activity'].sudo().search([
                ('res_model', '=', 'hr.employee'),
                ('res_id', 'in', applied_on.ids),
                ('activity_type_id', 'in', activity_type_ids)
            ])
            if existing_activities:
                existing_activities.unlink()
            
            # Xóa cả các task cũ trong board checklist
            applied_on.x_psm_0211_onboarding_task_ids.sudo().unlink()

            for record in applied_on:
                if self.x_psm_0211_vsattp_survey_id:
                    record.x_psm_0211_vsattp_survey_id = self.x_psm_0211_vsattp_survey_id
                # Gán ngày bắt đầu thử việc từ ngày chọn trong Launch Plan (mặc định hôm nay)
                record.x_psm_0211_probation_start_date = self.plan_date or fields.Date.today()
                # Chuyển trạng thái sang Thử việc (Probation) khi bắt đầu kế hoạch
                if record.x_psm_0211_onboarding_state == 'approved':
                    record.x_psm_0211_onboarding_state = 'probation'

        # 1. Gọi hành vi gốc của Odoo để hệ thống tạo Checklist (Activity) bình thường
        res = super().action_schedule_plan()
        
        # Odoo 17+ core creates activities, but we need to ensure they are in DB before searching
        self.env.flush_all()

        # 2. Xử lý thêm: Tạo bản ghi Task cho Dashboard Checklist
        if self.x_psm_0211_is_onboarding_plan:
            applied_on = self._get_applied_on_records()
            for record in applied_on:
                # Lấy các activity vừa được tạo dựa trên summary của Plan (do plan_template_id không tồn tại ở một số phiên bản)
                plan_summaries = self.plan_id.template_ids.mapped('summary')
                new_activities = self.env['mail.activity'].sudo().search([
                    ('res_model', '=', 'hr.employee'),
                    ('res_id', '=', record.id),
                    ('summary', 'in', plan_summaries),
                    ('activity_type_id', 'in', activity_type_ids)
                ])
                
                for activity in new_activities:
                    # QUY TẮC PHÂN CÔNG (ROLE-BASED ASSIGNMENT):
                    # Dựa vào Role được định nghĩa sẵn trong kịch bản (XML) để gán đúng người
                    template = self.plan_id.template_ids.filtered(lambda t: t.summary == activity.summary)[:1]
                    role = template.x_psm_0211_responsible_role if template else 'manager'
                    summary = (activity.summary or '').lower()

                    if record.x_psm_0211_staff_type == 'office':
                        if role == 'manager' and self.x_psm_0211_bp_user_id:
                            activity.sudo().user_id = self.x_psm_0211_bp_user_id.id
                        elif role == 'it' and self.plan_on_demand_user_id:
                            activity.sudo().user_id = self.plan_on_demand_user_id.id

                    # QUY TẮC CHO KHỐI VĂN PHÒNG (RST): Ẩn/Xoá VSATTP
                    if record.x_psm_0211_staff_type == 'office' and 'vsattp' in summary:
                        activity.unlink() # Xoá luôn activity để không vướng víu
                        continue

                    # Bỏ qua các activity training (đã có checklist riêng)
                    if 'đào tạo' in summary or 'hướng dẫn' in summary:
                        continue
                        
                    self.env['x_psm.hr.employee.onboarding.task'].sudo().create({
                        'employee_id': record.id,
                        'name': activity.summary or activity.activity_type_id.name,
                        'x_psm_date_planned': activity.date_deadline,
                        'x_psm_activity_id': activity.id,
                        'x_psm_is_done': False,
                    })

                record.action_psm_send_onboarding_plan_email(self)
                record.x_psm_0211_send_3P_notification_email(self)

        # 3. Tạo thông báo (Activity) lên đồng hồ cho Manager, BP và IT
        if self.x_psm_0211_is_onboarding_plan:
            applied_on = self._get_applied_on_records()
            today_tz = fields.Date.context_today(self)
            
            for record in applied_on:
                # 3.1 Thông báo cho Line Manager (Cả 2 khối)
                if record.parent_id and record.parent_id.user_id:
                    record.activity_schedule(
                        'mail.mail_activity_data_todo',
                        date_deadline=today_tz,
                        summary=f"Nhân viên mới: {record.name} đã được lên lịch Onboarding",
                        note=f"Nhân viên {record.name} đã được lên lịch bắt đầu Onboarding vào ngày {record.x_psm_0211_probation_start_date or 'N/A'}. Vui lòng theo dõi tiến độ.",
                        user_id=record.parent_id.user_id.id
                    )

                # 3.2 Thông báo cho BP/Phụ trách Onboarding (Khối RST)
                if record.x_psm_0211_staff_type == 'office' and self.x_psm_0211_bp_user_id:
                    record.activity_schedule(
                        'mail.mail_activity_data_todo',
                        date_deadline=today_tz,
                        summary=f"[MANAGER] Phụ trách Onboarding: {record.name}",
                        note=f"Kính gửi {self.x_psm_0211_bp_user_id.name},\n\n"
                             f"Bạn đã được chỉ định phụ trách lộ trình Onboarding cho nhân viên mới: {record.name}.\n"
                             f"- Ngày bắt đầu dự kiến: {record.x_psm_0211_probation_start_date or 'N/A'}\n"
                             f"- Các đầu việc bao gồm: Chuẩn bị nơi làm việc, bàn giao thiết bị và hướng dẫn định hướng.\n\n"
                             f"Vui lòng kiểm tra Checklist chi tiết tại hồ sơ nhân viên.",
                        user_id=self.x_psm_0211_bp_user_id.id
                    )

                # 3.3 Thông báo cho IT (Khối RST)
                if record.x_psm_0211_staff_type == 'office' and self.plan_on_demand_user_id:
                    record.activity_schedule(
                        'mail.mail_activity_data_todo',
                        date_deadline=today_tz,
                        summary=f"[IT] Yêu cầu chuẩn bị thiết bị: {record.name}",
                        note=f"Yêu cầu từ Phòng Nhân sự:\n\n"
                             f"Vui lòng chuẩn bị thiết bị (Laptop/PC) và khởi tạo các tài khoản hệ thống (Email, Odoo, v.v.) cho nhân sự mới:\n"
                             f"- Nhân viên: {record.name}\n"
                             f"- Khối: RST (Văn phòng)\n"
                             f"- Thời hạn hoàn thành: Trong vòng 48h từ khi nhận thông báo này.\n\n"
                             f"Sau khi hoàn tất, vui lòng cập nhật trạng thái trong Checklist Onboarding.",
                        user_id=self.plan_on_demand_user_id.id
                    )

        return res

    @api.depends('plan_date', 'plan_id', 'plan_on_demand_user_id', 'x_psm_0211_bp_user_id', 'res_model', 'res_ids')
    def _compute_plan_schedule_line_ids(self):
        # 1. Gọi logic gốc để lấy khung sườn
        super(MailActivitySchedule, self)._compute_plan_schedule_line_ids()
        
        for scheduler in self:
            if not (scheduler.x_psm_0211_is_onboarding_plan and scheduler.x_psm_0211_has_office_employee):
                continue
            
            # 2. Hiệu chỉnh lại người phụ trách (Responsible User) cho giao diện Preview
            # Tạo map Role cho các template để tra cứu nhanh
            template_roles = {t.summary: t.x_psm_0211_responsible_role for t in scheduler.plan_id.template_ids}
            
            for line in scheduler.plan_schedule_line_ids:
                # Tìm Role tương ứng với Summary của dòng Preview
                role = template_roles.get(line.line_description, 'manager')
                
                if role == 'manager' and scheduler.x_psm_0211_bp_user_id:
                    line.responsible_user_id = scheduler.x_psm_0211_bp_user_id.id
                elif role == 'it' and scheduler.plan_on_demand_user_id:
                    line.responsible_user_id = scheduler.plan_on_demand_user_id.id
