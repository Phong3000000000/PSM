from odoo import models, fields, api
from dateutil.relativedelta import relativedelta
import base64
from odoo.exceptions import UserError

class HrDisciplineRecord(models.Model):
    _name = "hr.discipline.record"
    _description = "Discipline Record"
    _inherit = ["portal.mixin", "mail.thread", "mail.activity.mixin"]
    _order = "date desc, id desc"

    name = fields.Char(
        string="Reference", required=True, copy=False, readonly=True, default="New"
    )
    employee_id = fields.Many2one(
        "hr.employee", string="Employee", required=True, tracking=True
    )
    violation_type_id = fields.Many2one(
        "hr.discipline.violation.type",
        string="Violation Type",
        required=True,
        tracking=True,
    )
    violation_category_id = fields.Many2one(
        related="violation_type_id.category_id",
        string="Violation Category",
        store=True,
        readonly=True,
    )
    description = fields.Text(string="Description / Explanation", required=True)
    date = fields.Date(
        string="Date", required=True, default=fields.Date.context_today, tracking=True
    )

    # Portal / Explanation Fields
    employee_explanation = fields.Text(string="Employee Explanation", tracking=True)
    explanation_date = fields.Date(string="Explanation Date")

    # Detailed Explanation Fields (Matching PDF Template)
    incident_date_time = fields.Datetime(string="Incident Time (By Employee)")
    incident_location = fields.Char(string="Incident Location")
    witness_names = fields.Char(string="Witnesses")
    explanation_reason = fields.Text(string="Reason/Cause")
    explanation_commitment = fields.Text(string="Commitment/Correction Plan")

    # Electronic Signature
    employee_signature = fields.Binary(
        string="Chữ ký nhân viên",
        help="Chữ ký điện tử của nhân viên khi gửi tường trình",
    )

    # Explanation History
    explanation_ids = fields.One2many(
        "hr.discipline.explanation",
        "record_id",
        string="Lịch sử tường trình",
    )

    active_explanation_id = fields.Many2one(
        "hr.discipline.explanation",
        string="Tường trình hiện tại",
        compute="_compute_active_explanation",
        store=True,
    )

    explanation_count = fields.Integer(
        compute="_compute_explanation_count", string="Số lần tường trình"
    )

    @api.depends("explanation_ids", "explanation_ids.state")
    def _compute_active_explanation(self):
        for rec in self:
            active = rec.explanation_ids.filtered(
                lambda e: e.state in ["submitted", "accepted"]
            )
            rec.active_explanation_id = active[0] if active else False

    @api.depends("explanation_ids")
    def _compute_explanation_count(self):
        for rec in self:
            rec.explanation_count = len(rec.explanation_ids)

    action_id = fields.Many2one(
        "hr.discipline.action",
        string="Proposed Action",
        tracking=True,
        help="Automatically suggested by the system based on history.",
    )

    previous_record_id = fields.Many2one(
        "hr.discipline.record",
        string="Previous Offense Link",
        readonly=True,
        help="Linked to a previous offense if this is an escalation.",
    )

    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("waiting_explanation", "Chờ Tường Trình"),
            ("manager_review", "Manager Review"),
            ("rgm_decision", "RGM Quyết Định"),
            ("store_discipline", "Store Level KL"),
            ("hr_meeting", "HR Meeting"),
            ("ceo_approve", "CEO Approve"),
            ("improving", "Đang Cải Thiện"),
            ("done", "Done"),
            ("archived", "Archived"),
            ("cancel", "Cancelled"),
        ],
        string="Status",
        default="draft",
        tracking=True,
        group_expand="_group_expand_states",
    )

    @api.model
    def _group_expand_states(self, states, domain, order=None):
        return [key for key, val in type(self).state.selection]

    # Discipline Level (Store vs Company)
    discipline_level = fields.Selection(
        [
            ("store", "Store Level"),
            ("company", "Company Level"),
        ],
        string="Cấp độ xử lý",
        tracking=True,
    )

    # Repeat Offense Detection
    is_repeat_offense = fields.Boolean(
        compute="_compute_repeat_offense",
        store=True,
        string="Tái phạm",
    )
    related_records_count = fields.Integer(
        compute="_compute_repeat_offense",
        store=True,
        string="Số lần vi phạm trước",
    )

    # Improvement Period
    improvement_start_date = fields.Date(string="Ngày bắt đầu cải thiện")
    improvement_end_date = fields.Date(string="Ngày kết thúc cải thiện")

    days_improving_remaining = fields.Integer(
        compute="_compute_days_improving_remaining",
        string="Ngày cải thiện còn lại",
        help="Số ngày còn lại trong quá trình cải thiện.",
    )

    @api.depends("state", "improvement_end_date")
    def _compute_days_improving_remaining(self):
        for rec in self:
            if rec.state == "improving" and rec.improvement_end_date:
                today = fields.Date.today()
                delta = (rec.improvement_end_date - today).days
                # If negative (overdue), show 0
                rec.days_improving_remaining = max(0, delta)
            else:
                rec.days_improving_remaining = 0

    # Meeting Integration
    meeting_count = fields.Integer(compute="_compute_meeting_count")

    def _compute_meeting_count(self):
        for rec in self:
            rec.meeting_count = self.env["calendar.event"].search_count(
                [("res_model", "=", self._name), ("res_id", "=", rec.id)]
            )

    def action_schedule_meeting(self):
        self.ensure_one()
        return {
            "name": "Discipline Meeting",
            "type": "ir.actions.act_window",
            "res_model": "calendar.event",
            "view_mode": "list,form,calendar",
            "domain": [("res_model", "=", self._name), ("res_id", "=", self.id)],
            "context": {
                "default_name": f"Họp xử lý kỷ luật: {self.employee_id.name}",
                "default_res_model": self._name,
                "default_res_id": self.id,
                "default_partner_ids": (
                    [self.employee_id.user_id.partner_id.id]
                    if self.employee_id.user_id
                    else []
                ),
            },
        }

    # Meeting Info (for Company Level)
    latest_meeting_id = fields.Many2one(
        "calendar.event", string="Cuộc họp mới nhất", compute="_compute_latest_meeting"
    )
    meeting_date = fields.Datetime(
        string="Ngày họp", compute="_compute_latest_meeting", store=True, readonly=False
    )
    meeting_notes = fields.Text(string="Nội dung họp")
    meeting_attachment = fields.Binary(string="Biên bản họp")
    meeting_attachment_filename = fields.Char(string="Tên file biên bản")

    @api.depends("meeting_count")  # Re-compute when meeting count changes
    def _compute_latest_meeting(self):
        for rec in self:
            # Filter meetings linked SPECIFICALLY to this discipline record
            meeting = self.env["calendar.event"].search(
                [
                    ("res_model", "=", self._name),
                    ("res_id", "=", rec.id),
                ],
                order="start desc",
                limit=1,
            )
            rec.latest_meeting_id = meeting
            # Only auto-update date if not set, or update it to match latest meeting?
            # User wants "take latest meeting date".
            if meeting:
                rec.meeting_date = meeting.start
            elif not rec.meeting_date:
                # Keep existing if manually set, or clear?
                # Let's clear if no meeting linked, but allow manual override if store=True/readonly=False logic permits.
                # Actually with compute+store, it only updates when dependencies change.
                pass

    # Compensation (Finance)
    has_compensation = fields.Boolean(string="Có bồi thường", tracking=True)
    compensation_amount = fields.Monetary(
        string="Giá trị bồi thường", currency_field="currency_id", tracking=True
    )
    currency_id = fields.Many2one(
        "res.currency",
        string="Currency",
        default=lambda self: self.env.company.currency_id,
    )

    # Decision Attachments
    disciplinary_decision_attachment = fields.Binary(string="Quyết định xử lý kỷ luật")
    disciplinary_decision_filename = fields.Char(string="Filename kỷ luật")

    compensation_decision_attachment = fields.Binary(string="Quyết định đền bù")
    compensation_decision_filename = fields.Char(string="Filename đền bù")

    @api.depends("employee_id")
    def _compute_repeat_offense(self):
        for rec in self:
            if not rec.employee_id:
                rec.is_repeat_offense = False
                rec.related_records_count = 0
                continue

            related_count = self.search_count(
                [
                    ("employee_id", "=", rec.employee_id.id),
                    ("id", "!=", rec._origin.id or rec.id),
                    ("state", "in", ["improving", "done"]),
                ]
            )
            rec.related_records_count = related_count
            rec.is_repeat_offense = related_count > 0

    # --- AUTO-ESCALATION LOGIC ---
    @api.onchange("employee_id", "date")
    def _compute_suggested_action(self):
        for rec in self:
            if not rec.employee_id or not rec.date:
                continue

            last_record = self.env["hr.discipline.record"].search(
                [
                    ("employee_id", "=", rec.employee_id.id),
                    ("state", "=", "done"),
                    ("date", "<", rec.date),
                    ("id", "!=", rec.id),
                ],
                order="date desc",
                limit=1,
            )

            if last_record and last_record.action_id.validity_months > 0:
                expire_date = last_record.date + relativedelta(
                    months=last_record.action_id.validity_months
                )

                if rec.date <= expire_date:
                    if last_record.action_id.next_action_id:
                        rec.action_id = last_record.action_id.next_action_id
                        rec.previous_record_id = last_record.id
                    else:
                        rec.action_id = last_record.action_id
                else:
                    first_action = self.env["hr.discipline.action"].search(
                        [], order="sequence asc", limit=1
                    )
                    rec.action_id = first_action
            else:
                first_action = self.env["hr.discipline.action"].search(
                    [], order="sequence asc", limit=1
                )
                rec.action_id = first_action

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", "New") == "New":
                vals["name"] = (
                    self.env["ir.sequence"].next_by_code("hr.discipline.record")
                    or "New"
                )
        return super().create(vals_list)

    # --- PORTAL ACTIONS ---
    def action_send_to_employee(self):
        """Action for Manager to request explanation from Employee"""
        self.ensure_one()
        self.state = "waiting_explanation"

        # Send Email
        template = self.env.ref(
            "M02_P0215_00.email_template_ask_explanation", raise_if_not_found=False
        )
        if template:
            template.send_mail(self.id, force_send=True)

        # Schedule Activity
        if self.employee_id.user_id:
            self.activity_schedule(
                "mail.mail_activity_data_todo",
                user_id=self.employee_id.user_id.id,
                summary="Action Required: Provide Explanation",
                note="Please submit your explanation via the employee portal.",
            )

    def _get_portal_url(self):
        return f"/my/discipline/{self.id}"

    # --- WORKFLOW BUTTONS ---

    def action_confirm(self):
        """Manager approves the explanation - determine next step"""
        for rec in self:
            # Mark current explanation as accepted
            if rec.active_explanation_id:
                rec.active_explanation_id.write(
                    {
                        "state": "accepted",
                        "reviewed_date": fields.Datetime.now(),
                        "reviewed_by": self.env.uid,
                    }
                )

            # Auto-Classify Logic
            is_minor = rec.violation_type_id.severity == "minor"
            is_first = not rec.is_repeat_offense

            if is_minor and is_first:
                # Minor first offense → Done directly with Feedback
                # Try to find 'Feedback' action
                feedback_action = self.env.ref(
                    "M02_P0215_00.action_feedback", raise_if_not_found=False
                )
                if feedback_action:
                    rec.action_id = feedback_action
                rec.state = "done"
            else:
                # Severe or repeat → RGM decides
                rec.state = "rgm_decision"

    def action_reject_explanation(self):
        """Reject current explanation and request a new one"""
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": "Lý do từ chối",
            "res_model": "hr.discipline.reject.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {"default_record_id": self.id},
        }

    def action_rgm_store_level(self):
        """RGM decides Store Level handling"""
        self.write(
            {
                "discipline_level": "store",
                "state": "store_discipline",
            }
        )

    def action_rgm_company_level(self):
        """RGM decides Company Level handling"""
        self.write(
            {
                "discipline_level": "company",
                "state": "hr_meeting",
            }
        )

    def action_store_confirm(self):
        """Store Manager confirms discipline and starts improvement"""
        for rec in self:
            rec.improvement_start_date = fields.Date.today()
            # Calculate end date based on action's improvement period
            if rec.action_id and rec.action_id.improvement_period:
                rec.improvement_end_date = fields.Date.today() + relativedelta(
                    days=rec.action_id.improvement_period
                )
            rec.state = "improving"

    def _get_report_by_name_strict(self, report_name):
        return self.env["ir.actions.report"].search(
            [("report_name", "=", report_name), ("model", "=", self._name)],
            order="id desc",
            limit=1,
        )

    def action_generate_disciplinary_decision(self):
        self.ensure_one()
        report = self._get_report_by_name_strict(
            "M02_P0215_00.report_disciplinary_decision_template"
        )

        if not report:
            raise UserError(
                "LỖI CẤU HÌNH: Không tìm thấy mẫu báo cáo 'Quyết định Xử lý kỷ luật'.\n"
                "Giải pháp: Hãy vào Settings -> Reports -> Tìm 'Quyết định Xử lý kỷ luật'.\n"
                "Nếu không thấy, hãy upgrade lại module."
            )

        # Render with list of IDs to be safe
        pdf_content, _ = report._render_qweb_pdf(report.id, [self.id])
        self.disciplinary_decision_attachment = base64.b64encode(pdf_content)
        self.disciplinary_decision_filename = f"Quyet_dinh_ky_luat_{self.name}.pdf"

    def action_generate_compensation_decision(self):
        self.ensure_one()
        report = self._get_report_by_name_strict(
            "M02_P0215_00.report_compensation_decision_template"
        )

        if not report:
            raise UserError(
                "LỖI CẤU HÌNH: Không tìm thấy mẫu báo cáo 'Quyết định Bồi thường'.\n"
                "Giải pháp: Hãy vào Settings -> Reports -> Tìm 'Quyết định Bồi thường'.\n"
                "Nếu không thấy, hãy upgrade lại module."
            )

        # Render with list of IDs to be safe
        pdf_content, _ = report._render_qweb_pdf(report.id, [self.id])
        self.compensation_decision_attachment = base64.b64encode(pdf_content)
        self.compensation_decision_filename = f"Quyet_dinh_boi_thuong_{self.name}.pdf"

    def action_hr_submit_meeting(self):
        """HR submits meeting results for CEO approval"""
        for rec in self:
            if not rec.disciplinary_decision_attachment:
                raise UserError(
                    "Vui lòng tạo 'Quyết định xử lý kỷ luật' trước khi trình CEO."
                )
            if rec.has_compensation and not rec.compensation_decision_attachment:
                raise UserError("Vui lòng tạo 'Quyết định đền bù' trước khi trình CEO.")
        self.write({"state": "ceo_approve"})

    def action_ceo_approve(self):
        """CEO approves the discipline decision"""
        for rec in self:
            rec.improvement_start_date = fields.Date.today()
            if rec.action_id and rec.action_id.improvement_period:
                rec.improvement_end_date = fields.Date.today() + relativedelta(
                    days=rec.action_id.improvement_period
                )
            rec.state = "improving"

    def action_ceo_reject(self):
        """CEO rejects - back to HR meeting"""
        self.write({"state": "hr_meeting"})

    def action_complete_improvement(self):
        """Complete improvement period → Done"""
        for rec in self:
            rec.write({"state": "done"})
            # Send completion email
            template = self.env.ref(
                "M02_P0215_00.email_template_discipline_done", raise_if_not_found=False
            )
            if template and rec.employee_id.work_email:
                template.send_mail(rec.id, force_send=True)

    def action_done(self):
        """Mark as Done"""
        self.write({"state": "done"})

    def action_cancel(self):
        """Cancel the record"""
        self.write({"state": "cancel"})

    def _cron_auto_archive(self):
        """Auto archive records that have been in 'done' state for 3 months"""
        three_months_ago = fields.Date.today() - relativedelta(months=3)
        records_to_archive = self.search(
            [
                ("state", "=", "done"),
                ("write_date", "<=", three_months_ago),
            ]
        )
        if records_to_archive:
            records_to_archive.write({"state": "archived"})

    def _cron_auto_complete_improvement(self):
        """Auto complete records where improvement period has ended"""
        today = fields.Date.today()
        # Find records where state is improving AND end date is less than today
        records_to_complete = self.search(
            [
                ("state", "=", "improving"),
                ("improvement_end_date", "<", today),
            ]
        )
        for rec in records_to_complete:
            rec.action_complete_improvement()
