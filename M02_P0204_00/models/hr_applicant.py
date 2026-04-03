# -*- coding: utf-8 -*-
"""
Extend HR Applicant
Thêm các trường liên quan đến lịch phỏng vấn và khảo sát
"""

from odoo import models, fields, api, exceptions, _, SUPERUSER_ID
from odoo.exceptions import AccessError
from odoo.modules.registry import Registry
from datetime import timedelta
import re
import logging
import base64
import threading

_logger = logging.getLogger(__name__)


def _send_background_task(db_name, mail_id):
    """Task executed in a background thread to send the mail immediately."""
    try:
        db_registry = Registry(db_name)
        with db_registry.cursor() as cr:
            env = api.Environment(cr, SUPERUSER_ID, {})
            mail = env['mail.mail'].browse(mail_id)
            if mail.exists():
                mail.send(raise_exception=False, auto_commit=True)
                _logger.info("[ASYNC_MAIL] Background thread successfully sent mail id=%s", mail_id)
    except Exception as e:
        _logger.error("[ASYNC_MAIL] Background thread failed for mail id=%s: %s", mail_id, str(e))


class HrApplicant(models.Model):
    _inherit = "hr.applicant"

    # ====================BRAND & SCHEDULE ====================

    company_id = fields.Many2one(
        "res.company", string="Brand", tracking=True, help="Brand mà ứng viên ứng tuyển"
    )

    department_id = fields.Many2one(
        "hr.department", string="Phòng ban", tracking=True, help="Phòng ban / Cửa hàng cụ thể"
    )

    recruitment_type = fields.Selection(
        related="job_id.recruitment_type",
        string="Loại Tuyển Dụng",
        store=True,
        readonly=True,
        tracking=True,
        help="Loại tuyển dụng được kế thừa từ Job Position",
    )

    position_level = fields.Selection(
        related="job_id.position_level",
        string="Cấp Bậc",
        store=True,
        readonly=True,
        tracking=True,
        help="Cấp bậc xác định pipeline (Management/Staff)",
    )

    stage_filter_type = fields.Char(
        compute="_compute_stage_filter_type",
        store=False,
        help="Dùng để lọc stage dropdown: store dùng position_level, office dùng 'office'",
    )

    def _get_pipeline_stage_type(self):
        """Return the stage type key for pipeline filtering.
        Store jobs use position_level (staff/management).
        Office jobs always use 'office'.
        """
        self.ensure_one()
        if self.recruitment_type == 'store':
            return self.position_level or 'store'
        return self.recruitment_type or False

    @api.depends("position_level", "recruitment_type")
    def _compute_stage_filter_type(self):
        for rec in self:
            rec.stage_filter_type = rec._get_pipeline_stage_type()

    interview_schedule_id = fields.Many2one(
        "interview.schedule",
        string="Lịch Phỏng Vấn",
        help="Lịch PV đã được duyệt của brand",
        tracking=True,
    )

    available_department_ids = fields.Many2many(
        "hr.department",
        compute="_compute_available_departments",
        string="Phòng ban có sẵn lịch",
    )

    @api.depends("department_id")
    def _compute_available_departments(self):
        """Tính toán danh sách phòng ban có lịch PV đã xác nhận trong tuần này"""
        today = fields.Date.today()
        # Tìm Thứ Hai tuần này
        monday = today - timedelta(days=today.weekday())
        
        # Chỉ lấy các department_id từ schedules đã xác nhận của tuần này
        schedules = self.env["interview.schedule"].search([
            ("state", "=", "confirmed"),
            ("week_start_date", "=", monday)
        ])
        available_depts = schedules.mapped("department_id")
        
        for rec in self:
            rec.available_department_ids = available_depts

    @api.depends('job_id')
    def _compute_stage(self):
        super()._compute_stage()
        for applicant in self:
            if applicant.job_id and applicant.job_id.recruitment_type:
                # Odoo mặc định lấy stage đầu tiên không cần biết recruitment_type.
                # Do đó, ghi đè lại nếu stage hiện tại (Odoo tự gán) không khớp recruitment_type của job.
                current_stage = applicant.stage_id
                if not current_stage or current_stage.recruitment_type != applicant.job_id.recruitment_type:
                    stage_type = applicant._get_pipeline_stage_type()
                    correct_stage = self.env['hr.recruitment.stage'].search([
                        ('recruitment_type', '=', stage_type),
                        ('fold', '=', False)
                    ], order='sequence asc', limit=1)
                    if correct_stage:
                        applicant.stage_id = correct_stage.id

    @api.model
    def _get_target_pipeline_stage(self, stage_name, recruitment_type='store', position_level='staff'):
        """Helper tiêu chuẩn tìm stage theo dạng fallback, giảm lặp code."""
        domain = [('name', '=', stage_name)]
        if recruitment_type == 'store':
            stage_type = position_level or 'staff'
            domain.append(('recruitment_type', 'in', [stage_type, 'both']))
        else:
            domain.append(('recruitment_type', 'in', ['office', 'both']))
            
        stage = self.env['hr.recruitment.stage'].sudo().search(domain, order='sequence asc', limit=1)
        if not stage:
            stage = self.env['hr.recruitment.stage'].sudo().search([('name', '=', stage_name)], order='sequence asc', limit=1)
        return stage

    # ==================== SURVEY ====================

    pre_interview_survey_id = fields.Many2one(
        "survey.survey",
        string="Khảo Sát",
        domain=[("is_pre_interview", "=", True)],
        help="Khảo sát trước phỏng vấn gửi cho ứng viên",
    )

    survey_user_input_id = fields.Many2one(
        "survey.user_input",
        string="Survey Input",
        copy=False,
        readonly=True,
        help="Bản ghi khảo sát cá nhân hóa cho ứng viên này",
    )

    survey_url = fields.Char(
        string="Link Khảo Sát",
        copy=False,
        help="Link cá nhân hóa cho ứng viên điền khảo sát",
    )

    survey_state = fields.Selection(
        related="survey_user_input_id.state",
        string="Trạng Thái Survey",
        store=False,
        readonly=True,
    )

    survey_scoring_percentage = fields.Float(
        related="survey_user_input_id.scoring_percentage",
        string="Điểm Survey (%)",
        store=False,
        readonly=True,
    )

    survey_scoring_success = fields.Boolean(
        related="survey_user_input_id.scoring_success",
        string="Đạt Survey",
        store=False,
        readonly=True,
    )

    survey_result_url = fields.Char(
        string='Survey result URL', 
        help='Link xem kết quả bài khảo sát của ứng viên'
    )

    # ==================== APPLICATION MATCH RESULT (NEW) ====================
    application_match_result = fields.Selection([
        ('passed', 'Đạt yêu cầu'),
        ('failed', 'Cần xem xét')
    ], string="Kết quả biểu mẫu", compute="_compute_application_match_result", store=True)

    failed_mandatory_questions = fields.Html(string="Sai câu bắt buộc (Thông tin chung)", readonly=True)
    
    application_answer_line_ids = fields.One2many(
        'hr.applicant.application.answer.line', 'applicant_id',
        string='Lịch sử trả lời biểu mẫu', readonly=True
    )

    @api.depends('failed_mandatory_questions')
    def _compute_application_match_result(self):
        for rec in self:
            # Chỉ check lỗi từ biểu mẫu ứng tuyển (Master fields)
            if rec.failed_mandatory_questions and '<ul>' in str(rec.failed_mandatory_questions):
                rec.application_match_result = 'failed'
            else:
                rec.application_match_result = 'passed'

    def action_show_failed_questions(self):
        self.ensure_one()
        # View popup wizard or fallback
        view_id = self.env.ref('M02_P0204_00.view_hr_applicant_application_result_popup', raise_if_not_found=False)
        if view_id:
            return {
                'name': 'Chi tiết biểu mẫu ứng tuyển',
                'type': 'ir.actions.act_window',
                'res_model': 'hr.applicant',
                'res_id': self.id,
                'view_mode': 'form',
                'view_id': view_id.id,
                'target': 'new',
                'context': {**self.env.context, 'dialog_size': 'extra-large'},
            }
        
        # Fallback if view doesn't exist yet
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Trạng thái',
                'message': 'Đã có kết quả biểu mẫu. Vui lòng kiểm tra màn hình chi tiết.',
                'type': 'info',
            }
        }

    # ==================== OJE EVALUATION (DYNAMIC) ====================

    oje_evaluator_user_id = fields.Many2one(
        "res.users",
        string="Người đánh giá OJE",
        index=True,
        tracking=True,
        help="Người chịu trách nhiệm đánh giá OJE cho ứng viên này (Snapshot từ Job)",
    )

    oje_evaluation_id = fields.Many2one(
        "hr.applicant.oje.evaluation",
        string="Phiếu Đánh Giá OJE",
        copy=False,
        readonly=True,
    )

    oje_evaluation_state = fields.Selection(
        related="oje_evaluation_id.state",
        string="Trạng Thái OJE",
        store=True,
    )

    can_backend_evaluate_oje = fields.Boolean(
        compute='_compute_can_backend_evaluate_oje',
        string='Có thể đánh giá OJE trên backend'
    )

    @api.depends('oje_evaluator_user_id', 'current_stage_name', 'oje_evaluation_state', 'job_id')
    def _compute_can_backend_evaluate_oje(self):
        user = self.env.user
        is_admin = user.has_group('base.group_system')
        for rec in self:
            rec.can_backend_evaluate_oje = bool(
                rec.job_id
                and rec.current_stage_name in ('Interview & OJE', 'OJE')
                and rec.oje_evaluation_state != 'done'
                and (
                    is_admin
                    or (rec.oje_evaluator_user_id and rec.oje_evaluator_user_id == user)
                )
            )

    def _check_backend_oje_access(self, user=False):
        self.ensure_one()
        current_user = user or self.env.user
        applicant = self.sudo()

        if current_user.has_group('base.group_system'):
            return True
        if applicant.oje_evaluator_user_id and current_user == applicant.oje_evaluator_user_id:
            return True

        # Portal manager fallback: allow DM hierarchy to access applicant in managed departments.
        if getattr(current_user, 'x_is_portal_manager', False):
            employee = self.env['hr.employee'].sudo().search([('user_id', '=', current_user.id)], limit=1)
            if employee:
                dept_domain = ['|', '|', '|',
                    ('id', '=', employee.department_id.id),
                    ('manager_id', '=', employee.id),
                    ('parent_id.manager_id', '=', employee.id),
                    ('parent_id.parent_id.manager_id', '=', employee.id),
                ]
            else:
                dept_domain = ['|', '|',
                    ('manager_id.user_id', '=', current_user.id),
                    ('parent_id.manager_id.user_id', '=', current_user.id),
                    ('parent_id.parent_id.manager_id.user_id', '=', current_user.id),
                ]

            managed_departments = self.env['hr.department'].sudo().search(dept_domain)
            applicant_department = applicant.department_id or applicant.job_id.department_id
            if applicant_department and applicant_department in managed_departments:
                return True

        raise AccessError(_("Bạn không có quyền đánh giá OJE cho ứng viên này."))

    def _is_oje_stage_allowed(self):
        self.ensure_one()
        return self.current_stage_name in ('Interview & OJE', 'OJE')

    def _get_oje_snapshot_source(self):
        self.ensure_one()
        template_scope = 'legacy'
        if hasattr(self.job_id, '_get_oje_template_scope'):
            template_scope = self.job_id._get_oje_template_scope() or 'legacy'

        job_active_sections = self.job_id.oje_config_section_ids.filtered(
            lambda s: s.is_active and (not s.scope or s.scope == template_scope)
        ).sorted('sequence')

        template_version = False
        master_section = job_active_sections.filtered(lambda s: s.source_template_section_id)[:1]
        if master_section and master_section.source_template_section_id.template_id:
            template_version = master_section.source_template_section_id.template_id.version

        if not template_version:
            template_version = '1.0'

        return template_scope, template_version, job_active_sections

    def _populate_oje_evaluation_snapshot(self, evaluation, template_scope, job_active_sections):
        self.ensure_one()
        line_vals = []

        if job_active_sections and template_scope in ('store_staff', 'store_management'):
            for config_section in job_active_sections:
                eval_section = self.env['hr.applicant.oje.evaluation.section'].create({
                    'evaluation_id': evaluation.id,
                    'source_config_section_id': config_section.id,
                    'sequence': config_section.sequence,
                    'name': config_section.name,
                    'section_kind': config_section.section_kind,
                    'scope': config_section.scope,
                    'rating_mode': config_section.rating_mode,
                    'objective_text': config_section.objective_text,
                    'hint_html': config_section.hint_html,
                    'behavior_html': config_section.behavior_html,
                    'is_active': config_section.is_active,
                })

                for config_line in config_section.line_ids.filtered('is_active').sorted('sequence'):
                    line_vals.append({
                        'evaluation_id': evaluation.id,
                        'section_id': eval_section.id,
                        'template_line_id': config_line.id,
                        'sequence': config_line.sequence,
                        'name': config_line.name or config_line.question_text,
                        'question_text': config_line.question_text or config_line.name,
                        'line_kind': config_line.line_kind or 'legacy',
                        'scope': config_line.scope,
                        'rating_mode': config_line.rating_mode,
                        'is_required': config_line.is_required,
                        'is_active': config_line.is_active,
                        'field_type': config_line.field_type,
                        'text_max_score': config_line.text_max_score,
                        'checkbox_score': config_line.checkbox_score,
                    })
        else:
            legacy_lines = self.job_id.oje_config_line_ids.filtered('is_active').sorted('sequence')
            for config_line in legacy_lines:
                line_vals.append({
                    'evaluation_id': evaluation.id,
                    'template_line_id': config_line.id,
                    'name': config_line.name,
                    'question_text': config_line.question_text or config_line.name,
                    'line_kind': config_line.line_kind or 'legacy',
                    'scope': config_line.scope,
                    'rating_mode': config_line.rating_mode,
                    'is_required': config_line.is_required,
                    'is_active': config_line.is_active,
                    'field_type': config_line.field_type,
                    'text_max_score': config_line.text_max_score,
                    'checkbox_score': config_line.checkbox_score,
                    'sequence': config_line.sequence,
                })

        if line_vals:
            self.env['hr.applicant.oje.evaluation.line'].create(line_vals)

    def _ensure_oje_evaluation(self, evaluator_user=None):
        self.ensure_one()

        if not self.job_id:
            raise exceptions.UserError(_("Ứng viên chưa có Job Position."))

        if not self.job_id.oje_config_line_ids and not self.job_id.oje_config_section_ids:
            raise exceptions.UserError(_("Job chưa có cấu hình OJE."))

        evaluator = evaluator_user or self.oje_evaluator_user_id or self.env.user

        template_scope, template_version, job_active_sections = self._get_oje_snapshot_source()

        if self.oje_evaluation_id:
            evaluation = self.oje_evaluation_id

            if evaluation.state != 'done' and template_scope in ('store_staff', 'store_management'):
                has_scope_sections = bool(evaluation.section_ids.filtered(
                    lambda s: s.is_active and s.section_kind in ('staff_block', 'management_dimension', 'management_xfactor')
                ))
                has_scope_lines = bool(evaluation.line_ids.filtered(
                    lambda l: l.is_active and l.line_kind in ('staff_question', 'management_task', 'management_xfactor')
                ))

                needs_refresh = bool(
                    evaluation.template_scope != template_scope
                    or not has_scope_sections
                    or not has_scope_lines
                )

                if needs_refresh:
                    evaluation.line_ids.unlink()
                    evaluation.section_ids.unlink()
                    evaluation.write({
                        'template_scope': template_scope,
                        'template_version': template_version,
                        'pass_score_snapshot': self.job_id.oje_pass_score,
                        'evaluator_user_id': evaluator.id,
                        'trial_date': evaluation.trial_date or fields.Date.today(),
                        'restaurant_name': evaluation.restaurant_name or self.department_id.name or self.job_id.department_id.name,
                        'operation_consultant_name': evaluation.operation_consultant_name or evaluator.name,
                    })
                    self._populate_oje_evaluation_snapshot(evaluation, template_scope, job_active_sections)

            return evaluation

        evaluation = self.env['hr.applicant.oje.evaluation'].create({
            'applicant_id': self.id,
            'job_id': self.job_id.id,
            'evaluator_user_id': evaluator.id,
            'pass_score_snapshot': self.job_id.oje_pass_score,
            'state': 'in_progress',
            'template_scope': template_scope,
            'template_version': template_version,
            'trial_date': fields.Date.today(),
            'restaurant_name': self.department_id.name or self.job_id.department_id.name,
            'operation_consultant_name': evaluator.name,
        })
        self._populate_oje_evaluation_snapshot(evaluation, template_scope, job_active_sections)

        self.write({'oje_evaluation_id': evaluation.id})
        return evaluation

    def action_open_backend_oje_evaluation(self):
        self.ensure_one()
        self._check_backend_oje_access()

        if not self._is_oje_stage_allowed():
            raise exceptions.UserError(_("Chỉ có thể đánh giá OJE khi ứng viên đang ở stage Interview & OJE hoặc OJE."))

        evaluation = self._ensure_oje_evaluation(evaluator_user=self.env.user)

        if evaluation.template_scope in ('store_staff', 'store_management'):
            return {
                'type': 'ir.actions.act_url',
                'name': _('Pass OJE'),
                'url': f'/recruitment/oje/internal/{evaluation.id}',
                'target': 'new',
            }

        if evaluation.state == 'done':
            view = self.env.ref('M02_P0204_00.hr_applicant_oje_evaluation_view_form')
        else:
            view = self.env.ref('M02_P0204_00.hr_applicant_oje_evaluation_view_form_edit')

        return {
            'type': 'ir.actions.act_window',
            'name': _('Pass OJE'),
            'res_model': 'hr.applicant.oje.evaluation',
            'res_id': evaluation.id,
            'view_mode': 'form',
            'views': [(view.id, 'form')],
            'target': 'current',
        }

    reject_reason = fields.Text(string="Lý do từ chối", tracking=True)

    refuse_reason_m2m_ids = fields.Many2many(
        'hr.applicant.refuse.reason',
        string="Chi tiết lý do từ chối",
        tracking=True,
    )

    oje_total_score = fields.Float(
        related="oje_evaluation_id.total_score",
        string="Tổng Điểm OJE",
        store=True,
    )

    oje_result = fields.Selection(
        related="oje_evaluation_id.result",
        string="Kết Quả OJE",
        store=True,
    )

    oje_evaluated_by = fields.Many2one(
        related="oje_evaluation_id.evaluator_user_id",
        string="Người Đánh Giá",
        store=True,
    )

    oje_evaluated_at = fields.Datetime(
        related="oje_evaluation_id.submitted_at",
        string="Ngày Đánh Giá",
        store=True,
    )

    oje_pass_score_snapshot = fields.Float(
        related="oje_evaluation_id.pass_score_snapshot",
        string="Điểm Đạt OJE",
        store=True,
    )

    oje_template_scope = fields.Selection(
        related="oje_evaluation_id.template_scope",
        string="Scope OJE",
        store=True,
    )

    oje_staff_decision = fields.Selection(
        related="oje_evaluation_id.staff_decision",
        string="Kết luận Staff",
        store=True,
    )

    oje_staff_ni_count = fields.Integer(
        related="oje_evaluation_id.staff_ni_count",
        string="NI",
        store=True,
    )
    oje_staff_gd_count = fields.Integer(
        related="oje_evaluation_id.staff_gd_count",
        string="GD",
        store=True,
    )
    oje_staff_ex_count = fields.Integer(
        related="oje_evaluation_id.staff_ex_count",
        string="EX",
        store=True,
    )
    oje_staff_os_count = fields.Integer(
        related="oje_evaluation_id.staff_os_count",
        string="OS",
        store=True,
    )

    oje_management_overall_rating = fields.Integer(
        related="oje_evaluation_id.management_overall_rating",
        string="Overall Rating",
        store=True,
    )

    oje_fail_reason = fields.Text(
        string="Lý do không đạt OJE",
        copy=False,
    )

    # Legacy OJE Survey Fields
    oje_survey_id = fields.Many2one(
        "survey.survey",
        string="Phiếu Đánh Giá OJE (Legacy)",
    )

    oje_survey_user_input_id = fields.Many2one(
        "survey.user_input",
        string="OJE Survey Input (Legacy)",
        copy=False,
        readonly=True,
    )

    oje_survey_url = fields.Char(
        string="Link Đánh Giá OJE (Legacy)",
        copy=False,
    )

    oje_survey_state = fields.Selection(
        related="oje_survey_user_input_id.state",
        string="Trạng Thái OJE (Legacy)",
        readonly=True,
    )

    oje_survey_scoring_percentage = fields.Float(
        related="oje_survey_user_input_id.scoring_percentage",
        string="Điểm OJE (%) (Legacy)",
        readonly=True,
    )

    oje_survey_scoring_success = fields.Boolean(
        related="oje_survey_user_input_id.scoring_success",
        string="Đạt OJE (Legacy)",
        readonly=True,
    )

    # ==================== SURVEY STAT BUTTONS ====================

    survey_display_text = fields.Char(compute="_compute_survey_display")
    survey_display_result = fields.Char(compute="_compute_survey_display")
    oje_display_text = fields.Char(compute="_compute_oje_display")
    oje_display_result = fields.Char(compute="_compute_oje_display")

    def _compute_survey_display(self):
        for rec in self:
            rec.survey_display_result = "Khảo sát"
            if not rec.survey_user_input_id:
                rec.survey_display_text = "Chưa có"
                continue

            state = rec.survey_state
            if state == "new":
                rec.survey_display_text = "Chưa làm"
            elif state == "in_progress":
                rec.survey_display_text = "Đang làm"
            elif state == "done":
                rec.survey_display_text = "Đã làm"
            else:
                rec.survey_display_text = "N/A"

    def _compute_oje_display(self):
        for rec in self:
            rec.oje_display_result = "Đánh giá OJE"
            if not rec.oje_evaluation_id:
                # Fallback legacy
                if rec.oje_survey_user_input_id:
                    state = rec.oje_survey_state
                    if state == "new":
                        rec.oje_display_text = "Chưa làm (Old)"
                    elif state == "in_progress":
                        rec.oje_display_text = "Đang làm (Old)"
                    elif state == "done":
                        score = int(rec.oje_survey_scoring_percentage)
                        success = "✓" if rec.oje_survey_scoring_success else "✗"
                        rec.oje_display_text = f"{score}% {success} (Old)"
                    else:
                        rec.oje_display_text = "N/A"
                else:
                    rec.oje_display_text = "Chưa có"
                continue

            state = rec.oje_evaluation_state
            if state == "new":
                rec.oje_display_text = "Chưa làm"
            elif state == "in_progress":
                rec.oje_display_text = "Đang làm"
            elif state == "done":
                success = "✓" if rec.oje_result == 'pass' else "✗"
                if rec.oje_template_scope == 'store_staff':
                    rec.oje_display_text = (
                        f"NI:{rec.oje_staff_ni_count} GD:{rec.oje_staff_gd_count} "
                        f"EX:{rec.oje_staff_ex_count} OS:{rec.oje_staff_os_count} {success}"
                    )
                elif rec.oje_template_scope == 'store_management':
                    rec.oje_display_text = f"Overall {rec.oje_management_overall_rating or 0}/5 {success}"
                else:
                    score = int(rec.oje_total_score)
                    rec.oje_display_text = f"{score}/{int(rec.oje_pass_score_snapshot)} {success}"
            else:
                rec.oje_display_text = "N/A"

    def action_open_survey_results(self):
        self.ensure_one()
        if not self.survey_user_input_id:
            return False
        return {
            "type": "ir.actions.act_window",
            "name": "Kết quả Khảo sát",
            "res_model": "survey.user_input",
            "res_id": self.survey_user_input_id.id,
            "view_mode": "form",
            "target": "current",
        }

    def action_open_oje_results(self):
        self.ensure_one()
        if not self.oje_evaluation_id:
            # Fallback legacy
            if self.oje_survey_user_input_id:
                return {
                    "type": "ir.actions.act_window",
                    "name": "Kết quả Đánh giá OJE (Legacy)",
                    "res_model": "survey.user_input",
                    "res_id": self.oje_survey_user_input_id.id,
                    "view_mode": "form",
                    "target": "current",
                }
            return False

        if self.oje_evaluation_id.template_scope in ('store_staff', 'store_management'):
            return {
                'type': 'ir.actions.act_url',
                'name': 'Kết quả Đánh giá OJE',
                'url': f'/recruitment/oje/internal/{self.oje_evaluation_id.id}',
                'target': 'new',
            }

        return {
            "type": "ir.actions.act_window",
            "name": "Kết quả Đánh giá OJE",
            "res_model": "hr.applicant.oje.evaluation",
            "res_id": self.oje_evaluation_id.id,
            "view_mode": "form",
            "target": "current",
        }

    # ==================== TRACKING ====================

    interview_invitation_sent = fields.Boolean(
        string="Đã Gửi Thư Mời PV", default=False, tracking=True
    )

    invitation_sent_date = fields.Datetime(string="Ngày Gửi Thư Mời", readonly=True)

    interview_confirmation_state = fields.Selection(
        [
            ("not_sent", "Chưa gửi"),
            ("pending", "Chờ ứng viên xác nhận"),
            ("accepted", "Ứng viên đã xác nhận"),
        ],
        string="Trạng thái xác nhận lịch PV",
        default="not_sent",
        copy=False,
        tracking=True,
    )

    interview_accept_token = fields.Char(
        string="Mã xác nhận lịch PV",
        copy=False,
        index=True,
        readonly=True,
    )

    interview_confirmation_sent_date = fields.Datetime(
        string="Ngày gửi email xác nhận PV",
        readonly=True,
        copy=False,
    )

    interview_preferred_datetime = fields.Datetime(
        string="Khung giờ ưu tiên từ survey",
        readonly=True,
        copy=False,
    )

    interview_preferred_slot_label = fields.Char(
        string="Lựa chọn khung giờ ưu tiên",
        readonly=True,
        copy=False,
    )

    interview_accepted_date = fields.Datetime(
        string="Ngày ứng viên xác nhận lịch PV",
        readonly=True,
        copy=False,
    )

    interview_confirmed_datetime = fields.Datetime(
        string="Lịch PV đã chốt",
        readonly=True,
        copy=False,
    )

    interview_event_id = fields.Many2one(
        "calendar.event",
        string="Sự kiện lịch PV",
        readonly=True,
        copy=False,
    )

    interview_booked_slot = fields.Selection(
        [
            ("1", "Slot 1"),
            ("2", "Slot 2"),
            ("3", "Slot 3"),
        ],
        string="Slot đã book",
        copy=False,
        readonly=True,
    )

    interview_booking_status = fields.Selection(
        [
            ("pending", "Chờ xử lý"),
            ("booked", "Đã book"),
            ("full", "Hết chỗ"),
        ],
        string="Trạng thái đặt lịch PV",
        default="pending",
        copy=False,
        tracking=True,
    )

    survey_under_review_date = fields.Datetime(
        string="Ngày Vào Xem Xét Survey",
        readonly=True,
        help="Thời điểm sai câu hỏi bắt buộc khi làm survey. Sau 24h tự động Reject."
    )

    application_source = fields.Selection([
        ('web', 'Website (nội bộ)'),
        ('api', 'API / Hệ thống bên ngoài'),
        ('manual', 'HR tạo thủ công'),
    ], string='Nguồn Ứng tuyển', default='manual', copy=False)

    current_stage_name = fields.Char(
        related="stage_id.name",
        string="Tên Stage Hiện Tại",
        store=False,
        readonly=True,
    )

    hide_approval_buttons = fields.Boolean(
        compute="_compute_hide_approval_buttons",
        store=False,
    )

    @api.depends("stage_id", "position_level")
    def _compute_hide_approval_buttons(self):
        for rec in self:
            if rec.position_level == 'management' and rec.stage_id and rec.stage_id.name in ('OJE', 'Offer', 'Hired', 'Reject'):
                rec.hide_approval_buttons = True
            else:
                rec.hide_approval_buttons = False

    # ==================== ONCHANGE ====================

    @api.onchange("job_id")
    def _onchange_job_id(self):
        """
        Khi chọn job → tự động set stage đầu tiên theo position_level (nếu có)
        hoặc theo recruitment_type
        """
        if self.job_id:
            # Ưu tiên lọc theo position_level (management/staff) nếu có
            stage_type = self._get_pipeline_stage_type()
            if stage_type:
                default_stage = self.env["hr.recruitment.stage"].search(
                    [("recruitment_type", "in", [stage_type, "both"])],
                    order="sequence asc",
                    limit=1,
                )
                if default_stage:
                    self.stage_id = default_stage

    @api.onchange("department_id")
    def _onchange_department_id(self):
        """Khi chọn phòng ban → tự động load lịch PV và Company"""
        if self.department_id:
            # Tự động set company từ department
            if self.department_id.company_id:
                self.company_id = self.department_id.company_id
            
            # Tìm lịch PV đã xác nhận của department trong tuần hiện tại
            today = fields.Date.today()
            monday = today - timedelta(days=today.weekday())
            
            schedule = self.env["interview.schedule"].search([
                ("department_id", "=", self.department_id.id),
                ("state", "=", "confirmed"),
                ("week_start_date", "=", monday),
            ], limit=1)

            if schedule:
                self.interview_schedule_id = schedule
                _logger.info(f"Auto-load schedule: {schedule.display_name}")
            else:
                self.interview_schedule_id = False
                _logger.warning(
                    f"Phòng ban {self.department_id.name} chưa có lịch PV đã xác nhận cho tuần này"
                )

    def _find_department_interview_schedule(self, department):
        """Ưu tiên lịch đã confirm gần nhất từ tuần hiện tại trở đi cho đúng phòng ban."""
        self.ensure_one()
        if not department:
            return self.env["interview.schedule"]

        today = fields.Date.today()
        monday = today - timedelta(days=today.weekday())
        Schedule = self.env["interview.schedule"].sudo()

        schedule = Schedule.search([
            ("department_id", "=", department.id),
            ("state", "=", "confirmed"),
            ("week_start_date", ">=", monday),
        ], order="week_start_date asc, id asc", limit=1)

        if not schedule:
            schedule = Schedule.search([
                ("department_id", "=", department.id),
                ("state", "=", "confirmed"),
            ], order="week_start_date desc, id desc", limit=1)
        return schedule

    oje_survey_url = fields.Char(string="Link Đánh Giá OJE", readonly=True)

    # Website Custom Form Fields
    x_birthday = fields.Date(string="Ngày sinh")
    x_current_job = fields.Char(string="Công việc hiện tại")
    x_portrait_image = fields.Binary(string="Ảnh chân dung")
    x_gender = fields.Selection([
        ('male', 'Nam'),
        ('female', 'Nữ'),
        ('not_display', 'Không hiển thị')
    ], string="Giới tính")
    x_id_number = fields.Char(string="Số CMT/CCCD/Hộ chiếu")
    x_education_level = fields.Selection([
        ('no_degree', 'Chưa tốt nghiệp'),
        ('high_school', 'Phổ thông'),
        ('vocational', 'Trung cấp'),
        ('college', 'Cao đẳng'),
        ('university', 'Đại học'),
        ('master', 'Thạc sỹ'),
        ('phd', 'Tiến sỹ'),
        ('postgraduate', 'Sau đại học'),
        ('others', 'Khác')
    ], string="Trình độ học vấn")
    x_school_name = fields.Char(string="Tên trường")
    x_current_address = fields.Char(string="Địa chỉ hiện tại")
    x_weekend_available = fields.Selection([
        ('yes', 'Có'),
        ('no', 'Không')
    ], string="Có thể làm việc cuối tuần/Lễ Tết?")
    x_worked_mcdonalds = fields.Selection([
        ('yes', 'Có'),
        ('no', 'Không')
    ], string="Đã từng làm việc tại McDonald’s VN?")
    x_last_company = fields.Char(string="Công ty gần nhất")
    x_referral_staff_id = fields.Char(string="Mã giới thiệu (Staff ID)")
    
    # Các trường mở rộng thêm cho phần "Các thông tin khác"
    x_application_content = fields.Text(string="Nội dung")
    x_salutation = fields.Char(string="Danh xưng")
    x_id_issue_date = fields.Date(string="Ngày cấp CMT/CCCD/Hộ chiếu")
    x_id_issue_place = fields.Char(string="Nơi cấp CMT/CCCD/Hộ chiếu")
    x_permanent_address = fields.Char(string="Địa chỉ thường trú")
    x_hometown = fields.Char(string="Nguyên quán")
    x_years_experience = fields.Integer(string="Số năm kinh nghiệm")
    x_height = fields.Integer(string="Chiều cao (cm)")
    x_weight = fields.Integer(string="Cân nặng (kg)")
    x_nationality = fields.Char(string="Quốc tịch")

    def _get_auto_pre_interview_survey(self, job):
        """Tự chọn survey theo cấp bậc + employment type của position."""
        self.ensure_one()
        Survey = self.env["survey.survey"].sudo()

        position_level = (job.position_level or "").strip().lower() if job else ""
        # level_id là Many2one('hr.job.level') từ M02_P0200_00; fallback nếu field cũ 'level' không tồn tại
        level_id = getattr(job, "level_id", False) if job else False
        raw_level_code = ((level_id.code if level_id else "") or "").strip().lower()
        raw_level_name = ((level_id.name if level_id else "") or "").strip().lower()
        job_name = (job.name or "").strip().lower() if job else ""

        is_management = bool(
            position_level == "management"
            or "manager" in raw_level_code
            or "manager" in raw_level_name
            or "quản lý" in raw_level_name
            or "quản lý" in job_name
            or "manager" in job_name
        )

        # Rule nghiệp vụ: cấp bậc quản lý luôn dùng survey quản lý cửa hàng,
        # bỏ qua part-time/full-time.
        if is_management:
            survey = self.env.ref("M02_P0204_00.survey_manager", raise_if_not_found=False)
            if survey:
                return survey

        # ƯU TIÊN: Survey Template đã cấu hình trên Job Position
        if job and job.generated_survey_template_id:
            return job.generated_survey_template_id

        contract_name = ((job.contract_type_id.name if job and "contract_type_id" in job._fields else "") or "").lower()
        is_part_time = "part" in contract_name

        if is_part_time:
            survey = self.env.ref("M02_P0204_00.survey_parttime", raise_if_not_found=False)
            if survey:
                return survey
        else:
            survey = self.env.ref("M02_P0204_00.survey_fulltime", raise_if_not_found=False)
            if survey:
                return survey

        return job.survey_id if job and "survey_id" in job._fields else Survey

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get("job_id"):
                continue

            job = self.env["hr.job"].browse(vals["job_id"])
            stage_type = job.position_level or job.recruitment_type if job.recruitment_type == 'store' else job.recruitment_type

            # Đồng bộ phòng ban / company theo position ngay lúc nộp CV.
            if not vals.get("department_id") and job.department_id:
                vals["department_id"] = job.department_id.id
            if not vals.get("company_id"):
                vals["company_id"] = (job.company_id.id or job.department_id.company_id.id or self.env.company.id)
            
            # Snapshot OJE Evaluator
            if not vals.get("oje_evaluator_user_id") and job.oje_evaluator_user_id:
                vals["oje_evaluator_user_id"] = job.oje_evaluator_user_id.id

        applicants = super().create(vals_list)

        # Tự động gửi link khảo sát / thư mời PV ngay khi nộp CV.
        base_url = self.env["ir.config_parameter"].sudo().get_param("web.base.url")
        for applicant in applicants:
            job = applicant.job_id
            if not job:
                continue

            if not applicant.department_id and job.department_id:
                applicant.department_id = job.department_id
            if not applicant.company_id:
                applicant.company_id = (job.company_id or job.department_id.company_id or self.env.company)

            # Interview schedule auto-assign: store only
            if applicant.recruitment_type == 'store' and not applicant.interview_schedule_id and applicant.department_id:
                schedule = applicant._find_department_interview_schedule(applicant.department_id)
                if schedule:
                    applicant.interview_schedule_id = schedule

            if not applicant.pre_interview_survey_id:
                applicant.pre_interview_survey_id = applicant._get_auto_pre_interview_survey(job)

            if not applicant.pre_interview_survey_id or not applicant.email_from:
                continue

            # Store-only: auto-send interview invitation / survey email
            if applicant.recruitment_type != 'store':
                continue

            # Nếu có lịch confirm theo phòng ban, gửi thư mời PV có kèm lịch + link survey.
            if applicant.interview_schedule_id and applicant.interview_schedule_id.state == "confirmed":
                # Chặn email trùng cho ứng viên nộp từ web (đã làm survey tại trang)
                if applicant.application_source == 'web':
                    _logger.info("[AUTO_INVITE] Skipped - web applicant already has survey answered.")
                    continue

                try:
                    applicant.action_send_interview_invitation()
                    _logger.info("[AUTO_INVITE] Sent interview invitation for applicant %s", applicant.id)
                    continue
                except Exception as e:
                    _logger.warning("[AUTO_INVITE] Fallback to survey invite for applicant %s: %s", applicant.id, str(e))

            # Chỉ gửi email survey cho ứng viên KHÔNG từ web (API/thủ công)
            if applicant.application_source != 'web':
                applicant._send_survey_invite_email()
            else:
                _logger.info("[SURVEY_EMAIL] Skipped survey email for web applicant %s (already completed on portal).", applicant.id)

        return applicants

    def _send_survey_invite_email(self):
        """Tách riêng logic gửi email survey để có thể skip khi nộp từ web form mới."""
        self.ensure_one()
        base_url = self.env["ir.config_parameter"].sudo().get_param("web.base.url")
        
        if not self.survey_user_input_id:
            user_input = self.env["survey.user_input"].create({
                "survey_id": self.pre_interview_survey_id.id,
                "partner_id": self.partner_id.id,
                "email": self.email_from,
            })
            self.write({
                "survey_user_input_id": user_input.id,
                "survey_url": base_url + user_input.get_start_url(),
                "interview_invitation_sent": True,
                "invitation_sent_date": fields.Datetime.now(),
            })

        template = self._get_email_template_resolution(
            event_code="survey_invite",
            fallback_xml_id="M02_P0204_00.email_applicant_survey_invite"
        )
        if template:
            try:
                self._send_mail_async(template, self.id)
                _logger.info(
                    f"[SURVEY_EMAIL] Queued for async send to {self.email_from} for job {self.job_id.name}"
                )
            except Exception as e:
                _logger.error(
                    f"[SURVEY_EMAIL] Failed to queue for {self.email_from}: {str(e)}"
                )

    def _get_email_template_resolution(self, event_code=None, resolve_stage_id=None, fallback_xml_id=None):
        """Resolver Helper: Resolves the best email template for a given applicant event/stage.
        Priority: 
        1. Job Email Rules for EVENT or STAGE
        2. Recruitment Stage Default Email Config
        3. Hardcoded Fallback XML ID
        """
        self.ensure_one()
        
        # 1. Job Overrides
        if self.job_id:
            domain = [('job_id', '=', self.job_id.id), ('active', '=', True)]
            if event_code:
                rule = self.env['hr.job.email.rule'].search(domain + [('rule_type', '=', 'event'), ('event_code', '=', event_code)], limit=1)
                if rule and rule.template_id:
                    return rule.template_id
            if resolve_stage_id:
                rule = self.env['hr.job.email.rule'].search(domain + [('rule_type', '=', 'stage'), ('stage_id', '=', resolve_stage_id)], limit=1)
                if rule and rule.template_id:
                    return rule.template_id

        # 2. Stage Global Config
        if resolve_stage_id:
            stage = self.env['hr.recruitment.stage'].browse(resolve_stage_id)
            if stage.exists() and stage.candidate_email_enabled and stage.candidate_email_template_id:
                return stage.candidate_email_template_id

        # 3. Fallback to native XML template
        if fallback_xml_id:
            return self.env.ref(fallback_xml_id, raise_if_not_found=False)

        return self.env['mail.template']

    def _send_mail_async(self, template, res_id, email_values=None):
        """Helper to send mail in a background thread after the current transaction commits."""
        mail_id = template.send_mail(res_id, force_send=False, email_values=email_values)
        if mail_id:
            db_name = self.env.cr.dbname
            def trigger_thread():
                t = threading.Thread(target=_send_background_task, args=(db_name, mail_id), daemon=True)
                t.start()
            self.env.cr.postcommit.add(trigger_thread)
        return mail_id

    # ==================== KANBAN STAGE FILTERING ====================

    @api.model
    def _resolve_stage_filter_type(self, domain=None):
        """Resolve the canonical pipeline type key from context, domain, or job lookup.
        Priority: context(default_stage_filter_type) > context(position_level) >
                  context(recruitment_type) > domain(position_level) >
                  domain(recruitment_type) > job lookup.
        Returns: 'staff' | 'management' | 'office' | 'store' | False
        """
        ctx = self.env.context

        # 1. Explicit stage filter (set by action_open_applicants)
        target = (
            ctx.get("default_stage_filter_type")
            or ctx.get("default_position_level")
            or ctx.get("default_recruitment_type")
        )
        if target:
            return target

        # 2. From domain — position_level first, then recruitment_type
        if domain:
            for leaf in domain:
                if isinstance(leaf, (list, tuple)) and len(leaf) == 3:
                    if leaf[0] == "position_level" and leaf[1] == "=":
                        return leaf[2]
            for leaf in domain:
                if isinstance(leaf, (list, tuple)) and len(leaf) == 3:
                    if leaf[0] == "recruitment_type" and leaf[1] == "=":
                        return leaf[2]

        # 3. Lookup job from context or domain
        job_id = ctx.get("default_job_id")
        if not job_id and domain:
            for leaf in domain:
                if isinstance(leaf, (list, tuple)) and len(leaf) == 3:
                    if leaf[0] == "job_id" and leaf[1] == "=":
                        job_id = leaf[2]
                        break
        if job_id:
            job = self.env["hr.job"].browse(job_id)
            if job.exists() and hasattr(job, '_get_stage_filter_type'):
                return job._get_stage_filter_type()

        return False

    @api.model
    def _read_group_stage_ids(self, stages, domain, order=None):
        """Filter kanban stages by the resolved pipeline type.
        Never returns all stages as a fallback — unknown falls back to 'both' only.
        """
        target_type = self._resolve_stage_filter_type(domain)

        if target_type:
            return stages.search(
                [("recruitment_type", "in", [target_type, "both"])],
                order=order or stages._order,
            )

        # Absolute fallback: show only generic 'both' stages, never everything
        return stages.search(
            [("recruitment_type", "=", "both")],
            order=order or stages._order,
        )



    # ==================== ACTIONS ====================

    def action_send_interview_invitation(self):
        """Gửi email mời phỏng vấn kèm link khảo sát"""
        self.ensure_one()

        # Validation
        if not self.company_id:
            raise exceptions.ValidationError("Vui lòng chọn Brand!")

        if not self.interview_schedule_id:
            raise exceptions.ValidationError("Vui lòng chọn Lịch Phỏng Vấn!")

        if self.interview_schedule_id.state != "confirmed":
            raise exceptions.ValidationError(
                "Lịch PV chưa được xác nhận bởi Store Manager!"
            )

        if not self.pre_interview_survey_id:
            raise exceptions.ValidationError("Vui lòng chọn Khảo Sát!")

        if not self.email_from:
            raise exceptions.UserError("Ứng viên chưa có email!")

        # Tạo survey copy riêng cho ứng viên để tránh xung đột dữ liệu Q14 giữa các link.
        isolated_survey = self._build_isolated_interview_survey()

        # Tạo survey.user_input qua hàm chuẩn của Odoo
        user_input = isolated_survey._create_answer(
            partner=self.partner_id,
            email=self.email_from,
        )
        base_url = self.env["ir.config_parameter"].sudo().get_param("web.base.url")
        self.write({
            "survey_user_input_id": user_input.id,
            "survey_url": base_url + user_input.get_start_url(),
        })

        # Tìm email template
        template = self._get_email_template_resolution(
            event_code="interview_invitation",
            fallback_xml_id="M02_P0204_00.email_interview_invitation"
        )

        if not template:
            raise exceptions.ValidationError("Không tìm thấy email template!")

        # Gửi email
        self._send_mail_async(template, self.id)

        # Cập nhật trạng thái
        self.write(
            {
                "interview_invitation_sent": True,
                "invitation_sent_date": fields.Datetime.now(),
            }
        )

        _logger.info(f"Đã gửi thư mời PV cho {self.partner_name}")

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": "Đã gửi!",
                "message": f"Đã gửi thư mời phỏng vấn cho {self.partner_name}",
                "type": "success",
                "next": {"type": "ir.actions.client", "tag": "reload"},
            },
        }

    def _format_interview_slot_label(self, interview_dt, index):
        """Format label cho đáp án Q14 theo timezone VN."""
        if not interview_dt:
            return f"Ngày PV {index}: (chưa cập nhật)"

        weekday_vn = ['Thứ Hai', 'Thứ Ba', 'Thứ Tư', 'Thứ Năm', 'Thứ Sáu', 'Thứ Bảy', 'Chủ Nhật']

        dt_vn = fields.Datetime.context_timestamp(
            self.with_context(tz='Asia/Ho_Chi_Minh'),
            interview_dt,
        )
        return f"Ngày PV {index}: {weekday_vn[dt_vn.weekday()]}, {dt_vn.strftime('%d/%m/%Y %H:%M')}"

    def _build_isolated_interview_survey(self):
        """Clone survey template cho từng applicant rồi cập nhật riêng đáp án Q14."""
        self.ensure_one()

        base_survey = self.pre_interview_survey_id
        if not base_survey:
            raise exceptions.ValidationError("Vui lòng chọn Khảo Sát!")

        email_tag = (self.email_from or self.partner_name or f"app-{self.id}").strip()
        dt_vn = fields.Datetime.context_timestamp(
            self.with_context(tz='Asia/Ho_Chi_Minh'),
            fields.Datetime.now(),
        )
        hour_12 = dt_vn.strftime('%I').lstrip('0') or '12'
        time_label = f"{dt_vn.strftime('%d/%m/%Y')} {hour_12}:{dt_vn.strftime('%M')}{dt_vn.strftime('%p')}"
        copy_title = f"{base_survey.title} | {email_tag} | {time_label}"
        isolated_survey = base_survey.copy({
            'title': copy_title,
            # Tránh xuất hiện trong danh sách survey template để HR chọn nhầm.
            'is_pre_interview': False,
        })
        # Ép lại title theo email ứng viên để dễ nhận diện trong danh sách Surveys.
        isolated_survey.sudo().write({'title': copy_title})

        q14 = isolated_survey.question_ids.filtered(
            lambda q: q.sequence == 140 and q.question_type == 'simple_choice'
        )[:1]

        if not q14:
            _logger.warning('[SURVEY_ISOLATED] Không tìm thấy Q14 trên survey copy %s', isolated_survey.id)
            return isolated_survey

        labels = [
            self._format_interview_slot_label(self.interview_schedule_id.interview_date_1, 1),
            self._format_interview_slot_label(self.interview_schedule_id.interview_date_2, 2),
            self._format_interview_slot_label(self.interview_schedule_id.interview_date_3, 3),
        ]

        for ans, label in zip(q14.suggested_answer_ids.sorted('sequence')[:3], labels):
            ans.sudo().write({'value': label})

        _logger.info(
            '[SURVEY_ISOLATED] Created survey copy %s for applicant %s with schedule %s',
            isolated_survey.id,
            self.id,
            self.interview_schedule_id.id,
        )
        return isolated_survey

    def _is_interview_stage(self):
        self.ensure_one()
        return bool(self.stage_id and "interview" in (self.stage_id.name or "").lower())

    def _extract_survey_preferred_slot(self):
        """Đọc lựa chọn slot từ đáp án survey đã hoàn thành (Q14)."""
        self.ensure_one()
        user_input = self.survey_user_input_id
        if not user_input or user_input.state != "done":
            return False, False

        line = user_input.user_input_line_ids.filtered(
            lambda l: l.question_id.question_type == "simple_choice"
            and (l.suggested_answer_id or getattr(l, "value_suggested", False))
            and (((l.suggested_answer_id or getattr(l, "value_suggested", False)).value or "").strip().startswith("Ngày PV"))
        )[:1]
        if not line:
            return False, False

        selected_answer = line.suggested_answer_id or getattr(line, "value_suggested", False)
        label = ((selected_answer and selected_answer.value) or "").strip()
        match = re.search(r"Ngày\s*PV\s*(\d)", label, flags=re.IGNORECASE)
        if not match:
            return False, label

        slot_index = int(match.group(1))
        if slot_index not in (1, 2, 3):
            return False, label
        return slot_index, label

    def _get_schedule_datetime_by_slot(self, slot_index):
        self.ensure_one()
        schedule = self.interview_schedule_id
        if not schedule:
            return False
        mapping = {
            1: schedule.interview_date_1,
            2: schedule.interview_date_2,
            3: schedule.interview_date_3,
        }
        return mapping.get(slot_index)

    def _send_interview_slot_confirmed_email(self):
        self.ensure_one()
        template = self._get_email_template_resolution(
            event_code="interview_slot_confirmed",
            fallback_xml_id="M02_P0204_00.email_interview_slot_confirmed"
        )
        if template and self.email_from:
            email_values = {}
            if self.interview_event_id:
                # Generate .ics file using Odoo's native method
                ics_files = self.interview_event_id.sudo()._get_ics_file()
                event_ics = ics_files.get(self.interview_event_id.id)
                if event_ics:
                    attachment = self.env['ir.attachment'].sudo().create({
                        'name': 'invitation.ics',
                        'type': 'binary',
                        'datas': base64.b64encode(event_ics),
                        'mimetype': 'text/calendar',
                    })
                    email_values['attachment_ids'] = [(6, 0, [attachment.id])]

            self._send_mail_async(template, self.id, email_values=email_values)

    def _send_interview_slot_full_email(self):
        self.ensure_one()
        template = self.env.ref(
            "M02_P0204_00.email_interview_slot_full",
            raise_if_not_found=False,
        )
        if template and self.email_from:
            self._send_mail_async(template, self.id)

    def action_accept_interview(self):
        """Chuyển ứng viên từ Interview sang OJE, bỏ qua kiểm tra Evaluation."""
        self.ensure_one()
        # Tìm stage OJE theo recruitment_type của ứng viên
        stage_type = self._get_pipeline_stage_type() or 'store'
        oje_stage = self.env['hr.recruitment.stage'].search([
            ('name', 'ilike', 'OJE'),
            ('recruitment_type', 'in', [stage_type, 'both']),
        ], order='sequence asc', limit=1)
        if not oje_stage:
            # Fallback: tìm bất kỳ stage OJE nào
            oje_stage = self.env['hr.recruitment.stage'].search([
                ('name', 'ilike', 'OJE'),
            ], order='sequence asc', limit=1)
        if not oje_stage:
            raise exceptions.UserError("Không tìm thấy stage OJE phù hợp.")
        
        # Bypass kanban_state / priority constraint: ghi trực tiếp
        self.write({
            'stage_id': oje_stage.id,
            'kanban_state': 'normal',  # reset về normal sau khi chấp nhận
        })
        return True

    def action_send_interview_accept_link(self):
        """Giữ lại nút cũ: chuyển thành gửi email xác nhận slot đã được book tự động."""
        self.ensure_one()
        if self.interview_booking_status == 'booked':
            self._send_interview_slot_confirmed_email()
            message = f"Đã gửi lại email xác nhận lịch phỏng vấn cho {self.partner_name}"
            notif_type = "success"
        else:
            self._send_interview_slot_full_email()
            message = f"Đã gửi email thông báo hết chỗ cho {self.partner_name}"
            notif_type = "warning"
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": "Đã gửi",
                "message": message,
                "type": notif_type,
                "next": {"type": "ir.actions.client", "tag": "reload"},
            },
        }

    def _lock_schedule_row(self):
        self.ensure_one()
        if self.interview_schedule_id:
            self.env.cr.execute(
                "SELECT id FROM interview_schedule WHERE id = %s FOR UPDATE",
                (self.interview_schedule_id.id,),
            )

    def _ensure_applicant_partner(self):
        self.ensure_one()
        if not self.partner_id:
            if not self.partner_name:
                raise exceptions.UserError(_("You must define a Contact Name for this applicant."))
            self.partner_id = self.env["res.partner"].sudo().create({
                "is_company": False,
                "name": self.partner_name,
                "email": self.email_from,
            })

    def _create_fcfs_interview_event(self, start_dt):
        self.ensure_one()
        self._ensure_applicant_partner()

        stop_dt = start_dt + timedelta(minutes=30)
        # Route Accept chạy auth=public, nên không dùng env.uid để tránh gán organizer thành Public User.
        organizer_user = self.user_id or self.create_uid or self.department_id.manager_id.user_id
        if organizer_user and organizer_user._is_public():
            organizer_user = self.department_id.manager_id.user_id or self.env.ref('base.user_admin', raise_if_not_found=False)

        partners = self.partner_id | self.department_id.manager_id.user_id.partner_id
        if organizer_user and organizer_user.partner_id:
            partners |= organizer_user.partner_id
        
        # Thêm Administrator làm người tham gia để hiển thị trên lịch của Admin (hữu ích khi test)
        admin_user = self.env.ref('base.user_admin', raise_if_not_found=False)
        if admin_user and admin_user.partner_id:
            partners |= admin_user.partner_id

        event_vals = {
            "name": f"Interview - {self.partner_name or self.name}",
            "start": start_dt,
            "stop": stop_dt,
            "allday": False,
            "res_model": "hr.applicant",
            "res_id": self.id,
            "res_model_id": self.env['ir.model']._get_id('hr.applicant'),
            "applicant_id": self.id,
            "user_id": organizer_user.id if organizer_user else False,
            "partner_ids": [(6, 0, partners.ids)],
            "description": "Tạo tự động ngay khi ứng viên pass survey và slot còn chỗ (FCFS).",
        }
        # Use no_mail_to_attendees=True to suppress redundant generic Odoo invitation
        return self.env["calendar.event"].sudo().with_context(no_mail_to_attendees=True).create(event_vals)

    def _publish_slot_update_bus(self):
        self.ensure_one()
        schedule = self.interview_schedule_id
        if not schedule:
            return

        remaining = schedule._get_slot_remaining_map()
        payload = {
            "schedule_id": schedule.id,
            "department_id": schedule.department_id.id,
            "remaining": {
                "1": remaining.get(1, 0),
                "2": remaining.get(2, 0),
                "3": remaining.get(3, 0),
            },
            "max_candidates": {
                "1": schedule.max_candidates_slot_1,
                "2": schedule.max_candidates_slot_2,
                "3": schedule.max_candidates_slot_3,
            },
        }
        self.env["bus.bus"]._sendone(
            f"recruitment_interview_slot_{schedule.id}",
            "slot_update",
            payload,
        )

    def action_auto_book_interview_from_survey(self):
        """Book slot phỏng vấn tự động ngay khi survey done theo cơ chế FCFS + lock."""
        self.ensure_one()

        if self.interview_event_id and self.interview_booking_status == 'booked':
            return {"status": "already_booked"}

        if not self.interview_schedule_id:
            return {"status": "no_schedule"}

        # ƯU TIÊN: Đọc từ field interview_booked_slot (form website mới)
        slot_index = int(self.interview_booked_slot) if self.interview_booked_slot else None
        slot_label = f"Slot {slot_index}" if slot_index else None

        # FALLBACK: Đọc từ đáp án Q14 trong survey (luồng cũ qua link email)
        if not slot_index:
            slot_index, slot_label = self._extract_survey_preferred_slot()

        if not slot_index:
            return {"status": "no_slot_selected"}

        target_start = self._get_schedule_datetime_by_slot(slot_index)
        if not target_start:
            return {"status": "invalid_slot"}

        self._lock_schedule_row()
        remaining_map = self.interview_schedule_id._get_slot_remaining_map()
        if remaining_map.get(slot_index, 0) <= 0:
            self.write({
                "interview_booking_status": "full",
                "interview_booked_slot": str(slot_index),
                "interview_preferred_slot_label": slot_label or False,
                "interview_preferred_datetime": target_start,
                "interview_confirmation_state": "not_sent",
                "interview_confirmation_sent_date": fields.Datetime.now(),
                "interview_accept_token": False,
            })
            self._send_interview_slot_full_email()
            self._publish_slot_update_bus()
            return {"status": "slot_full"}

        event = self._create_fcfs_interview_event(target_start)
        self.write({
            "interview_event_id": event.id,
            "interview_confirmed_datetime": target_start,
            "interview_booked_slot": str(slot_index),
            "interview_booking_status": "booked",
            "interview_preferred_slot_label": slot_label or False,
            "interview_preferred_datetime": target_start,
            "interview_confirmation_state": "accepted",
            "interview_accepted_date": fields.Datetime.now(),
            "interview_confirmation_sent_date": fields.Datetime.now(),
            "interview_accept_token": False,
        })
        self._send_interview_slot_confirmed_email()
        self._publish_slot_update_bus()

        self.message_post(
            body=_("Hệ thống đã tự động book lịch phỏng vấn ngay khi ứng viên hoàn thành survey."),
            subtype_xmlid="mail.mt_note",
        )
        return {"status": "booked", "event_id": event.id}

    def action_accept_interview_confirmation(self):
        """Backward-compatible endpoint: hiện tại chuyển sang auto-book từ survey."""
        self.ensure_one()
        result = self.action_auto_book_interview_from_survey()
        if self.interview_event_id:
            return self.interview_event_id
        raise exceptions.UserError(
            "Khung giờ bạn chọn đã hết chỗ hoặc chưa đủ điều kiện để tự động tạo lịch. Vui lòng liên hệ HR."
        )

    def _maybe_send_interview_confirmation_on_stage_change(self, old_stages):
        for rec in self:
            old_stage_id = old_stages.get(rec.id)
            if not rec.stage_id or old_stage_id == rec.stage_id.id:
                continue
            if not rec._is_interview_stage():
                continue
            if rec.interview_booking_status == 'booked':
                continue
            try:
                if rec.survey_user_input_id and rec.survey_user_input_id.state == 'done':
                    rec.action_auto_book_interview_from_survey()
                else:
                    rec.write({
                        "interview_booking_status": "pending",
                        "interview_confirmation_state": "not_sent",
                        "interview_accept_token": False,
                    })
            except Exception as err:
                _logger.error(
                    "[INTERVIEW_AUTO_BOOK] Failed for applicant %s: %s",
                    rec.id,
                    err,
                )

    def _autosend_for_digitization(self):
        """Override to allow bypassing OCR trigger via context to prevent concurrent update errors"""
        if self.env.context.get('skip_extract'):
            _logger.info("[OCR_BYPASS] Skipping auto-send for digitization due to skip_extract context")
            return
        return super()._autosend_for_digitization()

    # ==================== APPROVAL OVERRIDES ====================

    def action_approve_documents(self):
        """Override: Khối Cửa Hàng → Under Review; others → Contract Signed"""
        # Sử dụng skip_extract=True để tránh lỗi SerializationFailure (Concurrent Update)
        # do iap_extract cố gắng gán digitization lặp lại trong post-commit.
        self = self.with_context(skip_extract=True)
        for rec in self:
            _logger.info("[APPROVE_DOCS] Processing applicant %s (type: %s, level: %s)", rec.id, rec.recruitment_type, rec.position_level)
            if rec.recruitment_type == 'store':
                stage_type = rec._get_pipeline_stage_type()
                # Sử dụng ilike và domain rộng hơn một chút để tránh lỗi tìm kiếm
                stage = self.env['hr.recruitment.stage'].search([
                    ('name', 'ilike', 'Under Review'),
                    ('recruitment_type', 'in', [stage_type, 'both']),
                ], limit=1)
                if not stage:
                    _logger.warning("[APPROVE_DOCS] Specific stage 'Under Review' not found for type %s. Falling back to generic search.", stage_type)
                    stage = self.env['hr.recruitment.stage'].search([('name', 'ilike', 'Under Review')], limit=1)
                
                _logger.info("[APPROVE_DOCS] Store mode - final stage result: %s", stage.id if stage else "NOT FOUND")
                if stage:
                    rec.stage_id = stage.id
                super(HrApplicant, rec).action_approve_documents()
            else:
                stage = self.env['hr.recruitment.stage'].search(
                    [('name', 'ilike', 'Contract Signed')], limit=1
                )
                _logger.info("[APPROVE_DOCS] Office mode - searching for 'Contract Signed'. Result: %s", stage.id if stage else "NOT FOUND")
                if stage:
                    rec.stage_id = stage.id
                super(HrApplicant, rec).action_approve_documents()

    def action_reject_documents(self):
        """HR quyết định không duyệt hồ sơ → mở wizard nhập lý do"""
        self.ensure_one()
        return {
            'name': 'Lý do từ chối hồ sơ',
            'type': 'ir.actions.act_window',
            'res_model': 'applicant.get.refuse.reason',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_applicant_ids': self.ids,
                'active_ids': self.ids,
                'default_source_action': 'reject_documents',
            },
        }

    def _action_reject_documents_confirmed(self, reason):
        """Callback confirm rejection hồ sơ"""
        self = self.with_context(skip_extract=True)
        for rec in self:
            clean_reason = (reason or '').strip()
            if not clean_reason:
                from odoo.exceptions import ValidationError
                raise ValidationError("Vui lòng nhập lý do từ chối!")

            stage_type = rec._get_pipeline_stage_type()
            domain = [('name', 'ilike', 'Reject')]
            if stage_type:
                domain.append(('recruitment_type', 'in', [stage_type, 'both']))
            stage = self.env['hr.recruitment.stage'].search(domain, limit=1)
            if not stage:
                stage = self.env['hr.recruitment.stage'].search([('name', 'ilike', 'Reject')], limit=1)

            vals = {
                'document_approval_status': 'refused',
                'reject_reason': clean_reason,
            }
            if stage:
                vals['stage_id'] = stage.id

            rec.write(vals)
            rec.message_post(body=f"Từ chối hồ sơ. Lý do: {clean_reason}")

    # ==================== EVALUATION AUTO-PROGRESSION ====================

    def write(self, vals):
        # Đồng bộ refuse_reason_id sang reject_reason cho các flow legacy (như 0205)
        if 'refuse_reason_id' in vals and vals.get('refuse_reason_id') and 'reject_reason' not in vals:
            reason = self.env['hr.applicant.refuse.reason'].browse(vals['refuse_reason_id'])
            if reason.exists() and 'System:' not in reason.name:
                vals['reject_reason'] = reason.name

        # Lưu lại stage cũ trước khi write để check điều kiện gửi email Reject
        old_stages = {rec.id: rec.stage_id.id for rec in self}
        
        result = super().write(vals)
        # Khi HR đánh giá (priority/stars) tại stage Interview
        if 'priority' in vals and vals['priority'] != '0':
            for rec in self:
                if (
                    rec.recruitment_type == 'store'
                    and rec.stage_id
                    and 'interview' in rec.stage_id.name.lower()
                ):
                    stage_type = rec.position_level or rec.recruitment_type
                    if rec.position_level == 'staff':
                        # Staff: Interview & OJE → Hired + email chúc mừng
                        domain = [
                            ('name', '=', 'Hired'),
                            ('hired_stage', '=', True),
                        ]
                        if stage_type:
                            domain.append(('recruitment_type', 'in', [stage_type, 'both']))
                        target_stage = self.env['hr.recruitment.stage'].search(domain, limit=1)
                        if target_stage:
                            rec.stage_id = target_stage.id
                    elif rec.position_level == 'management':
                        # Management: Interview → OJE
                        domain = [('name', '=', 'OJE')]
                        if stage_type:
                            domain.append(('recruitment_type', 'in', [stage_type, 'both']))
                        target_stage = self.env['hr.recruitment.stage'].search(domain, limit=1)
                        if target_stage:
                            rec.stage_id = target_stage.id
        # Bắt sự kiện chuyển stage thành 'Reject' hoặc tương tự để gửi email báo rớt
        if 'stage_id' in vals:
            for rec in self:
                # Kiểm tra xem trước đó ứng viên chưa ở stage Reject
                old_stage_id = old_stages.get(rec.id)
                if old_stage_id != vals['stage_id']:
                    new_stage = self.env['hr.recruitment.stage'].browse(vals['stage_id'])
                    
                    # === KIỂM TRA EMAIL CONFIGURE THEO JOB HOẶC THEO VÒNG (STAGE) ===
                    if not self.env.context.get('skip_stage_email') and not self.env.context.get('skip_rejection_email'):
                        stage_template = rec._get_email_template_resolution(resolve_stage_id=new_stage.id)
                        if stage_template and rec.email_from:
                            try:
                                rec._send_mail_async(stage_template, rec.id)
                                _logger.info("[STAGE_EMAIL] Sent dynamic stage email to %s for moving to %s", rec.email_from, new_stage.name)
                            except Exception as e:
                                _logger.error("[STAGE_EMAIL] Failed to send dynamic stage email to %s: %s", rec.email_from, str(e))
                            # Bỏ qua các check bên dưới để tránh gửi đúp (VD: Stage Reject có rule đè thì gửi template đè, không chạy template gốc)
                            continue

                    # 1. Stage Reject có thể có tên chứa chữ 'Reject'
                    if new_stage and 'reject' in new_stage.name.lower():
                        # Bỏ qua email rejection nếu đang dùng context flag (ví dụ OJE flow tự gửi email riêng)
                        if not self.env.context.get('skip_rejection_email'):
                            self._send_rejection_email(rec)

                    # 2. Stage Hired - Gửi email chúc mừng (Congratulations)
                    if new_stage and new_stage.hired_stage:
                        self._send_congrats_email(rec)

            self._maybe_send_interview_confirmation_on_stage_change(old_stages)
        return result

    def _send_congrats_email(self, applicant):
        """Gửi email chúc mừng cho ứng viên"""
        template = applicant._get_email_template_resolution(
            event_code="hired",
            fallback_xml_id="M02_P0204_00.email_congratulations"
        )
        if template and applicant.email_from:
            try:
                self._send_mail_async(template, applicant.id)
                _logger.info("[EVAL_AUTO] Queued async congrats email to %s", applicant.email_from)
            except Exception as e:
                _logger.error("[EVAL_AUTO] Failed to send congrats to %s: %s", applicant.email_from, str(e))

    def _send_rejection_email(self, applicant):
        """Gửi email thông báo rớt cho ứng viên"""
        template = applicant._get_email_template_resolution(
            event_code="reject",
            fallback_xml_id="M02_P0204_00.email_rejection"
        )
        if template and applicant.email_from:
            try:
                self._send_mail_async(template, applicant.id)
                _logger.info("[EVAL_AUTO] Queued async rejection email to %s", applicant.email_from)
            except Exception as e:
                _logger.error("[EVAL_AUTO] Failed to send rejection email to %s: %s", applicant.email_from, str(e))

    def _send_oje_rejection_email(self, applicant):
        """Gửi email thông báo rớt OJE cho ứng viên"""
        template = applicant._get_email_template_resolution(
            event_code="oje_reject",
            fallback_xml_id="M02_P0204_00.email_oje_rejection"
        )
        if template and applicant.email_from:
            try:
                self._send_mail_async(template, applicant.id)
                _logger.info("[OJE_AUTO] Queued async OJE rejection email to %s", applicant.email_from)
            except Exception as e:
                _logger.error("[OJE_AUTO] Failed to send OJE rejection email to %s: %s", applicant.email_from, str(e))

    # ==================== OJE & OFFER ACTIONS ====================

    def action_accept_stage(self):
        """Chấp nhận: OJE → Offer, Offer → Hired"""
        for rec in self:
            stage_type = rec.position_level or rec.recruitment_type
            current_name = rec.stage_id.name if rec.stage_id else ''
            if current_name == 'OJE':
                target_name = 'Offer'
            elif current_name == 'Offer':
                target_name = 'Hired'
            else:
                continue
            domain = [('name', '=', target_name)]
            if stage_type:
                domain.append(('recruitment_type', 'in', [stage_type, 'both']))
            target_stage = self.env['hr.recruitment.stage'].search(domain, limit=1)
            if target_stage:
                rec.stage_id = target_stage.id

    def action_reject_stage(self):
        """Từ chối: mở wizard nhập lý do"""
        self.ensure_one()
        return {
            'name': 'Lý do từ chối',
            'type': 'ir.actions.act_window',
            'res_model': 'applicant.get.refuse.reason',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_applicant_ids': self.ids,
                'active_ids': self.ids,
                'default_source_action': 'reject_stage'
            },
        }

    def _action_reject_stage_confirmed(self, reason):
        for rec in self:
            stage_type = rec.position_level or rec.recruitment_type
            domain = [('name', '=', 'Reject')]
            if stage_type:
                domain.append(('recruitment_type', 'in', [stage_type, 'both']))
            stage = self.env['hr.recruitment.stage'].search(domain, limit=1)
            if stage:
                rec.stage_id = stage.id
            rec.write({
                'document_approval_status': 'refused',
                'reject_reason': reason.strip() if reason else False,
            })
            rec.message_post(body=f"Từ chối ứng viên. Lý do: {reason}")

    def action_move_next_stage(self):
        """Chuyển sang giai đoạn tiếp theo"""
        self.ensure_one()
        if not self.stage_id:
            raise exceptions.UserError("Không xác định được giai đoạn hiện tại!")

        domain = [
            ("sequence", ">", self.stage_id.sequence),
        ]
        stage_type = self.position_level or self.recruitment_type
        if stage_type:
            domain.append(("recruitment_type", "in", [stage_type, "both"]))

        next_stage = self.env["hr.recruitment.stage"].search(
            domain, order="sequence asc", limit=1
        )

        if next_stage:
            self.stage_id = next_stage
        else:
            raise exceptions.UserError(
                "Đã ở giai đoạn cuối cùng, không thể chuyển tiếp!"
            )

    # ==================== SURVEY UNDER REVIEW ACTIONS ====================

    def action_approve_survey_review(self):
        """HR xem xét xong → tiếp tục pipeline sau Survey (Interview hoặc Survey Passed)"""
        for rec in self:
            stage_type = rec._get_pipeline_stage_type()
            # Route giống survey pass: staff → Interview & OJE, management → Interview
            if rec.recruitment_type == 'store' and rec.position_level == 'staff':
                target_name = "Interview & OJE"
            elif rec.recruitment_type == 'store' and rec.position_level == 'management':
                target_name = "Interview"
            else:
                target_name = "Survey Passed"
            domain = [("name", "=", target_name)]
            if stage_type:
                domain.append(("recruitment_type", "in", [stage_type, "both"]))
            target_stage = self.env["hr.recruitment.stage"].search(domain, limit=1)
            if not target_stage:
                target_stage = self.env["hr.recruitment.stage"].search([("name", "=", target_name)], limit=1)
            if target_stage:
                rec.stage_id = target_stage
                rec.survey_under_review_date = False
            else:
                _logger.warning("[SURVEY_REVIEW] Không tìm thấy stage '%s' pipeline '%s'", target_name, stage_type)

    def action_move_to_store_interview(self):
        """Chuyển ứng viên từ Survey Passed → Interview & OJE (staff) hoặc Interview (management).
        Chỉ có tác dụng với store jobs. Được gọi bằng nút trên form header.
        """
        for rec in self:
            if rec.recruitment_type != 'store':
                continue
            stage_type = rec._get_pipeline_stage_type()
            if rec.position_level == 'staff':
                target_name = "Interview & OJE"
            else:
                target_name = "Interview"

            domain = [("name", "=", target_name)]
            if stage_type:
                domain.append(("recruitment_type", "in", [stage_type, "both"]))
            target_stage = self.env["hr.recruitment.stage"].search(domain, limit=1)
            if not target_stage:
                target_stage = self.env["hr.recruitment.stage"].search([("name", "=", target_name)], limit=1)
            if target_stage:
                rec.stage_id = target_stage
                _logger.info("[STORE_INTERVIEW] %s → '%s'", rec.partner_name, target_stage.name)
            else:
                raise exceptions.UserError(f"Không tìm thấy stage '{target_name}' cho pipeline '{stage_type}'!")


    def action_reject_survey_review(self):
        """HR quyết định không duyệt → mở wizard nhập lý do"""
        self.ensure_one()
        return {
            'name': 'Lý do từ chối survey',
            'type': 'ir.actions.act_window',
            'res_model': 'applicant.get.refuse.reason',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_applicant_ids': self.ids,
                'active_ids': self.ids,
                'default_source_action': 'reject_survey'
            },
        }

    def _action_reject_survey_review_confirmed(self, reason):
        for rec in self:
            stage_type = rec._get_pipeline_stage_type()
            domain = [("name", "=", "Reject")]
            if stage_type:
                domain.append(("recruitment_type", "in", [stage_type, "both"]))
            stage = self.env["hr.recruitment.stage"].search(domain, limit=1)
            if stage:
                rec.stage_id = stage
            rec.write({
                'survey_under_review_date': False,
                'document_approval_status': 'refused',
                'reject_reason': reason.strip() if reason else False,
            })
            rec.message_post(body=f"Từ chối Survey. Lý do: {reason}")

    # ==================== OJE EVALUATION ACTIONS ====================

    def _build_store_staff_fail_reason(self, evaluation):
        self.ensure_one()
        reasons = []

        ni_lines = evaluation.line_ids.filtered(
            lambda l: l.is_active and l.line_kind == 'staff_question' and l.staff_rating == 'ni'
        )
        if ni_lines:
            labels = [line.question_text or line.name for line in ni_lines]
            reasons.append(_("Có tiêu chí bị đánh giá NI: %s") % "; ".join(labels))

        if evaluation.staff_decision in ('reject', 'other_position'):
            decision_label = dict(evaluation._fields['staff_decision'].selection).get(
                evaluation.staff_decision,
                evaluation.staff_decision,
            )
            reasons.append(_("Kết luận cuối cùng: %s.") % decision_label)

        return "\n".join(reasons) if reasons else _("Không đạt theo tiêu chuẩn đánh giá Staff.")

    def _build_store_management_fail_reason(self, evaluation):
        self.ensure_one()
        return _("Overall rating dưới ngưỡng đạt (>= 3): %s/5.") % (evaluation.management_overall_rating or 0)

    def _build_legacy_oje_fail_reason(self, evaluation):
        self.ensure_one()
        fail_reasons = []
        for line in evaluation.line_ids:
            if line.field_type == 'text':
                if line.text_score < line.text_max_score:
                    fail_reasons.append(
                        f"- {line.name}: {line.text_score}/{line.text_max_score} điểm. "
                        f"Nhận xét: {line.text_value or 'N/A'}"
                    )
            elif line.field_type == 'checkbox':
                if not line.checkbox_value:
                    fail_reasons.append(f"- {line.name}: Không đạt (0/{line.checkbox_score} điểm)")
            elif line.field_type == 'radio':
                max_opt_score = max(line.template_line_id.option_ids.mapped('score'), default=0)
                if line.selected_option_score < max_opt_score:
                    selected_name = line.selected_option_id.name if line.selected_option_id else 'N/A'
                    fail_reasons.append(
                        f"- {line.name}: {selected_name} ({line.selected_option_score}/{max_opt_score} điểm)"
                    )
        return "\n".join(fail_reasons) if fail_reasons else _("Không đáp ứng tiêu chuẩn OJE chung.")

    def _find_oje_target_stage(self, stage_name, use_hired_flag=False, ilike=False):
        self.ensure_one()
        stage_type = self._get_pipeline_stage_type()
        comparator = 'ilike' if ilike else '='

        domain = [("name", comparator, stage_name)]
        if use_hired_flag:
            domain.append(("hired_stage", "=", True))
        if stage_type:
            domain.append(("recruitment_type", "in", [stage_type, "both"]))

        stage = self.env["hr.recruitment.stage"].sudo().search(domain, limit=1)
        if stage:
            return stage

        fallback_domain = [("name", comparator, stage_name)]
        if use_hired_flag:
            fallback_domain.append(("hired_stage", "=", True))
        stage = self.env["hr.recruitment.stage"].sudo().search(fallback_domain, limit=1)
        if stage:
            return stage

        if use_hired_flag:
            plain_domain = [("name", comparator, stage_name)]
            if stage_type:
                plain_domain.append(("recruitment_type", "in", [stage_type, "both"]))
            stage = self.env["hr.recruitment.stage"].sudo().search(plain_domain, limit=1)
            if stage:
                return stage

        return stage

    def action_apply_oje_evaluation_result(self):
        """Áp kết quả OJE theo scope template mới, fallback legacy cho bản ghi cũ."""
        self.ensure_one()
        evaluation = self.oje_evaluation_id
        if not evaluation or evaluation.state != 'done':
            raise exceptions.UserError("Phiếu đánh giá OJE chưa hoàn thành!")

        scope = evaluation.template_scope or 'legacy'
        if scope == 'store_staff':
            is_pass = bool(evaluation.staff_decision == 'hire' and not evaluation.has_any_ni)
        elif scope == 'store_management':
            is_pass = bool((evaluation.management_overall_rating or 0) >= 3)
        else:
            is_pass = bool(evaluation.result == 'pass')

        if is_pass:
            if self.position_level == 'management':
                target_stage = self._find_oje_target_stage('Offer')
                missing_stage_label = 'Offer'
            else:
                target_stage = self._find_oje_target_stage('Hired', use_hired_flag=True)
                missing_stage_label = 'Hired'

            if not target_stage:
                raise exceptions.UserError(f"Không tìm thấy Stage '{missing_stage_label}'!")

            self.write({
                'stage_id': target_stage.id,
                'oje_fail_reason': False,
            })
        else:
            target_stage = self._find_oje_target_stage('Reject', ilike=True)
            if not target_stage:
                raise exceptions.UserError("Không tìm thấy Stage 'Reject'!")

            if scope == 'store_staff':
                fail_reason = self._build_store_staff_fail_reason(evaluation)
            elif scope == 'store_management':
                fail_reason = self._build_store_management_fail_reason(evaluation)
            else:
                fail_reason = self._build_legacy_oje_fail_reason(evaluation)

            self.with_context(skip_rejection_email=True).write({
                'stage_id': target_stage.id,
                'document_approval_status': 'refused',
                'oje_fail_reason': fail_reason,
            })

            self._send_oje_rejection_email(self)

    # Legacy action (can be removed later)
    def action_check_oje_result(self):
        return self.action_apply_oje_evaluation_result()

    def action_create_oje_survey(self):
        """Legacy action: deprecated. See portal logic for new evaluation creation."""
        raise exceptions.UserError("Hệ thống đã chuyển sang mẫu đánh giá động. Vui lòng thực hiện trên Portal.")

    @api.model
    def action_auto_reject_stale_survey_reviews(self):
        """Scheduled action: sau 24h ở Under Review (do sai câu bắt buộc) mà không xử lý → Reject tự động"""
        from datetime import datetime, timedelta
        cutoff = fields.Datetime.now() - timedelta(hours=24)
        stale = self.search([
            ('survey_under_review_date', '!=', False),
            ('survey_under_review_date', '<', cutoff),
        ])
        _logger.info("[AUTO_REJECT] Found %d records overdue Under Review review", len(stale))
        for rec in stale:
            stage_type = rec.position_level or rec.recruitment_type
            domain = [("name", "=", "Reject")]
            if stage_type:
                domain.append(("recruitment_type", "in", [stage_type, "both"]))
            stage = self.env["hr.recruitment.stage"].search(domain, limit=1)
            if stage:
                rec.stage_id = stage
            rec.survey_under_review_date = False
            rec.document_approval_status = 'refused'
            _logger.info("[AUTO_REJECT] Auto-rejected applicant id=%d (%s)", rec.id, rec.partner_name)
