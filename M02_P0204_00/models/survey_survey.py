# -*- coding: utf-8 -*-
"""
Model: Survey Extension
Mô tả: Chuẩn hóa metadata survey theo Survey Usage
    và các cờ logic cho câu hỏi biểu mẫu ứng tuyển.
"""

import re
import unicodedata

from odoo import _, api, models, fields
from odoo.exceptions import UserError, ValidationError


class SurveySurvey(models.Model):
    """Extend Survey với metadata 0204 cho master/custom/runtime."""
    _inherit = 'survey.survey'

    x_psm_survey_usage = fields.Selection(
        [
            ("pre_interview", "Pre-Interview"),
            ("interview", "Interview Evaluation"),
            ("oje", "OJE Evaluation"),
        ],
        string="Survey Usage",
        help="Phân loại survey để module 0204 đọc đúng luồng nghiệp vụ.",
    )

    x_psm_oje_scope = fields.Selection(
        [
            ("store_staff", "Store Staff"),
            ("store_management", "Store Management"),
        ],
        string="OJE Scope",
        help="Scope dùng cho OJE runtime khi survey usage là OJE.",
    )

    x_psm_0204_owner_job_id = fields.Many2one(
        "hr.job",
        oldname="owner_job_id",
        string="Owner Job",
        help="Survey custom thuộc Job nào. Để trống nếu là survey mặc định/chung.",
    )

    x_psm_0204_owner_department_id = fields.Many2one(
        "hr.department",
        oldname="owner_department_id",
        string="Owner Department",
        help="Phòng ban sở hữu survey custom. Để trống nếu là survey master mặc định/chung.",
    )

    x_psm_0204_is_runtime_isolated_copy = fields.Boolean(
        string="Runtime Isolated Copy",
        default=False,
        help=(
            "Đánh dấu survey copy runtime riêng theo applicant; "
            "không dùng cho cấu hình template/master/custom của Job."
        ),
    )

    x_psm_default_template_for = fields.Selection(
        [
            ("pre_interview", "Pre-Interview"),
            ("interview", "Interview"),
            ("oje_store_staff", "OJE Store Staff"),
            ("oje_store_management", "OJE Store Management"),
        ],
        string="Master Template For (Legacy)",
        help=(
            "Đánh dấu survey này là mẫu mặc định cho đúng luồng nghiệp vụ. "
            "Để trống nghĩa là survey không được dùng như default template."
        ),
    )

    x_psm_0204_default_template_for = fields.Selection(
        oldname="default_template_for",
        related="x_psm_default_template_for",
        string="Master Template For",
        readonly=False,
        store=True,
    )

    def _x_psm_is_master_template(self):
        self.ensure_one()
        return bool(
            not self.x_psm_0204_owner_job_id
            and not self.x_psm_0204_owner_department_id
            and (self.x_psm_0204_default_template_for or self.x_psm_default_template_for)
        )

    @api.model
    def _x_psm_can_manage_master_templates(self):
        context = self.env.context
        if (
            self.env.su
            or context.get("install_mode")
            or context.get("module")
            or context.get("x_psm_allow_master_template_edit")
        ):
            return True

        user = self.env.user
        return bool(
            user.has_group("survey.group_survey_user")
            or user.has_group("survey.group_survey_manager")
            or user.has_group("hr_recruitment.group_hr_recruitment_manager")
            or user.has_group("M02_P0204_00.group_gdh_ops_0204_mgr")
        )

    def _x_psm_sync_missing_owner_department(self):
        if self.env.context.get("x_psm_skip_owner_department_sync"):
            return

        for survey in self.filtered(
            lambda rec: rec.x_psm_0204_owner_job_id
            and not rec.x_psm_0204_owner_department_id
            and rec.x_psm_0204_owner_job_id.department_id
        ):
            survey.sudo().with_context(x_psm_skip_owner_department_sync=True).write(
                {
                    "x_psm_0204_owner_department_id": survey.x_psm_0204_owner_job_id.department_id.id,
                }
            )

    @api.model
    def _x_psm_get_default_template_usage_scope_map(self):
        return {
            "pre_interview": ("pre_interview", False),
            "interview": ("interview", False),
            "oje_store_staff": ("oje", "store_staff"),
            "oje_store_management": ("oje", "store_management"),
        }

    @api.model
    def _x_psm_normalize_usage_vals(self, vals):
        normalized_vals = dict(vals)

        # Legacy removed flags are intentionally ignored.
        normalized_vals.pop("is_pre_interview", None)
        normalized_vals.pop("is_oje_evaluation", None)
        normalized_vals.pop("x_psm_0204_is_pre_interview", None)
        normalized_vals.pop("x_psm_0204_is_oje_evaluation", None)

        legacy_key_map = {
            "owner_job_id": "x_psm_0204_owner_job_id",
            "owner_department_id": "x_psm_0204_owner_department_id",
            "default_template_for": "x_psm_0204_default_template_for",
        }
        for old_key, new_key in legacy_key_map.items():
            if old_key in normalized_vals and new_key not in normalized_vals:
                normalized_vals[new_key] = normalized_vals.pop(old_key)

        if normalized_vals.get("x_psm_0204_is_runtime_isolated_copy"):
            normalized_vals["x_psm_default_template_for"] = False
            normalized_vals["x_psm_0204_owner_job_id"] = False
            normalized_vals["x_psm_0204_owner_department_id"] = False

        owner_job_id = normalized_vals.get("x_psm_0204_owner_job_id")
        if owner_job_id:
            if not normalized_vals.get("x_psm_0204_owner_department_id"):
                owner_job = self.env["hr.job"].sudo().browse(owner_job_id)
                normalized_vals["x_psm_0204_owner_department_id"] = owner_job.department_id.id or False

            # Custom survey không được mang cờ default template.
            normalized_vals["x_psm_default_template_for"] = False
        elif "x_psm_0204_owner_job_id" in normalized_vals:
            normalized_vals["x_psm_0204_owner_department_id"] = False

        return normalized_vals

    @api.model_create_multi
    def create(self, vals_list):
        normalized_vals_list = [self._x_psm_normalize_usage_vals(vals) for vals in vals_list]
        if not self._x_psm_can_manage_master_templates():
            for vals in normalized_vals_list:
                if (
                    not vals.get("x_psm_0204_owner_job_id")
                    and not vals.get("x_psm_0204_owner_department_id")
                    and vals.get("x_psm_default_template_for")
                ):
                    raise UserError(_("Bạn không có quyền tạo Master Survey."))

        records = super().create(normalized_vals_list)
        records._x_psm_sync_missing_owner_department()
        return records

    def write(self, vals):
        normalized_vals = self._x_psm_normalize_usage_vals(vals)
        if not self._x_psm_can_manage_master_templates():
            master_surveys = self.filtered(lambda rec: rec._x_psm_is_master_template())
            if master_surveys:
                raise UserError(_("Bạn không có quyền chỉnh sửa Master Survey."))

        result = super().write(normalized_vals)
        self._x_psm_sync_missing_owner_department()
        return result

    def unlink(self):
        if not self._x_psm_can_manage_master_templates():
            master_surveys = self.filtered(lambda rec: rec._x_psm_is_master_template())
            if master_surveys:
                raise UserError(_("Bạn không có quyền xóa Master Survey."))
        return super().unlink()

    @api.constrains("x_psm_0204_default_template_for", "x_psm_survey_usage", "x_psm_oje_scope")
    def _check_x_psm_default_template_usage_scope(self):
        default_map = self._x_psm_get_default_template_usage_scope_map()
        for rec in self:
            default_for = rec.x_psm_0204_default_template_for or rec.x_psm_default_template_for
            if not default_for:
                continue

            expected_usage, expected_scope = default_map.get(default_for, (False, False))
            if expected_usage and rec.x_psm_survey_usage != expected_usage:
                raise ValidationError(
                    _(
                        "Master Template For '%(default_for)s' yêu cầu Survey Usage = '%(expected_usage)s'."
                    )
                    % {
                        "default_for": dict(rec._fields["x_psm_0204_default_template_for"].selection).get(
                            default_for,
                            default_for,
                        ),
                        "expected_usage": expected_usage,
                    }
                )

            if expected_scope and rec.x_psm_oje_scope != expected_scope:
                raise ValidationError(
                    _(
                        "Master Template For '%(default_for)s' yêu cầu OJE Scope = '%(expected_scope)s'."
                    )
                    % {
                        "default_for": dict(rec._fields["x_psm_0204_default_template_for"].selection).get(
                            default_for,
                            default_for,
                        ),
                        "expected_scope": expected_scope,
                    }
                )

    @api.constrains("x_psm_0204_default_template_for", "x_psm_0204_owner_job_id", "x_psm_0204_owner_department_id")
    def _check_x_psm_default_template_owner_job(self):
        for rec in self.filtered(
            lambda survey: (survey.x_psm_0204_default_template_for or survey.x_psm_default_template_for)
            and (survey.x_psm_0204_owner_job_id or survey.x_psm_0204_owner_department_id)
        ):
            raise ValidationError(
                _(
                    "Survey đã gắn Owner Job/Owner Department không được đánh dấu Master Template For. "
                    "Hãy để trống cả Owner Job và Owner Department cho survey master mặc định/chung."
                )
            )

    @api.constrains("x_psm_0204_default_template_for", "active", "x_psm_0204_owner_job_id", "x_psm_0204_owner_department_id")
    def _check_x_psm_unique_active_default_template(self):
        for rec in self.filtered(lambda survey: survey.active and (survey.x_psm_0204_default_template_for or survey.x_psm_default_template_for)):
            selector = rec.x_psm_0204_default_template_for or rec.x_psm_default_template_for
            duplicate = self.sudo().search(
                [
                    ("id", "!=", rec.id),
                    ("active", "=", True),
                    ("x_psm_0204_owner_job_id", "=", False),
                    ("x_psm_0204_owner_department_id", "=", False),
                    "|",
                    ("x_psm_0204_default_template_for", "=", selector),
                    ("x_psm_default_template_for", "=", selector),
                ],
                limit=1,
            )
            if duplicate:
                raise ValidationError(
                    _(
                        "Mỗi loại default chỉ được có tối đa 1 survey active. "
                        "'%(_current)s' đang xung đột với '%(_duplicate)s'."
                    )
                    % {
                        "_current": rec.title,
                        "_duplicate": duplicate.title,
                    }
                )

    @api.constrains("x_psm_0204_owner_job_id", "x_psm_0204_owner_department_id")
    def _check_x_psm_owner_pair(self):
        for rec in self.filtered(lambda survey: survey.x_psm_0204_owner_department_id and not survey.x_psm_0204_owner_job_id):
            raise ValidationError(
                _("Owner Department chỉ hợp lệ khi đã gắn Owner Job.")
            )

    @api.constrains(
        "active",
        "x_psm_0204_owner_job_id",
        "x_psm_0204_owner_department_id",
        "x_psm_0204_is_runtime_isolated_copy",
        "x_psm_survey_usage",
        "x_psm_oje_scope",
    )
    def _check_x_psm_unique_active_custom_survey(self):
        for rec in self.filtered(
            lambda survey: survey.active
            and survey.x_psm_0204_owner_job_id
            and not survey.x_psm_0204_is_runtime_isolated_copy
        ):
            owner_department = rec.x_psm_0204_owner_department_id or rec.x_psm_0204_owner_job_id.department_id
            domain = [
                ("id", "!=", rec.id),
                ("active", "=", True),
                ("x_psm_0204_is_runtime_isolated_copy", "=", False),
                ("x_psm_0204_owner_job_id", "=", rec.x_psm_0204_owner_job_id.id),
                ("x_psm_0204_owner_department_id", "=", owner_department.id if owner_department else False),
                ("x_psm_survey_usage", "=", rec.x_psm_survey_usage),
            ]
            if rec.x_psm_survey_usage == "oje":
                domain.append(("x_psm_oje_scope", "=", rec.x_psm_oje_scope or False))

            duplicate = self.sudo().search(domain, limit=1)
            if duplicate:
                raise ValidationError(
                    _(
                        "Đã tồn tại survey custom active cho tổ hợp Job/Phòng ban/Loại survey này: '%(duplicate)s'."
                    )
                    % {"duplicate": duplicate.title}
                )


