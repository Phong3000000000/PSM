# -*- coding: utf-8 -*-
"""
Extend HR Applicant
Thêm các trường liên quan đến lịch phỏng vấn và khảo sát
"""

from odoo import models, fields, api, exceptions, _, SUPERUSER_ID
from odoo.exceptions import AccessError
from odoo.modules.registry import Registry
from datetime import timedelta
import json
import html
import re
import logging
import base64
import threading
import unicodedata

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
        help="Dùng để lọc stage dropdown theo 3 family office/staff/management.",
    )

    def _x_psm_normalize_stage_type(self, recruitment_type=False, position_level=False):
        """Normalize raw recruitment hints to canonical stage family keys."""
        if recruitment_type == 'office':
            return 'office'
        if recruitment_type == 'store':
            return position_level if position_level in ('staff', 'management') else False
        if recruitment_type in ('staff', 'management'):
            return recruitment_type
        if position_level in ('staff', 'management'):
            return position_level
        return False

    def _get_pipeline_stage_type(self):
        """Return the stage type key for pipeline filtering.
        Store jobs use position_level (staff/management).
        Office jobs always use 'office'.
        """
        self.ensure_one()
        return self._x_psm_normalize_stage_type(
            recruitment_type=self.recruitment_type,
            position_level=self.position_level,
        )

    @api.depends("position_level", "recruitment_type")
    def _compute_stage_filter_type(self):
        for rec in self:
            rec.stage_filter_type = rec._get_pipeline_stage_type()

    def _x_psm_stage_scope_domain(self, stage_type=None, include_office_visibility=True):
        """Build stage scope domain with job_ids as primary filter.

        recruitment_type/office flags are retained as secondary filters to keep
        existing flow semantics while allowing job-specific stage reuse.
        """
        self.ensure_one()
        scope_domain = []

        if self.job_id:
            scope_domain.extend([
                '|',
                ('job_ids', '=', False),
                ('job_ids', '=', self.job_id.id),
            ])

        stage_type = stage_type or self._get_pipeline_stage_type()
        if not stage_type:
            if self.recruitment_type == 'store':
                scope_domain.append(('id', '=', 0))
            return scope_domain

        scope_domain.append(('recruitment_type', '=', stage_type))
        if include_office_visibility and stage_type == 'office':
            scope_domain.extend([
                '|',
                ('office_pipeline_visible', '=', True),
                ('recruitment_type', '!=', 'office'),
            ])

        return scope_domain

    def _x_psm_stage_matches_scope(self, stage, stage_type=None):
        """Check whether a stage is valid for the current applicant scope."""
        self.ensure_one()
        if not stage:
            return False

        if self.job_id and stage.job_ids and self.job_id not in stage.job_ids:
            return False

        stage_type = stage_type or self._get_pipeline_stage_type()
        if self.recruitment_type == 'store' and not stage_type:
            return False
        if stage_type and stage.recruitment_type != stage_type:
            return False

        if (
            stage_type == 'office'
            and stage.recruitment_type == 'office'
            and 'office_pipeline_visible' in stage._fields
            and not stage.office_pipeline_visible
        ):
            return False

        return True

    def _x_psm_get_stage_xmlid_candidates(self, stage_name):
        """Return ordered XMLID candidates for a logical stage name.

        XMLID resolution is preferred to reduce dependency on translated/display
        stage names. Name-based search remains as fallback for compatibility.
        """
        self.ensure_one()
        key = (stage_name or '').strip().lower()
        stage_type = self._get_pipeline_stage_type()
        candidates = []

        if key in ('under review', 'under_review'):
            if stage_type == 'staff':
                candidates.append('M02_P0204.stage_staff_under_review')
            elif stage_type == 'management':
                candidates.append('M02_P0204.stage_mgmt_under_review')
            elif stage_type == 'office':
                candidates.append('M02_P0205.stage_office_screening')
            else:
                candidates.extend([
                    'M02_P0204.stage_staff_under_review',
                    'M02_P0204.stage_mgmt_under_review',
                ])
        elif key in ('interview & oje', 'interview and oje', 'interview_oje'):
            candidates.append('M02_P0204.stage_staff_interview_oje')
        elif key == 'interview':
            if stage_type == 'office':
                candidates.append('M02_P0205.stage_office_interview_1')
            elif stage_type == 'staff':
                candidates.append('M02_P0204.stage_staff_interview_oje')
            elif stage_type == 'management':
                candidates.append('M02_P0204.stage_mgmt_interview')
            else:
                candidates.extend([
                    'M02_P0204.stage_mgmt_interview',
                    'M02_P0204.stage_staff_interview_oje',
                ])
        elif key == 'oje':
            if stage_type == 'staff':
                candidates.append('M02_P0204.stage_staff_interview_oje')
            elif stage_type == 'management':
                candidates.append('M02_P0204.stage_mgmt_oje')
            else:
                candidates.append('M02_P0204.stage_staff_interview_oje')
        elif key == 'offer':
            if stage_type == 'office':
                candidates.append('M02_P0205.stage_office_proposal')
            candidates.append('M02_P0204.stage_mgmt_offer')
        elif key in ('hired', 'contract signed'):
            if stage_type == 'office':
                candidates.append('M02_P0205.stage_office_hired')
            if stage_type == 'staff':
                candidates.append('M02_P0204.stage_staff_hired')
            elif stage_type == 'management':
                candidates.append('M02_P0204.stage_mgmt_hired')
            else:
                candidates.extend([
                    'M02_P0204.stage_staff_hired',
                    'M02_P0204.stage_mgmt_hired',
                ])
        elif key == 'reject':
            if stage_type == 'office':
                candidates.append('M02_P0205.stage_office_reject')
            if stage_type == 'staff':
                candidates.append('M02_P0204.stage_staff_reject')
            elif stage_type == 'management':
                candidates.append('M02_P0204.stage_mgmt_reject')
            else:
                candidates.extend([
                    'M02_P0204.stage_staff_reject',
                    'M02_P0204.stage_mgmt_reject',
                ])
        elif key == 'screening':
            candidates.append('M02_P0205.stage_office_screening')

        # Deduplicate while preserving order.
        seen = set()
        deduped = []
        for xmlid in candidates:
            if xmlid in seen:
                continue
            seen.add(xmlid)
            deduped.append(xmlid)
        return deduped

    def _x_psm_resolve_stage(self, stage_name, ilike=False, use_hired_flag=False, stage_type=None):
        """Resolve a target stage using XMLID-first then name-based fallback."""
        self.ensure_one()
        stage_type = stage_type or self._get_pipeline_stage_type()
        if self.recruitment_type == 'store' and not stage_type:
            return self.env['hr.recruitment.stage']
        stage_model = self.env['hr.recruitment.stage'].sudo()

        # 1) XMLID-first lookup
        for xmlid in self._x_psm_get_stage_xmlid_candidates(stage_name):
            stage = self.env.ref(xmlid, raise_if_not_found=False)
            if not stage or not stage.exists():
                continue
            if use_hired_flag and not stage.hired_stage:
                continue
            if stage_type and not self._x_psm_stage_matches_scope(stage, stage_type=stage_type):
                continue
            return stage

        # 2) Name-based scoped fallback
        comparator = 'ilike' if ilike else '='
        domain = []
        if self.job_id:
            domain.extend([
                '|',
                ('job_ids', '=', False),
                ('job_ids', '=', self.job_id.id),
            ])

        domain.append(('name', comparator, stage_name))

        if stage_type:
            domain.append(('recruitment_type', '=', stage_type))
            if stage_type == 'office':
                domain.extend([
                    '|',
                    ('office_pipeline_visible', '=', True),
                    ('recruitment_type', '!=', 'office'),
                ])

        if use_hired_flag:
            domain.append(('hired_stage', '=', True))

        stage = stage_model.search(domain, order='sequence asc', limit=1)
        if stage:
            return stage

        # 3) Generic fallback by name, still scoped by job_ids when possible.
        generic_domain = []
        if self.job_id:
            generic_domain.extend([
                '|',
                ('job_ids', '=', False),
                ('job_ids', '=', self.job_id.id),
            ])
        generic_domain.append(('name', comparator, stage_name))
        if use_hired_flag:
            generic_domain.append(('hired_stage', '=', True))
        stage = stage_model.search(generic_domain, order='sequence asc', limit=1)
        if stage and (not stage_type or self._x_psm_stage_matches_scope(stage, stage_type=stage_type)):
            return stage
        return self.env['hr.recruitment.stage']

    def _x_psm_is_interview_stage_record(self, stage):
        """Determine whether a stage belongs to the interview family."""
        self.ensure_one()
        if not stage:
            return False

        interview_xmlids = (
            self._x_psm_get_stage_xmlid_candidates('Interview')
            + self._x_psm_get_stage_xmlid_candidates('Interview & OJE')
        )
        for xmlid in interview_xmlids:
            target = self.env.ref(xmlid, raise_if_not_found=False)
            if target and target.id == stage.id:
                return True

        return bool('interview' in (stage.name or '').lower())

    interview_schedule_id = fields.Many2one(
        "x_psm_interview_schedule",
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
        schedules = self.env["x_psm_interview_schedule"].search([
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
            if not applicant.job_id:
                continue

            stage_type = applicant._get_pipeline_stage_type()
            if applicant.stage_id and applicant._x_psm_stage_matches_scope(applicant.stage_id, stage_type=stage_type):
                continue

            correct_stage = self.env['hr.recruitment.stage'].search(
                applicant._x_psm_stage_scope_domain(stage_type=stage_type) + [('fold', '=', False)],
                order='sequence asc',
                limit=1,
            )
            if not correct_stage and applicant.job_id:
                correct_stage = self.env['hr.recruitment.stage'].search([
                    '|',
                    ('job_ids', '=', False),
                    ('job_ids', '=', applicant.job_id.id),
                    ('fold', '=', False),
                ], order='sequence asc', limit=1)
            if correct_stage:
                applicant.stage_id = correct_stage.id

    @api.model
    def _get_target_pipeline_stage(self, stage_name, recruitment_type='store', position_level='staff', job=None):
        """Helper tiêu chuẩn tìm stage theo dạng fallback, giảm lặp code."""
        job = job or (self[:1].job_id if self else False)
        domain = [('name', '=', stage_name)]

        if job:
            domain.extend([
                '|',
                ('job_ids', '=', False),
                ('job_ids', '=', job.id),
            ])

        if recruitment_type == 'store':
            stage_type = position_level if position_level in ('staff', 'management') else False
        elif recruitment_type in ('office', 'staff', 'management'):
            stage_type = recruitment_type
        else:
            stage_type = False

        if not stage_type:
            return self.env['hr.recruitment.stage'].sudo()

        domain.append(('recruitment_type', '=', stage_type))
        if stage_type == 'office':
            domain.extend([
                '|',
                ('office_pipeline_visible', '=', True),
                ('recruitment_type', '!=', 'office'),
            ])
            
        stage = self.env['hr.recruitment.stage'].sudo().search(domain, order='sequence asc', limit=1)
        if not stage and job:
            fallback_domain = [
                ('name', '=', stage_name),
                '|',
                ('job_ids', '=', False),
                ('job_ids', '=', job.id),
                ('recruitment_type', '=', stage_type),
            ]
            if stage_type == 'office':
                fallback_domain.extend([
                    '|',
                    ('office_pipeline_visible', '=', True),
                    ('recruitment_type', '!=', 'office'),
                ])
            stage = self.env['hr.recruitment.stage'].sudo().search(
                fallback_domain,
                order='sequence asc',
                limit=1,
            )
        if not stage:
            fallback_domain = [
                ('name', '=', stage_name),
                ('recruitment_type', '=', stage_type),
            ]
            if stage_type == 'office':
                fallback_domain.extend([
                    '|',
                    ('office_pipeline_visible', '=', True),
                    ('recruitment_type', '!=', 'office'),
                ])
            stage = self.env['hr.recruitment.stage'].sudo().search(
                fallback_domain,
                order='sequence asc',
                limit=1,
            )
        return stage

    # ==================== SURVEY ====================

    pre_interview_survey_id = fields.Many2one(
        "survey.survey",
        string="Khảo Sát",
        domain=[
            ("x_psm_survey_usage", "=", "pre_interview"),
            ("x_psm_0204_is_runtime_isolated_copy", "=", False),
        ],
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
        ('passed', 'Đạt'),
        ('review', 'Cần xem xét'),
        ('reject', 'Reject ngay'),
    ], string="Kết quả biểu mẫu", compute="_compute_application_match_result", store=False)

    application_form_review_payload = fields.Text(
        string="Chi tiết biểu mẫu ứng tuyển (JSON)",
        copy=False,
        readonly=True,
    )

    application_form_review_html = fields.Html(
        string="Chi tiết biểu mẫu ứng tuyển",
        compute="_compute_application_form_review_html",
        sanitize=False,
    )

    failed_mandatory_questions = fields.Html(string="Sai câu bắt buộc (Thông tin chung)", readonly=True)

    def _x_psm_normalize_plain_text(self, value):
        value = value or ''
        value = unicodedata.normalize('NFD', value)
        value = ''.join(ch for ch in value if unicodedata.category(ch) != 'Mn')
        value = value.lower()
        return re.sub(r'[^a-z0-9]+', ' ', value).strip()

    def _x_psm_parse_application_form_review_payload(self):
        self.ensure_one()
        raw_payload = (self.application_form_review_payload or '').strip()
        if not raw_payload:
            return {}

        try:
            payload = json.loads(raw_payload)
        except Exception as error_exc:
            _logger.warning(
                "[APPLICATION_FORM_REVIEW] Cannot parse payload for applicant %s: %s",
                self.id,
                error_exc,
            )
            return {}

        if isinstance(payload, list):
            return {'version': 1, 'lines': payload}
        if isinstance(payload, dict):
            return payload
        return {}

    def _x_psm_resolve_review_line_result(self, review_line):
        if not isinstance(review_line, dict):
            return 'passed'

        result = review_line.get('result')
        if result in ('passed', 'review', 'reject'):
            return result

        if review_line.get('is_correct') is False:
            return 'reject' if review_line.get('reject_when_wrong') else 'review'
        return 'passed'

    @api.depends('application_form_review_payload', 'failed_mandatory_questions')
    def _compute_application_match_result(self):
        for rec in self:
            payload = rec._x_psm_parse_application_form_review_payload()
            review_lines = payload.get('lines') if isinstance(payload, dict) else []

            has_reject = any(rec._x_psm_resolve_review_line_result(line) == 'reject' for line in review_lines or [])
            has_review = any(rec._x_psm_resolve_review_line_result(line) == 'review' for line in review_lines or [])

            if has_reject:
                rec.application_match_result = 'reject'
                continue
            if has_review:
                rec.application_match_result = 'review'
                continue

            legacy_failed_html = str(rec.failed_mandatory_questions or '')
            legacy_has_failed = bool(legacy_failed_html and '<ul>' in legacy_failed_html)
            if legacy_has_failed:
                normalized_legacy = rec._x_psm_normalize_plain_text(re.sub(r'<[^>]+>', ' ', legacy_failed_html))
                if 'loai khi sai' in normalized_legacy or 'reject ngay' in normalized_legacy:
                    rec.application_match_result = 'reject'
                else:
                    rec.application_match_result = 'review'
            else:
                rec.application_match_result = 'passed'

    @api.depends('application_form_review_payload', 'failed_mandatory_questions', 'application_match_result')
    def _compute_application_form_review_html(self):
        status_label_map = {
            'passed': 'Đạt',
            'review': 'Cần xem xét',
            'reject': 'Reject ngay',
        }
        status_badge_class_map = {
            'passed': 'badge bg-success',
            'review': 'badge bg-warning text-dark',
            'reject': 'badge bg-danger',
        }

        for rec in self:
            payload = rec._x_psm_parse_application_form_review_payload()
            review_lines = payload.get('lines') if isinstance(payload, dict) else []
            review_lines = [line for line in (review_lines or []) if isinstance(line, dict)]

            if not review_lines:
                rec.application_form_review_html = (
                    rec.failed_mandatory_questions
                    or '<p class="text-muted mb-0">Chưa có dữ liệu rà soát tự động cho biểu mẫu ứng tuyển.</p>'
                )
                continue

            passed_count = 0
            review_count = 0
            reject_count = 0
            row_html_parts = []

            for index, line in enumerate(review_lines, start=1):
                line_result = rec._x_psm_resolve_review_line_result(line)
                if line_result == 'passed':
                    passed_count += 1
                elif line_result == 'review':
                    review_count += 1
                elif line_result == 'reject':
                    reject_count += 1

                question_label = html.escape(str(line.get('question_label') or line.get('field_name') or _('Câu hỏi %s') % index))
                selected_answer = html.escape(str(line.get('selected_answer') or '-'))

                correct_answers = [
                    str(answer)
                    for answer in (line.get('correct_answers') or [])
                    if answer not in (None, '')
                ]
                correct_answer_text = html.escape(', '.join(correct_answers) if correct_answers else '-')

                rule_labels = []
                if line.get('mandatory_correct'):
                    rule_labels.append('Phải đúng')
                if line.get('reject_when_wrong'):
                    rule_labels.append('Loại khi sai')
                rule_text = html.escape(', '.join(rule_labels) if rule_labels else '-')

                status_label = html.escape(status_label_map.get(line_result, 'Đạt'))
                status_badge_class = status_badge_class_map.get(line_result, 'badge bg-success')

                row_html_parts.append(
                    (
                        '<tr>'
                        f'<td class="text-center">{index}</td>'
                        f'<td>{question_label}</td>'
                        f'<td>{selected_answer}</td>'
                        f'<td>{correct_answer_text}</td>'
                        f'<td>{rule_text}</td>'
                        f'<td class="text-center"><span class="{status_badge_class}">{status_label}</span></td>'
                        '</tr>'
                    )
                )

            summary_html = (
                '<div class="d-flex flex-wrap gap-2 mb-3">'
                f'<span class="badge bg-success">Đạt: {passed_count}</span>'
                f'<span class="badge bg-warning text-dark">Cần xem xét: {review_count}</span>'
                f'<span class="badge bg-danger">Reject ngay: {reject_count}</span>'
                '</div>'
            )

            table_html = (
                '<div class="table-responsive w-100">'
                '<table class="table table-sm table-bordered align-middle mb-0 w-100">'
                '<thead class="table-light">'
                '<tr>'
                '<th class="text-center" style="width: 56px;">#</th>'
                '<th>Câu hỏi</th>'
                '<th>Ứng viên trả lời</th>'
                '<th>Đáp án đúng</th>'
                '<th>Rule</th>'
                '<th class="text-center" style="width: 130px;">Kết quả</th>'
                '</tr>'
                '</thead>'
                '<tbody>'
                + ''.join(row_html_parts)
                + '</tbody>'
                '</table>'
                '</div>'
            )

            rec.application_form_review_html = summary_html + table_html

    def action_show_failed_questions(self):
        self.ensure_one()
        # View popup wizard or fallback
        view_id = self.env.ref('M02_P0204.view_hr_applicant_application_result_popup', raise_if_not_found=False)
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

    # ==================== INTERVIEW EVALUATION (STORE MANAGEMENT) ====================

    interview_evaluator_user_id = fields.Many2one(
        "res.users",
        string="Người đánh giá Interview",
        tracking=True,
        help="Người chịu trách nhiệm đánh giá Interview cho ứng viên này (snapshot từ Job).",
    )

    interview_evaluation_id = fields.Many2one(
        "x_psm_hr_applicant_interview_evaluation",
        string="Phiếu Đánh Giá Interview",
        copy=False,
        readonly=True,
    )

    interview_evaluation_state = fields.Selection(
        related="interview_evaluation_id.state",
        string="Trạng Thái Interview",
        store=True,
    )

    can_backend_evaluate_interview = fields.Boolean(
        compute='_compute_can_backend_evaluate_interview',
        string='Có thể đánh giá Interview trên backend',
    )

    @api.depends('interview_evaluator_user_id', 'current_stage_name', 'interview_evaluation_state', 'job_id')
    def _compute_can_backend_evaluate_interview(self):
        user = self.env.user
        is_hr_manager = user.has_group('M02_P0200.GDH_RST_HR_RECRUITMENT_M')
        for rec in self:
            assigned_user = rec.interview_evaluator_user_id or rec.job_id.interview_evaluator_user_id
            rec.can_backend_evaluate_interview = bool(
                rec.job_id
                and rec.recruitment_type == 'store'
                and rec.position_level == 'management'
                and rec.current_stage_name == 'Interview'
                and rec.interview_evaluation_state != 'done'
                and (
                    is_hr_manager
                    or (assigned_user and assigned_user == user)
                )
            )

    def _check_backend_interview_access(self, user=False):
        self.ensure_one()
        current_user = user or self.env.user
        applicant = self.sudo()

        if current_user.has_group('M02_P0200.GDH_RST_HR_RECRUITMENT_M'):
            return True

        assigned_user = applicant.interview_evaluator_user_id or applicant.job_id.interview_evaluator_user_id
        if assigned_user and current_user == assigned_user:
            return True

        raise AccessError(_("Bạn không có quyền đánh giá Interview cho ứng viên này."))

    def _is_interview_stage_allowed(self):
        self.ensure_one()
        return self.current_stage_name == 'Interview'

    def _get_interview_snapshot_source(self):
        self.ensure_one()
        interview_survey = self.job_id._x_psm_get_interview_survey() if hasattr(self.job_id, '_x_psm_get_interview_survey') else False
        if not interview_survey:
            raise exceptions.UserError(_("Job chưa cấu hình Survey Interview."))

        snapshot_sections = self.job_id._x_psm_prepare_interview_snapshot_sections() if hasattr(self.job_id, '_x_psm_prepare_interview_snapshot_sections') else []
        if not snapshot_sections:
            raise exceptions.UserError(_("Survey Interview chưa có câu hỏi để sinh phiếu đánh giá."))

        raw_version = interview_survey.write_date or interview_survey.create_date
        template_version = fields.Datetime.to_string(raw_version) if raw_version else '1.0'
        config_signature = self.job_id._get_interview_config_signature() if hasattr(self.job_id, '_get_interview_config_signature') else False

        return template_version, config_signature, snapshot_sections

    def _populate_interview_evaluation_snapshot(self, evaluation, snapshot_sections):
        self.ensure_one()
        line_vals = []

        for section_data in snapshot_sections:
            eval_section = self.env['x_psm_hr_applicant_interview_evaluation_section'].create({
                'evaluation_id': evaluation.id,
                'source_config_section_id': section_data.get('source_question_id') or False,
                'sequence': section_data.get('sequence', 10),
                'name': section_data.get('name') or _('Interview Section'),
                'is_active': section_data.get('is_active', True),
            })

            for line_data in section_data.get('lines', []):
                display_type = line_data.get('display_type') or 'question'
                group_kind = line_data.get('x_psm_interview_group_kind') or (
                    'subheader' if display_type in ('section', 'subheader') else 'question'
                )
                line_vals.append({
                    'evaluation_id': evaluation.id,
                    'section_id': eval_section.id,
                    'template_line_id': line_data.get('source_question_id') or False,
                    'sequence': line_data.get('sequence', 10),
                    'display_type': display_type,
                    'label': line_data.get('label') or False,
                    'question_text': line_data.get('question_text') or False,
                    'x_psm_interview_group_kind': group_kind,
                    'x_psm_interview_group_label': line_data.get('x_psm_interview_group_label') or False,
                    'is_required': line_data.get('is_required', True) if display_type == 'question' else False,
                    'is_active': line_data.get('is_active', True),
                })

        if line_vals:
            self.env['x_psm_hr_applicant_interview_evaluation_line'].create(line_vals)

    def _ensure_interview_evaluation(self, evaluator_user=None):
        self.ensure_one()

        if not self.job_id:
            raise exceptions.UserError(_("Ứng viên chưa có Job Position."))

        if not (self.recruitment_type == 'store' and self.position_level == 'management'):
            raise exceptions.UserError(_("Chỉ hỗ trợ đánh giá Interview cho scope Store + Management."))

        if not self.job_id.x_psm_interview_survey_id:
            raise exceptions.UserError(_("Job chưa cấu hình Survey Interview."))

        evaluator = evaluator_user or self.interview_evaluator_user_id or self.job_id.interview_evaluator_user_id or self.env.user
        template_version, config_signature, snapshot_sections = self._get_interview_snapshot_source()

        if self.interview_evaluation_id:
            evaluation = self.interview_evaluation_id

            if evaluation.state != 'done':
                has_sections = bool(evaluation.section_ids.filtered('is_active'))
                has_questions = bool(evaluation.line_ids.filtered(
                    lambda line: line.is_active and line.display_type == 'question'
                ))
                needs_refresh = bool(
                    evaluation.config_signature != config_signature
                    or not has_sections
                    or not has_questions
                )

                if needs_refresh:
                    evaluation.line_ids.unlink()
                    evaluation.section_ids.unlink()
                    evaluation.write({
                        'template_version': template_version,
                        'config_signature': config_signature,
                        'evaluator_user_id': evaluator.id,
                        'interviewer_name': evaluation.interviewer_name or evaluator.name,
                        'state': 'in_progress',
                    })
                    self._populate_interview_evaluation_snapshot(evaluation, snapshot_sections)
                elif not evaluation.evaluator_user_id:
                    evaluation.write({'evaluator_user_id': evaluator.id})

            if self.interview_evaluator_user_id != evaluator:
                self.write({'interview_evaluator_user_id': evaluator.id})
            return evaluation

        evaluation = self.env['x_psm_hr_applicant_interview_evaluation'].create({
            'applicant_id': self.id,
            'job_id': self.job_id.id,
            'evaluator_user_id': evaluator.id,
            'state': 'in_progress',
            'template_version': template_version,
            'config_signature': config_signature,
            'interview_date': fields.Date.today(),
            'interviewer_name': evaluator.name,
        })
        self._populate_interview_evaluation_snapshot(evaluation, snapshot_sections)

        self.write({
            'interview_evaluation_id': evaluation.id,
            'interview_evaluator_user_id': evaluator.id,
        })
        return evaluation

    def action_open_backend_interview_evaluation(self):
        self.ensure_one()
        self._check_backend_interview_access()

        if not self._is_interview_stage_allowed():
            raise exceptions.UserError(_("Chỉ có thể đánh giá Interview khi ứng viên đang ở stage Interview."))

        evaluation = self._ensure_interview_evaluation(evaluator_user=self.env.user)
        return {
            'type': 'ir.actions.act_url',
            'name': _('Pass Interview'),
            'url': f'/recruitment/interview/internal/{evaluation.id}',
            'target': 'new',
        }

    interview_final_score = fields.Float(
        related="interview_evaluation_id.final_score",
        string="Điểm Interview",
        store=True,
    )

    interview_result = fields.Selection(
        related="interview_evaluation_id.result",
        string="Kết Quả Interview",
        store=True,
    )

    interview_evaluated_by = fields.Many2one(
        related="interview_evaluation_id.evaluator_user_id",
        string="Người Đánh Giá Interview",
        store=True,
    )

    interview_evaluated_at = fields.Datetime(
        related="interview_evaluation_id.submitted_at",
        string="Ngày Đánh Giá Interview",
        store=True,
    )

    interview_fail_reason = fields.Text(
        string="Lý do không đạt Interview",
        copy=False,
    )

    # ==================== OJE EVALUATION (DYNAMIC) ====================

    oje_evaluator_user_id = fields.Many2one(
        "res.users",
        string="Người đánh giá OJE",
        index=True,
        tracking=True,
        help="Người chịu trách nhiệm đánh giá OJE cho ứng viên này (Snapshot từ Job)",
    )

    oje_evaluation_id = fields.Many2one(
        "x_psm_hr_applicant_oje_evaluation",
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
        is_hr_manager = user.has_group('M02_P0200.GDH_RST_HR_RECRUITMENT_M')
        for rec in self:
            rec.can_backend_evaluate_oje = bool(
                rec.job_id
                and rec.current_stage_name in ('Interview & OJE', 'OJE')
                and rec.oje_evaluation_state != 'done'
                and (
                    is_hr_manager
                    or (rec.oje_evaluator_user_id and rec.oje_evaluator_user_id == user)
                )
            )

    def _check_backend_oje_access(self, user=False):
        self.ensure_one()
        current_user = user or self.env.user
        applicant = self.sudo()

        if current_user.has_group('M02_P0200.GDH_RST_HR_RECRUITMENT_M'):
            return True
        if applicant.oje_evaluator_user_id and current_user == applicant.oje_evaluator_user_id:
            return True

        # Portal fallback: allow DM1 hierarchy access in managed departments.
        if current_user._x_psm_0204_is_store_portal_dm1():
            employee = current_user._x_psm_0204_get_portal_employee()
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
        template_scope = self.job_id._get_oje_template_scope() if hasattr(self.job_id, '_get_oje_template_scope') else False
        template_scope = template_scope or 'legacy'

        if template_scope not in ('store_staff', 'store_management'):
            raise exceptions.UserError(_("Chỉ hỗ trợ đánh giá OJE cho job thuộc khối Cửa hàng."))

        oje_survey = self.job_id._x_psm_get_oje_survey() if hasattr(self.job_id, '_x_psm_get_oje_survey') else False
        if not oje_survey:
            raise exceptions.UserError(_("Job chưa cấu hình Survey OJE."))

        snapshot_sections = self.job_id._x_psm_prepare_oje_snapshot_sections() if hasattr(self.job_id, '_x_psm_prepare_oje_snapshot_sections') else []
        if not snapshot_sections:
            raise exceptions.UserError(_("Survey OJE chưa có câu hỏi để sinh phiếu đánh giá."))

        raw_version = oje_survey.write_date or oje_survey.create_date
        template_version = fields.Datetime.to_string(raw_version) if raw_version else '1.0'
        config_signature = self.job_id._x_psm_get_oje_config_signature() if hasattr(self.job_id, '_x_psm_get_oje_config_signature') else False

        return template_scope, template_version, config_signature, snapshot_sections

    def _populate_oje_evaluation_snapshot(self, evaluation, template_scope, snapshot_sections):
        self.ensure_one()
        line_vals = []

        for section_data in snapshot_sections:
            eval_section = self.env['x_psm_hr_applicant_oje_evaluation_section'].create({
                'evaluation_id': evaluation.id,
                'source_config_section_id': section_data.get('source_question_id') or False,
                'sequence': section_data.get('sequence', 10),
                'name': section_data.get('name') or _('OJE Section'),
                'section_kind': section_data.get('section_kind') or 'legacy',
                'scope': section_data.get('scope') or template_scope,
                'rating_mode': section_data.get('rating_mode') or 'legacy_generic',
                'objective_text': section_data.get('objective_text') or False,
                'hint_html': section_data.get('hint_html') or False,
                'behavior_html': section_data.get('behavior_html') or False,
                'is_active': section_data.get('is_active', True),
            })

            for line_data in section_data.get('lines', []):
                line_vals.append({
                    'evaluation_id': evaluation.id,
                    'section_id': eval_section.id,
                    'template_line_id': line_data.get('source_question_id') or False,
                    'sequence': line_data.get('sequence', 10),
                    'name': line_data.get('name') or line_data.get('question_text') or _('OJE Line'),
                    'question_text': line_data.get('question_text') or line_data.get('name') or False,
                    'line_kind': line_data.get('line_kind') or 'legacy',
                    'scope': line_data.get('scope') or template_scope,
                    'rating_mode': line_data.get('rating_mode') or 'legacy_generic',
                    'is_required': line_data.get('is_required', True),
                    'is_active': line_data.get('is_active', True),
                    'field_type': line_data.get('field_type') or 'text',
                    'text_max_score': line_data.get('text_max_score', 0.0),
                    'checkbox_score': line_data.get('checkbox_score', 0.0),
                })

        if line_vals:
            self.env['x_psm_hr_applicant_oje_evaluation_line'].create(line_vals)

    def _ensure_oje_evaluation(self, evaluator_user=None):
        self.ensure_one()

        if not self.job_id:
            raise exceptions.UserError(_("Ứng viên chưa có Job Position."))

        evaluator = evaluator_user or self.oje_evaluator_user_id or self.env.user

        template_scope, template_version, config_signature, snapshot_sections = self._get_oje_snapshot_source()

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
                    or evaluation.template_version != template_version
                    or (evaluation.x_psm_config_signature or '') != (config_signature or '')
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
                        'x_psm_config_signature': config_signature or False,
                    })
                    self._populate_oje_evaluation_snapshot(evaluation, template_scope, snapshot_sections)

            return evaluation

        evaluation = self.env['x_psm_hr_applicant_oje_evaluation'].create({
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
            'x_psm_config_signature': config_signature or False,
        })
        self._populate_oje_evaluation_snapshot(evaluation, template_scope, snapshot_sections)

        self.write({'oje_evaluation_id': evaluation.id, 'oje_evaluator_user_id': evaluator.id})
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
            view = self.env.ref('M02_P0204.hr_applicant_oje_evaluation_view_form')
        else:
            view = self.env.ref('M02_P0204.hr_applicant_oje_evaluation_view_form_edit')

        return {
            'type': 'ir.actions.act_window',
            'name': _('Pass OJE'),
            'res_model': 'x_psm_hr_applicant_oje_evaluation',
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

    oje_management_overall_rating = fields.Float(
        related="oje_evaluation_id.management_overall_rating",
        string="Overall Rating",
        store=True,
        digits=(16, 2),
    )

    oje_fail_reason = fields.Text(
        string="Lý do không đạt OJE",
        copy=False,
    )

    # ==================== SURVEY STAT BUTTONS ====================

    survey_display_text = fields.Char(compute="_compute_survey_display")
    survey_display_result = fields.Char(compute="_compute_survey_display")
    interview_display_text = fields.Char(compute="_compute_interview_display")
    interview_display_result = fields.Char(compute="_compute_interview_display")
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
                    rec.oje_display_text = f"Overall {(rec.oje_management_overall_rating or 0.0):.2f}/5 {success}"
                else:
                    score = int(rec.oje_total_score)
                    rec.oje_display_text = f"{score}/{int(rec.oje_pass_score_snapshot)} {success}"
            else:
                rec.oje_display_text = "N/A"

    def _compute_interview_display(self):
        for rec in self:
            rec.interview_display_result = "Đánh giá Interview"
            if not rec.interview_evaluation_id:
                rec.interview_display_text = "Chưa có"
                continue

            state = rec.interview_evaluation_state
            if state == "new":
                rec.interview_display_text = "Chưa làm"
            elif state == "in_progress":
                rec.interview_display_text = "Đang làm"
            elif state == "done":
                success = "✓" if rec.interview_result == 'pass' else "✗"
                rec.interview_display_text = f"{rec.interview_final_score or 0:.2f}/5 {success}"
            else:
                rec.interview_display_text = "N/A"

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
            "res_model": "x_psm_hr_applicant_oje_evaluation",
            "res_id": self.oje_evaluation_id.id,
            "view_mode": "form",
            "target": "current",
        }

    def action_open_interview_results(self):
        self.ensure_one()
        if not self.interview_evaluation_id:
            return False
        return {
            'type': 'ir.actions.act_url',
            'name': 'Kết quả Đánh giá Interview',
            'url': f'/recruitment/interview/internal/{self.interview_evaluation_id.id}',
            'target': 'new',
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
            default_stage = self.env["hr.recruitment.stage"].search(
                self._x_psm_stage_scope_domain(stage_type=stage_type) + [("fold", "=", False)],
                order="sequence asc",
                limit=1,
            )
            if not default_stage:
                default_stage = self.env["hr.recruitment.stage"].search(
                    [
                        '|',
                        ('job_ids', '=', False),
                        ('job_ids', '=', self.job_id.id),
                        ('fold', '=', False),
                    ],
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
            
            schedule = self.env["x_psm_interview_schedule"].search([
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
            return self.env["x_psm_interview_schedule"]

        today = fields.Date.today()
        monday = today - timedelta(days=today.weekday())
        Schedule = self.env["x_psm_interview_schedule"].sudo()

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

    # Website Custom Form Fields
    x_birthday = fields.Date(string="Ngày sinh")
    x_current_job = fields.Char(string="Công việc hiện tại")
    x_portrait_image = fields.Binary(string="Ảnh chân dung")
    x_gender = fields.Selection([
        ('male', 'Nam'),
        ('female', 'Nữ'),
        ('not_display', 'Không hiển thị')
    ], string="Giới tính")
    x_id_document_type = fields.Selection([
        ('citizen_id', 'CCCD'),
        ('passport', 'Hộ chiếu'),
    ], string="Loại giấy tờ tùy thân", default='citizen_id')
    x_id_number = fields.Char(string="Số giấy tờ tùy thân")
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
    x_id_issue_date = fields.Date(string="Ngày cấp giấy tờ tùy thân")
    x_id_issue_place = fields.Char(string="Nơi cấp giấy tờ tùy thân")
    x_permanent_address = fields.Char(string="Địa chỉ thường trú")
    x_hometown = fields.Char(string="Nguyên quán")
    x_years_experience = fields.Integer(string="Số năm kinh nghiệm")
    x_height = fields.Integer(string="Chiều cao (cm)")
    x_weight = fields.Integer(string="Cân nặng (kg)")
    x_nationality = fields.Char(string="Quốc tịch")

    def _get_auto_pre_interview_survey(self, job):
        """Tự chọn survey tiền phỏng vấn (biểu mẫu ứng tuyển) cho ứng viên."""
        self.ensure_one()
        Survey = self.env["survey.survey"].sudo()

        # ƯU TIÊN: Survey đã cấu hình trực tiếp trên Job Position (core Odoo)
        if (
            job
            and "survey_id" in job._fields
            and job.survey_id
            and not job.survey_id.x_psm_0204_is_runtime_isolated_copy
        ):
            return job.survey_id

        # ƯU TIÊN: Survey biểu mẫu ứng tuyển chung đã seed trong module.
        survey = self.env.ref("M02_P0204.survey_fulltime", raise_if_not_found=False)
        if survey and not survey.x_psm_0204_is_runtime_isolated_copy:
            return survey

        # Fallback cuối: lấy survey usage=pre_interview đầu tiên.
        survey = Survey.search(
            [
                ("x_psm_survey_usage", "=", "pre_interview"),
                ("x_psm_0204_is_runtime_isolated_copy", "=", False),
            ],
            order="id asc",
            limit=1,
        )
        if survey:
            return survey

        return False

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

            # Snapshot Interview Evaluator (Store + Management)
            if (
                not vals.get("interview_evaluator_user_id")
                and job.recruitment_type == 'store'
                and job.position_level == 'management'
                and job.interview_evaluator_user_id
            ):
                vals["interview_evaluator_user_id"] = job.interview_evaluator_user_id.id

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
            fallback_xml_id="M02_P0204.email_applicant_survey_invite"
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
        1. Recruitment Stage template (stage.template_id)
        2. Event fallback XML ID (explicit fallback_xml_id or mapped from event_code)
        """
        self.ensure_one()

        # 1. Stage template from standard hr.recruitment.stage
        if resolve_stage_id:
            stage = self.env['hr.recruitment.stage'].browse(resolve_stage_id)
            if stage.exists() and stage.template_id:
                return stage.template_id

        # 2. Event fallback
        event_xmlid_map = {
            "survey_invite": "M02_P0204.email_survey_invitation",
            "interview_invitation": "M02_P0204.email_interview_invitation",
            "interview_slot_confirmed": "M02_P0204.email_interview_slot_confirmed",
            "reject": "M02_P0204.email_rejection",
            "oje_reject": "M02_P0204.email_oje_rejection",
            "hired": "M02_P0204.email_congratulations",
            "hired_part_time": "M02_P0204.email_congratulations_part_time",
        }
        xml_id = fallback_xml_id or event_xmlid_map.get(event_code)
        if xml_id:
            return self.env.ref(xml_id, raise_if_not_found=False)

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
        Returns: 'staff' | 'management' | 'office' | False
        """
        ctx = self.env.context

        # 1. Explicit stage filter (set by action_open_applicants)
        target = ctx.get("default_stage_filter_type")
        if target in ('office', 'staff', 'management'):
            return target

        target = self._x_psm_normalize_stage_type(
            recruitment_type=ctx.get("default_recruitment_type"),
            position_level=ctx.get("default_position_level"),
        )
        if target:
            return target

        # 2. From domain — position_level first, then recruitment_type
        if domain:
            for leaf in domain:
                if isinstance(leaf, (list, tuple)) and len(leaf) == 3:
                    if leaf[0] == "position_level" and leaf[1] == "=":
                        target = self._x_psm_normalize_stage_type(position_level=leaf[2])
                        if target:
                            return target
            for leaf in domain:
                if isinstance(leaf, (list, tuple)) and len(leaf) == 3:
                    if leaf[0] == "recruitment_type" and leaf[1] == "=":
                        target = self._x_psm_normalize_stage_type(recruitment_type=leaf[2])
                        if target:
                            return target

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
    def _resolve_stage_scope_job_id(self, domain=None):
        """Resolve job_id used to scope stage set in kanban/read_group."""
        ctx = self.env.context
        job_id = ctx.get("default_job_id")
        if job_id:
            return job_id

        if domain:
            for leaf in domain:
                if not isinstance(leaf, (list, tuple)) or len(leaf) != 3:
                    continue
                if leaf[0] != 'job_id':
                    continue
                if leaf[1] == '=':
                    return leaf[2]
                if leaf[1] == 'in' and isinstance(leaf[2], (list, tuple)) and leaf[2]:
                    return leaf[2][0]
        return False

    @api.model
    def _read_group_stage_ids(self, stages, domain, order=None):
        """Filter kanban stages by the resolved pipeline type.
        Never returns all stages as a fallback.
        """
        target_type = self._resolve_stage_filter_type(domain)
        scope_job_id = self._resolve_stage_scope_job_id(domain)

        if not target_type:
            store_scope = self.env.context.get("default_recruitment_type") == 'store'
            if not store_scope and domain:
                for leaf in domain:
                    if (
                        isinstance(leaf, (list, tuple))
                        and len(leaf) == 3
                        and leaf[0] == 'recruitment_type'
                        and leaf[1] == '='
                        and leaf[2] == 'store'
                    ):
                        store_scope = True
                        break
            if not store_scope and scope_job_id:
                job = self.env['hr.job'].browse(scope_job_id)
                if job.exists() and job.recruitment_type == 'store' and not job.position_level:
                    store_scope = True
            if store_scope:
                return stages.browse()

        search_domain = []

        if scope_job_id:
            search_domain.extend([
                '|',
                ('job_ids', '=', False),
                ('job_ids', '=', scope_job_id),
            ])

        if target_type:
            search_domain.append(('recruitment_type', '=', target_type))
            if target_type == 'office':
                search_domain.extend([
                    '|',
                    ('office_pipeline_visible', '=', True),
                    ('recruitment_type', '!=', 'office'),
                ])

        if not search_domain:
            search_domain = [('job_ids', '=', False)]

        return stages.search(search_domain, order=order or stages._order)



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
            fallback_xml_id="M02_P0204.email_interview_invitation"
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
            # Đánh dấu survey runtime riêng theo applicant và tách khỏi master/custom của Job.
            'x_psm_0204_is_runtime_isolated_copy': True,
            'x_psm_default_template_for': False,
            'x_psm_0204_owner_job_id': False,
            'x_psm_0204_owner_department_id': False,
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
        return self._x_psm_is_interview_stage_record(self.stage_id)

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
            fallback_xml_id="M02_P0204.email_interview_slot_confirmed"
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
            "M02_P0204.email_interview_slot_full",
            raise_if_not_found=False,
        )
        if template and self.email_from:
            self._send_mail_async(template, self.id)

    def action_accept_interview(self):
        """Store+Management mở phiếu Interview; các scope khác giữ hành vi cũ chuyển Interview -> OJE."""
        self.ensure_one()

        if self.recruitment_type == 'store' and self.position_level == 'management':
            return self.action_open_backend_interview_evaluation()

        oje_stage = self._x_psm_resolve_stage('OJE', ilike=True)
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
            table_name = self.interview_schedule_id._table
            self.env.cr.execute(
                f'SELECT id FROM "{table_name}" WHERE id = %s FOR UPDATE',
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
                stage = rec._x_psm_resolve_stage('Under Review', ilike=True)
                if not stage:
                    _logger.warning("[APPROVE_DOCS] Specific stage 'Under Review' not found for applicant %s.", rec.id)
                
                _logger.info("[APPROVE_DOCS] Store mode - final stage result: %s", stage.id if stage else "NOT FOUND")
                if stage:
                    rec.stage_id = stage.id
                super(HrApplicant, rec).action_approve_documents()
            else:
                stage = rec._x_psm_resolve_stage('Contract Signed', ilike=True)
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

            stage = rec._x_psm_resolve_stage('Reject', ilike=True)

            vals = {
                'x_psm_0205_document_approval_status': 'refused',
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

        # 0205 can run without the legacy document status field.
        if 'x_psm_0205_document_approval_status' in vals and 'x_psm_0205_document_approval_status' not in self._fields:
            vals = dict(vals)
            vals.pop('x_psm_0205_document_approval_status', None)

        # Lưu lại stage cũ trước khi write để check điều kiện gửi email Reject
        old_stages = {rec.id: rec.stage_id.id for rec in self}
        
        result = super().write(vals)
        # Khi HR đánh giá (priority/stars) tại stage Interview
        if 'priority' in vals and vals['priority'] != '0':
            for rec in self:
                if (
                    rec.recruitment_type == 'store'
                    and rec.stage_id
                    and rec._is_interview_stage()
                ):
                    if rec.position_level == 'staff':
                        # Staff: Interview & OJE → Hired + email chúc mừng
                        target_stage = rec._x_psm_resolve_stage('Hired', use_hired_flag=True)
                        if target_stage:
                            rec.stage_id = target_stage.id
                    elif rec.position_level == 'management':
                        # Management: Interview → OJE
                        target_stage = rec._x_psm_resolve_stage('OJE', ilike=True)
                        if target_stage:
                            rec.stage_id = target_stage.id
        # Bắt sự kiện chuyển stage thành 'Reject' hoặc tương tự để gửi email báo rớt
        if 'stage_id' in vals:
            for rec in self:
                # Kiểm tra xem trước đó ứng viên chưa ở stage Reject
                old_stage_id = old_stages.get(rec.id)
                if old_stage_id != vals['stage_id']:
                    new_stage = self.env['hr.recruitment.stage'].browse(vals['stage_id'])
                    
                    # === KIỂM TRA EMAIL CONFIGURE THEO STAGE TEMPLATE ===
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
        part_time_contract = self.env.ref("hr.contract_type_part_time", raise_if_not_found=False)
        job_is_part_time = bool(
            applicant.job_id
            and "contract_type_id" in applicant.job_id._fields
            and applicant.job_id.contract_type_id
            and part_time_contract
            and applicant.job_id.contract_type_id.id == part_time_contract.id
        )
        is_staff_part_time = bool(applicant.position_level == "staff" and job_is_part_time)

        event_code = "hired_part_time" if is_staff_part_time else "hired"
        fallback_xml_id = (
            "M02_P0204.email_congratulations_part_time"
            if is_staff_part_time
            else "M02_P0204.email_congratulations"
        )

        template = applicant._get_email_template_resolution(
            event_code=event_code,
            fallback_xml_id=fallback_xml_id,
        )
        if template and applicant.email_from:
            try:
                self._send_mail_async(template, applicant.id)
                _logger.info(
                    "[EVAL_AUTO] Queued async congrats email (%s) to %s",
                    event_code,
                    applicant.email_from,
                )
            except Exception as e:
                _logger.error("[EVAL_AUTO] Failed to send congrats to %s: %s", applicant.email_from, str(e))

    def _send_rejection_email(self, applicant):
        """Gửi email thông báo rớt cho ứng viên"""
        template = applicant._get_email_template_resolution(
            event_code="reject",
            fallback_xml_id="M02_P0204.email_rejection"
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
            fallback_xml_id="M02_P0204.email_oje_rejection"
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
            if not rec.stage_id:
                continue

            oje_stage = rec._x_psm_resolve_stage('OJE', ilike=True)
            offer_stage = rec._x_psm_resolve_stage('Offer')

            if oje_stage and rec.stage_id.id == oje_stage.id:
                target_name = 'Offer'
            elif offer_stage and rec.stage_id.id == offer_stage.id:
                target_name = 'Hired'
            elif (rec.stage_id.name or '') == 'OJE':
                # Legacy fallback when XMLID mapping is unavailable in old databases.
                target_name = 'Offer'
            elif (rec.stage_id.name or '') == 'Offer':
                # Legacy fallback when XMLID mapping is unavailable in old databases.
                target_name = 'Hired'
            else:
                continue

            target_stage = rec._x_psm_resolve_stage(target_name, use_hired_flag=(target_name == 'Hired'))
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
            stage = rec._x_psm_resolve_stage('Reject', ilike=True)
            if stage:
                rec.stage_id = stage.id
            rec.write({
                'x_psm_0205_document_approval_status': 'refused',
                'reject_reason': reason.strip() if reason else False,
            })
            rec.message_post(body=f"Từ chối ứng viên. Lý do: {reason}")

    def action_move_next_stage(self):
        """Chuyển sang giai đoạn tiếp theo"""
        self.ensure_one()
        if not self.stage_id:
            raise exceptions.UserError("Không xác định được giai đoạn hiện tại!")

        stage_type = self._get_pipeline_stage_type()
        domain = self._x_psm_stage_scope_domain(stage_type=stage_type) + [
            ("sequence", ">", self.stage_id.sequence),
            ("fold", "=", False),
        ]

        next_stage = self.env["hr.recruitment.stage"].search(
            domain, order="sequence asc", limit=1
        )

        if not next_stage and self.job_id:
            next_stage = self.env["hr.recruitment.stage"].search(
                [
                    '|',
                    ('job_ids', '=', False),
                    ('job_ids', '=', self.job_id.id),
                    ("sequence", ">", self.stage_id.sequence),
                    ("fold", "=", False),
                ],
                order="sequence asc",
                limit=1,
            )

        if next_stage:
            self.stage_id = next_stage
        else:
            raise exceptions.UserError(
                "Đã ở giai đoạn cuối cùng, không thể chuyển tiếp!"
            )

    # ==================== SURVEY UNDER REVIEW ACTIONS ====================

    def action_approve_survey_review(self):
        """HR xem xét xong → tiếp tục pipeline sau Survey theo flow hiện tại."""
        for rec in self:
            # Route giống survey pass: staff → Interview & OJE, management → Interview
            if rec.recruitment_type == 'store' and rec.position_level == 'staff':
                target_name = "Interview & OJE"
            elif rec.recruitment_type == 'store' and rec.position_level == 'management':
                target_name = "Interview"
            else:
                target_name = "Screening"
            target_stage = rec._x_psm_resolve_stage(target_name)
            if target_stage:
                rec.stage_id = target_stage
                rec.survey_under_review_date = False

                # Đồng bộ luồng với case pass biểu mẫu: khi về stage Interview thì auto-book lịch.
                if rec.recruitment_type == 'store' and rec._x_psm_is_interview_stage_record(target_stage):
                    if not rec.interview_schedule_id and rec.department_id:
                        fallback_schedule = rec._find_department_interview_schedule(rec.department_id)
                        if fallback_schedule:
                            rec.interview_schedule_id = fallback_schedule.id

                    try:
                        booking_result = rec.action_auto_book_interview_from_survey()
                        _logger.info(
                            "[SURVEY_REVIEW] Auto-book after approve for applicant %s: %s",
                            rec.id,
                            booking_result,
                        )
                    except Exception as booking_err:
                        _logger.error(
                            "[SURVEY_REVIEW] Auto-book failed after approve for applicant %s: %s",
                            rec.id,
                            booking_err,
                        )
            else:
                _logger.warning("[SURVEY_REVIEW] Không tìm thấy stage '%s' cho applicant %s", target_name, rec.id)

    def action_move_to_store_interview(self):
        """Chuyển ứng viên store sang Interview & OJE (staff) hoặc Interview (management).
        Chỉ có tác dụng với store jobs. Được gọi bằng nút trên form header.
        """
        for rec in self:
            if rec.recruitment_type != 'store':
                continue
            if rec.position_level == 'staff':
                target_name = "Interview & OJE"
            else:
                target_name = "Interview"

            target_stage = rec._x_psm_resolve_stage(target_name)
            if target_stage:
                rec.stage_id = target_stage
                _logger.info("[STORE_INTERVIEW] %s → '%s'", rec.partner_name, target_stage.name)
            else:
                raise exceptions.UserError(f"Không tìm thấy stage '{target_name}' cho applicant hiện tại!")


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
            stage = rec._x_psm_resolve_stage("Reject", ilike=True)
            if stage:
                rec.stage_id = stage
            rec.write({
                'survey_under_review_date': False,
                'x_psm_0205_document_approval_status': 'refused',
                'reject_reason': reason.strip() if reason else False,
            })
            rec.message_post(body=f"Từ chối Survey. Lý do: {reason}")

    # ==================== INTERVIEW EVALUATION ACTIONS ====================

    def _build_interview_fail_reason(self, evaluation):
        self.ensure_one()
        return _("Final Score %s < 3.") % (f"{evaluation.final_score or 0.0:.2f}")

    def _find_interview_target_stage(self, stage_name, ilike=False):
        self.ensure_one()
        return self._x_psm_resolve_stage(stage_name, ilike=ilike)

    def action_apply_interview_evaluation_result(self):
        self.ensure_one()
        evaluation = self.interview_evaluation_id
        if not evaluation or evaluation.state != 'done':
            raise exceptions.UserError("Phiếu đánh giá Interview chưa hoàn thành!")

        if evaluation.stage_applied:
            return True

        if evaluation.result == 'pass':
            target_stage = self._find_interview_target_stage('OJE')
            if not target_stage:
                target_stage = self._find_interview_target_stage('OJE', ilike=True)

            if not target_stage:
                raise exceptions.UserError("Không tìm thấy Stage 'OJE'!")

            self.write({
                'stage_id': target_stage.id,
                'interview_fail_reason': False,
            })
        else:
            target_stage = self._find_interview_target_stage('Reject', ilike=True)
            if not target_stage:
                raise exceptions.UserError("Không tìm thấy Stage 'Reject'!")

            self.write({
                'stage_id': target_stage.id,
                'x_psm_0205_document_approval_status': 'refused',
                'interview_fail_reason': self._build_interview_fail_reason(evaluation),
            })

        evaluation.sudo().write({'stage_applied': True})
        return True

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
        return _("Overall rating dưới ngưỡng đạt (>= 3): %.2f/5.") % (evaluation.management_overall_rating or 0.0)

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
                max_opt_score = max(line.template_line_id.suggested_answer_ids.mapped('answer_score'), default=0)
                if line.selected_option_score < max_opt_score:
                    selected_name = line.selected_option_id.value if line.selected_option_id else 'N/A'
                    fail_reasons.append(
                        f"- {line.name}: {selected_name} ({line.selected_option_score}/{max_opt_score} điểm)"
                    )
        return "\n".join(fail_reasons) if fail_reasons else _("Không đáp ứng tiêu chuẩn OJE chung.")

    def _find_oje_target_stage(self, stage_name, use_hired_flag=False, ilike=False):
        self.ensure_one()
        return self._x_psm_resolve_stage(stage_name, ilike=ilike, use_hired_flag=use_hired_flag)

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
                'x_psm_0205_document_approval_status': 'refused',
                'oje_fail_reason': fail_reason,
            })

            self._send_oje_rejection_email(self)

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
            stage = rec._x_psm_resolve_stage("Reject", ilike=True)
            if stage:
                rec.stage_id = stage
            rec.survey_under_review_date = False
            if 'x_psm_0205_document_approval_status' in rec._fields:
                rec.x_psm_0205_document_approval_status = 'refused'
            _logger.info("[AUTO_REJECT] Auto-rejected applicant id=%d (%s)", rec.id, rec.partner_name)