class SurveyQuestion(models.Model):
    """Extend câu hỏi để đánh dấu câu 'không thể sai'"""
    _inherit = 'survey.question'

    x_psm_0204_is_mandatory_correct = fields.Boolean(
        oldname="is_mandatory_correct",
        string="Phải đúng",
        default=False,
        help=(
            "Nếu câu này được đánh dấu và ứng viên trả lời SAI — "
            "hệ thống sẽ đánh dấu là không đạt tiêu chí bắt buộc "
            "(Store đưa vào Under Review, Office báo cảnh báo trên log)."
        )
    )

    x_psm_0204_is_reject_when_wrong = fields.Boolean(
        oldname="is_reject_when_wrong",
        string="Loại khi sai",
        default=False,
        help=(
            "Nếu tick, khi ứng viên trả lời sai câu này thì hồ sơ sẽ bị chuyển Reject ngay. "
            "Cờ này luôn đi cùng 'Phải đúng'."
        ),
    )

    x_psm_show_on_webform = fields.Boolean(
        string="Hiển thị trên form ứng tuyển",
        default=True,
        help=(
            "Bật: câu hỏi hiển thị trên trang ứng tuyển website. "
            "Tắt: câu hỏi không render trên form apply website."
        ),
    )

    x_psm_parent_survey_usage = fields.Selection(
        related="survey_id.x_psm_survey_usage",
        string="Survey Usage",
        readonly=True,
    )

    x_psm_oje_section_kind = fields.Selection(
        [
            ("auto", "Tự động"),
            ("staff_block", "Staff Block"),
            ("management_dimension", "Management Dimension"),
            ("management_xfactor", "Management X-Factor"),
        ],
        string="PSM OJE Section Kind",
        default="auto",
        help="Dùng cho record page để map section OJE runtime.",
    )

    x_psm_oje_line_kind = fields.Selection(
        [
            ("auto", "Tự động"),
            ("staff_question", "Staff Question"),
            ("management_task", "Management Task"),
            ("management_xfactor", "Management X-Factor"),
        ],
        string="PSM OJE Line Kind",
        default="auto",
        help="Dùng cho câu hỏi để map line kind OJE runtime.",
    )

    x_psm_interview_line_kind = fields.Selection(
        [
            ("auto", "Tự động"),
            ("subheader", "Sub Header"),
            ("question", "Question"),
            ("skillset_child", "Skillset Child"),
        ],
        string="PSM Interview Line Kind",
        default="auto",
        help="Dùng cho câu hỏi Interview Evaluation để render theo layout metadata.",
    )

    x_psm_interview_group_label = fields.Char(
        string="PSM Interview Group Label",
        help="Nhãn nhóm bên trái khi line kind là Skillset Child (dùng cho rowspan).",
    )

    def init(self):
        super().init()
        # Keep old records visible after upgrade unless user explicitly turns them off.
        self._cr.execute(
            """
                UPDATE survey_question
                   SET x_psm_show_on_webform = TRUE
                 WHERE x_psm_show_on_webform IS NULL
            """
        )

    def _x_psm_normalize_plain_text(self, value):
        value = value or ""
        value = unicodedata.normalize("NFD", value)
        value = "".join(ch for ch in value if unicodedata.category(ch) != "Mn")
        value = value.lower()
        return re.sub(r"[^a-z0-9]+", " ", value).strip()

    def _x_psm_is_locked_application_core_question(self):
        self.ensure_one()
        if self.survey_id.x_psm_survey_usage != "pre_interview":
            return False

        normalized_title = self._x_psm_normalize_plain_text(self.title or self.question or "")
        lock_markers = [
            "ho va ten",
            "email",
            "cv",
            "ho so dinh kem",
        ]
        return any(marker in normalized_title for marker in lock_markers)

    def _x_psm_allow_locked_question_write(self):
        context = self.env.context
        return bool(
            context.get("install_mode")
            or context.get("module")
            or context.get("x_psm_allow_core_question_update")
        )

    def _x_psm_is_master_template_question(self):
        self.ensure_one()
        return bool(self.survey_id and self.survey_id._x_psm_is_master_template())

    @api.model
    def _x_psm_can_manage_master_questions(self):
        return self.env["survey.survey"]._x_psm_can_manage_master_templates()

    @api.model
    def _x_psm_normalize_question_flags_vals(self, vals):
        normalized_vals = dict(vals)

        if "is_mandatory_correct" in normalized_vals and "x_psm_0204_is_mandatory_correct" not in normalized_vals:
            normalized_vals["x_psm_0204_is_mandatory_correct"] = normalized_vals.pop("is_mandatory_correct")
        if "is_reject_when_wrong" in normalized_vals and "x_psm_0204_is_reject_when_wrong" not in normalized_vals:
            normalized_vals["x_psm_0204_is_reject_when_wrong"] = normalized_vals.pop("is_reject_when_wrong")

        if normalized_vals.get("x_psm_0204_is_reject_when_wrong"):
            normalized_vals["x_psm_0204_is_mandatory_correct"] = True
            normalized_vals.setdefault("constr_mandatory", True)

        if normalized_vals.get("x_psm_0204_is_mandatory_correct") is False:
            normalized_vals["x_psm_0204_is_reject_when_wrong"] = False

        return normalized_vals

    @api.model_create_multi
    def create(self, vals_list):
        normalized_vals_list = [self._x_psm_normalize_question_flags_vals(vals) for vals in vals_list]

        if not self._x_psm_can_manage_master_questions():
            survey_ids = [vals.get("survey_id") for vals in normalized_vals_list if vals.get("survey_id")]
            if survey_ids:
                master_surveys = self.env["survey.survey"].sudo().browse(survey_ids).filtered(
                    lambda survey: survey._x_psm_is_master_template()
                )
                if master_surveys:
                    raise UserError(_("Bạn không có quyền chỉnh sửa câu hỏi của Master Survey."))

        for vals in normalized_vals_list:
            vals.setdefault("x_psm_show_on_webform", True)
        return super().create(normalized_vals_list)

    def write(self, vals):
        if not self._x_psm_can_manage_master_questions():
            master_questions = self.filtered(lambda question: question._x_psm_is_master_template_question())
            if master_questions:
                raise UserError(_("Bạn không có quyền chỉnh sửa câu hỏi của Master Survey."))

        if not self._x_psm_allow_locked_question_write():
            locked_questions = self.filtered(lambda question: question._x_psm_is_locked_application_core_question())
            if locked_questions:
                raise UserError(
                    _(
                        "Không thể chỉnh sửa các câu hỏi lõi của biểu mẫu ứng tuyển (Họ và tên / Email / CV)."
                    )
                )

        normalized_vals = self._x_psm_normalize_question_flags_vals(vals)
        return super().write(normalized_vals)

    def unlink(self):
        if not self._x_psm_can_manage_master_questions():
            master_questions = self.filtered(lambda question: question._x_psm_is_master_template_question())
            if master_questions:
                raise UserError(_("Bạn không có quyền xóa câu hỏi của Master Survey."))

        if not self._x_psm_allow_locked_question_write():
            locked_questions = self.filtered(lambda question: question._x_psm_is_locked_application_core_question())
            if locked_questions:
                raise UserError(
                    _(
                        "Không thể xóa các câu hỏi lõi của biểu mẫu ứng tuyển (Họ và tên / Email / CV)."
                    )
                )

        return super().unlink()

    @api.onchange("x_psm_0204_is_reject_when_wrong")
    def _onchange_is_reject_when_wrong(self):
        if self.x_psm_0204_is_reject_when_wrong:
            self.x_psm_0204_is_mandatory_correct = True
            self.constr_mandatory = True

    @api.onchange("x_psm_0204_is_mandatory_correct")
    def _onchange_is_mandatory_correct(self):
        if not self.x_psm_0204_is_mandatory_correct:
            self.x_psm_0204_is_reject_when_wrong = False
