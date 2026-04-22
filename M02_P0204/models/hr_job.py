from odoo import api, exceptions, fields, models, _
import json
import logging
import re
import unicodedata

_logger = logging.getLogger(__name__)


class HrJob(models.Model):
    _inherit = "hr.job"
    _order = "recruitment_qty_updated_at desc nulls last, id desc"

    no_of_recruitment = fields.Integer(default=0)
    recruitment_qty_updated_at = fields.Datetime("Cap nhat so luong lan cuoi", copy=False)

    recruitment_type = fields.Selection(
        [
            ("store", "Store"),
            ("office", "Office"),
        ],
        string="Recruitment Type",
        help="Job scope determines which pipeline and surveys apply.",
        compute="_compute_recruitment_logic",
        store=True,
        readonly=False,
    )

    position_level = fields.Selection(
        [
            ("management", "Management"),
            ("staff", "Staff"),
        ],
        string="Level",
        help="Position level determines pipeline and survey templates.",
        compute="_compute_recruitment_logic",
        store=True,
        readonly=False,
    )

    auto_evaluate_survey = fields.Boolean(
        string="Tu Dong Danh Gia Survey",
        default=False,
    )

    survey_eval_mode = fields.Selection(
        [
            ("percentage", "Theo % diem"),
            ("correct_count", "Theo so cau dung"),
        ],
        string="Che do danh gia",
        default="percentage",
    )

    min_correct_answers = fields.Integer(
        string="So cau dung toi thieu",
        default=0,
        help="So cau tra loi dung toi thieu de ung vien duoc coi la dat (dung khi che do = Theo so cau dung)",
    )

    display_name_with_dept = fields.Char(
        string="Ten voi Phong ban",
        compute="_compute_display_name_with_dept",
        store=True,
    )

    x_psm_interview_survey_id = fields.Many2one(
        "survey.survey",
        string="Survey Interview",
        domain="[('x_psm_survey_usage', '=', 'interview'), ('x_psm_0204_is_runtime_isolated_copy', '=', False), '|', '&', ('x_psm_0204_owner_job_id', '=', False), ('x_psm_0204_owner_department_id', '=', False), '&', ('x_psm_0204_owner_job_id', '=', id), ('x_psm_0204_owner_department_id', '=', department_id)]",
        help="Survey dung lam template cau hoi Interview cho job nay.",
    )

    x_psm_oje_survey_id = fields.Many2one(
        "survey.survey",
        string="Survey OJE",
        domain="[('x_psm_survey_usage', '=', 'oje'), ('x_psm_0204_is_runtime_isolated_copy', '=', False), '|', '&', ('x_psm_0204_owner_job_id', '=', False), ('x_psm_0204_owner_department_id', '=', False), '&', ('x_psm_0204_owner_job_id', '=', id), ('x_psm_0204_owner_department_id', '=', department_id)]",
        help="Survey dung lam template tieu chi OJE cho job nay.",
    )

    job_refuse_reason_ids = fields.One2many(
        "hr.applicant.refuse.reason",
        "job_id",
        string="Cau hinh ly do tu choi",
    )

    oje_pass_score = fields.Float(string="Diem dat OJE", default=6.0)
    oje_evaluator_user_id = fields.Many2one(
        "res.users",
        string="Nguoi danh gia OJE",
        help="User chiu trach nhiem danh gia OJE (Snapshot tu requester cua Job Request)",
    )

    interview_evaluator_user_id = fields.Many2one(
        "res.users",
        string="Nguoi danh gia Interview",
        help="User chiu trach nhiem danh gia Interview cho ung vien Store + Management.",
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("no_of_recruitment", 0) > 0:
                vals["recruitment_qty_updated_at"] = fields.Datetime.now()

        jobs = super().create(vals_list)

        if not self.env.context.get("skip_default_config_bootstrap"):
            jobs._bootstrap_default_configuration_on_create()

        return jobs

    def write(self, vals):
        vals = dict(vals)

        # Guard: block manual edits to scope fields unless internal context provided
        if not self.env.context.get('x_psm_0204_allow_scope_sync'):
            blocked = {k for k in ('recruitment_type', 'position_level') if k in vals}
            if blocked:
                raise exceptions.UserError(
                    _(
                        "Recruitment Type and Level are managed by the system and cannot be "
                        "changed manually. Contact your system administrator if a correction is needed."
                    )
                )

        scope_key_changed = any(k in vals for k in ("recruitment_type", "position_level"))

        if "no_of_recruitment" in vals:
            changed_records = self.filtered(lambda r: r.no_of_recruitment != vals["no_of_recruitment"])
            if changed_records:
                vals["recruitment_qty_updated_at"] = fields.Datetime.now()

        res = super().write(vals)

        if scope_key_changed:
            for rec in self:
                scope = rec._get_oje_template_scope()
                if (
                    rec.x_psm_oje_survey_id
                    and rec.x_psm_oje_survey_id.x_psm_oje_scope
                    and scope
                    and rec.x_psm_oje_survey_id.x_psm_oje_scope != scope
                ):
                    rec.x_psm_oje_survey_id = False
                if not rec._is_interview_template_supported():
                    rec.x_psm_interview_survey_id = False

        return res

    @api.constrains("survey_id", "x_psm_interview_survey_id", "x_psm_oje_survey_id")
    def _check_x_psm_survey_owner_consistency(self):
        for rec in self:
            survey_bindings = [
                (_("Application Survey"), rec.survey_id),
                (_("Interview Survey"), rec.x_psm_interview_survey_id),
                (_("OJE Survey"), rec.x_psm_oje_survey_id),
            ]
            for label, survey in survey_bindings:
                if not survey:
                    continue

                if survey.x_psm_0204_owner_job_id and survey.x_psm_0204_owner_job_id != rec:
                    raise exceptions.ValidationError(
                        _(
                            "%(label)s đang thuộc Job '%(owner)s'. Vui lòng chọn survey chung hoặc survey custom của đúng Job hiện tại."
                        )
                        % {
                            "label": label,
                            "owner": survey.x_psm_0204_owner_job_id.display_name,
                        }
                    )

                if survey.x_psm_0204_owner_department_id and survey.x_psm_0204_owner_department_id != rec.department_id:
                    raise exceptions.ValidationError(
                        _(
                            "%(label)s đang thuộc Phòng ban '%(owner)s'. Vui lòng chọn survey chung hoặc survey custom của đúng Phòng ban hiện tại."
                        )
                        % {
                            "label": label,
                            "owner": survey.x_psm_0204_owner_department_id.display_name,
                        }
                    )

    @api.model
    def _x_psm_deactivate_legacy_hr_job_views(self):
        """Deactivate obsolete hr.job inherited views left from pre-migration versions."""
        self.env.cr.execute(
            """
            SELECT id
              FROM ir_ui_view
             WHERE active = TRUE
               AND model = 'hr.job'
               AND (
                    name = 'hr.job.application.field.view.form.inherit'
                OR name = 'hr.job.survey.config.view.form.inherit'
                    OR arch_db::text ILIKE '%application_field_ids%'
                    OR arch_db::text ILIKE '%action_load_default_fields%'
                OR arch_db::text ILIKE '%master_survey_id%'
               )
            """
        )
        legacy_view_ids = [row[0] for row in self.env.cr.fetchall()]
        if legacy_view_ids:
            self.env["ir.ui.view"].sudo().browse(legacy_view_ids).write({"active": False})
            _logger.info(
                "[LEGACY_VIEW_CLEANUP] Deactivated %s legacy hr.job views: %s",
                len(legacy_view_ids),
                legacy_view_ids,
            )

    @api.model
    def _x_psm_cleanup_obsolete_email_rule_metadata(self):
        """Remove stale metadata of deprecated x_psm_hr_job_email_rule layer.

        This hook is idempotent and safe to execute on every install/upgrade.
        """
        legacy_model_name = "x_psm_hr_job_email_rule"
        obsolete_job_field_names = [
            "email_rule_ids",
            "email_rule_stage_ids",
            "email_rule_event_ids",
        ]

        def _safe_unlink(model_name, domain, label, active_test=False, force_unlink=False):
            model = self.env[model_name].sudo().with_context(active_test=active_test)
            if force_unlink:
                model = model.with_context(_force_unlink=True)
            records = model.search(domain)
            if not records:
                return 0
            count = len(records)
            try:
                if force_unlink:
                    records = records.with_context(_force_unlink=True)
                records.unlink()
            except Exception as err:
                _logger.warning(
                    "[EMAIL_RULE_CLEANUP] Skip removing %s due to error: %s",
                    label,
                    err,
                )
                return 0
            _logger.info("[EMAIL_RULE_CLEANUP] Removed %s %s record(s)", count, label)
            return count

        # Remove xmlids that may anchor old hr.job technical fields.
        _safe_unlink(
            "ir.model.data",
            [
                ("module", "=", "M02_P0204"),
                ("model", "=", "ir.model.fields"),
                (
                    "name",
                    "in",
                    [
                        "field_hr_job__email_rule_ids",
                        "field_hr_job__email_rule_stage_ids",
                        "field_hr_job__email_rule_event_ids",
                    ],
                ),
            ],
            "legacy email-rule field xmlid",
        )

        # Remove obsolete hr.job fields that still point to the removed model.
        obsolete_fields = self.env["ir.model.fields"].sudo().search(
            [
                ("model", "=", "hr.job"),
                ("name", "in", obsolete_job_field_names),
            ]
        )
        if obsolete_fields:
            obsolete_field_ids = obsolete_fields.ids
            _safe_unlink(
                "ir.model.data",
                [
                    ("model", "=", "ir.model.fields"),
                    ("res_id", "in", obsolete_field_ids),
                ],
                "xmlid linked to obsolete hr.job email fields",
            )
            try:
                obsolete_fields.with_context(_force_unlink=True).unlink()
                _logger.info(
                    "[EMAIL_RULE_CLEANUP] Removed %s obsolete hr.job field metadata record(s)",
                    len(obsolete_field_ids),
                )
            except Exception as err:
                _logger.warning(
                    "[EMAIL_RULE_CLEANUP] Skip removing obsolete hr.job fields due to error: %s",
                    err,
                )

        # Remove metadata records directly referencing the removed model.
        _safe_unlink(
            "ir.model.access",
            [("model_id.model", "=", legacy_model_name)],
            "legacy model ACL",
        )
        _safe_unlink(
            "ir.rule",
            [("model_id.model", "=", legacy_model_name)],
            "legacy model record rule",
        )
        _safe_unlink(
            "ir.actions.act_window",
            [("res_model", "=", legacy_model_name)],
            "legacy model window action",
        )
        _safe_unlink(
            "ir.actions.server",
            [("model_name", "=", legacy_model_name)],
            "legacy model server action",
        )
        _safe_unlink(
            "ir.ui.view",
            [("model", "=", legacy_model_name)],
            "legacy model view",
            active_test=False,
        )
        _safe_unlink(
            "ir.model.fields",
            ["|", ("model", "=", legacy_model_name), ("relation", "=", legacy_model_name)],
            "legacy model field metadata",
            force_unlink=True,
        )
        _safe_unlink(
            "ir.model.data",
            [
                ("module", "=", "M02_P0204"),
                ("name", "=", "model_x_psm_hr_job_email_rule"),
            ],
            "legacy model xmlid anchor",
        )

        if "model_id" in self.env["ir.filters"]._fields:
            _safe_unlink(
                "ir.filters",
                [("model_id", "=", legacy_model_name)],
                "legacy model saved filter",
            )
        elif "model" in self.env["ir.filters"]._fields:
            _safe_unlink(
                "ir.filters",
                [("model", "=", legacy_model_name)],
                "legacy model saved filter",
            )

        if "model" in self.env["mail.template"]._fields:
            _safe_unlink(
                "mail.template",
                [("model", "=", legacy_model_name)],
                "legacy model mail template",
                active_test=False,
            )

        # Finally remove ir.model row if still present.
        _safe_unlink(
            "ir.model",
            [("model", "=", legacy_model_name)],
            "legacy model definition",
            force_unlink=True,
        )

    def _bootstrap_default_configuration_on_create(self):
        """Auto-load default settings for newly created jobs."""
        for job in self:
            try:
                if not job.applicant_properties_definition:
                    job.action_load_default_applicant_properties_definition()
            except Exception as err:
                _logger.warning(
                    "[JOB_BOOTSTRAP] Cannot load default applicant properties for job %s: %s",
                    job.id,
                    err,
                )

            try:
                if not job.job_refuse_reason_ids:
                    job.action_load_default_refuse_reasons()
            except Exception as err:
                _logger.warning("[JOB_BOOTSTRAP] Cannot load default refuse reasons for job %s: %s", job.id, err)

            try:
                job._x_psm_auto_bind_custom_surveys_on_create()
            except Exception as err:
                _logger.warning("[JOB_BOOTSTRAP] Cannot auto-bind custom surveys for job %s: %s", job.id, err)

    @api.depends("name", "department_id", "level_id")
    def _compute_recruitment_logic(self):
        for job in self:
            rec_type = "office"
            pos_level = "staff"

            if job.department_id and hasattr(job.department_id, "block_id"):
                block_code = job.department_id.block_id.code or ""
                if block_code == "OPS":
                    rec_type = "store"
                elif block_code == "RST":
                    rec_type = "office"
                else:
                    block_name = job.department_id.block_id.name or ""
                    if "Van hanh" in block_name or "Cua hang" in block_name:
                        rec_type = "store"

            if hasattr(job, "level_id") and job.level_id:
                level_code = (job.level_id.code or "").lower()
                level_name = (job.level_id.name or "").lower()
                if "manager" in level_code or "manager" in level_name or "quan ly" in level_name:
                    pos_level = "management"
                else:
                    pos_level = "staff"
            else:
                name_upper = (job.name or "").upper()
                if any(k in name_upper for k in ["MANAGER", "QUAN LY", "GIAM SAT", "SUPERVISOR", "LEADER", "TRAINEE MANAGER"]):
                    pos_level = "management"
                else:
                    pos_level = "staff"

            job.recruitment_type = rec_type
            job.position_level = pos_level

    @api.depends("name", "department_id")
    def _compute_display_name_with_dept(self):
        for job in self:
            if job.department_id:
                job.display_name_with_dept = f"{job.name} ({job.department_id.name})"
            else:
                job.display_name_with_dept = job.name

    def _get_stage_filter_type(self):
        """Return the canonical pipeline filter type key."""
        self.ensure_one()
        if self.recruitment_type == "store":
            return self.position_level if self.position_level in ("staff", "management") else False
        return self.recruitment_type or False

    def action_open_applicants(self):
        self.ensure_one()
        stage_type = self._get_stage_filter_type()

        return {
            "name": f"Ung Vien - {self.name}",
            "type": "ir.actions.act_window",
            "res_model": "hr.applicant",
            "view_mode": "kanban,list,form,pivot,graph,calendar,activity",
            "domain": [("job_id", "=", self.id)],
            "context": {
                "default_job_id": self.id,
                "search_default_job_id": [self.id],
                "search_default_applicants": 1,
                "default_recruitment_type": self.recruitment_type,
                "default_position_level": self.position_level,
                "default_stage_filter_type": stage_type,
                "dialog_size": "medium",
                "allow_search_matching_applicants": 1,
            },
        }

    def _x_psm_get_default_applicant_properties_definition(self):
        self.ensure_one()
        return [
            {
                "name": "x_psm_current_job",
                "string": "Cong viec hien tai",
                "type": "char",
            },
            {
                "name": "x_psm_birthday",
                "string": "Ngay sinh",
                "type": "date",
            },
            {
                "name": "x_psm_gender",
                "string": "Gioi tinh",
                "type": "selection",
                "selection": [["male", "Nam"], ["female", "Nu"], ["not_display", "Khong hien thi"]],
            },
            {
                "name": "x_psm_id_document_type",
                "string": "Loai giay to tuy than",
                "type": "selection",
                "selection": [["citizen_id", "CCCD"], ["passport", "Ho chieu"]],
            },
            {
                "name": "x_psm_id_number",
                "string": "So giay to tuy than",
                "type": "char",
            },
            {
                "name": "x_psm_education_level",
                "string": "Trinh do hoc van",
                "type": "selection",
                "selection": [
                    ["no_degree", "Chua tot nghiep"],
                    ["high_school", "Pho thong"],
                    ["vocational", "Trung cap"],
                    ["college", "Cao dang"],
                    ["university", "Dai hoc"],
                    ["master", "Thac sy"],
                    ["phd", "Tien sy"],
                    ["postgraduate", "Sau dai hoc"],
                    ["others", "Khac"],
                ],
            },
            {
                "name": "x_psm_school_name",
                "string": "Ten truong",
                "type": "char",
            },
            {
                "name": "x_psm_years_experience",
                "string": "So nam kinh nghiem",
                "type": "integer",
            },
            {
                "name": "x_psm_weekend_available",
                "string": "Co the lam cuoi tuan/Le Tet?",
                "type": "boolean",
            },
            {
                "name": "x_psm_worked_mcdonalds",
                "string": "Da tung lam viec tai McDonald's VN?",
                "type": "boolean",
            },
            {
                "name": "x_psm_application_content",
                "string": "Noi dung",
                "type": "text",
            },
        ]

    def _x_psm_normalize_plain_text(self, value):
        value = value or ""
        value = unicodedata.normalize("NFD", value)
        value = "".join(ch for ch in value if unicodedata.category(ch) != "Mn")
        value = value.lower()
        value = re.sub(r"[^a-z0-9]+", " ", value).strip()
        return value

    def _x_psm_make_webform_field_name(self, question, used_names):
        question_text = (question.title or question.question or "").strip()
        normalized = self._x_psm_normalize_plain_text(question_text)

        canonical_name_map = [
            ("so dien thoai", "partner_phone"),
            ("phone number", "partner_phone"),
            ("ngay sinh", "x_birthday"),
            ("ngay thang nam sinh", "x_birthday"),
            ("gioi tinh", "x_gender"),
            ("danh xung", "x_salutation"),
            ("loai giay to tuy than", "x_id_document_type"),
            ("so giay to tuy than", "x_id_number"),
            ("so cmt cccd ho chieu", "x_id_number"),
            ("so cmt can cuoc ho chieu", "x_id_number"),
            ("ngay cap giay to tuy than", "x_id_issue_date"),
            ("ngay cap cmt cccd ho chieu", "x_id_issue_date"),
            ("ngay cap cmt can cuoc ho chieu", "x_id_issue_date"),
            ("noi cap giay to tuy than", "x_id_issue_place"),
            ("noi cap cmt cccd ho chieu", "x_id_issue_place"),
            ("noi cap cmt can cuoc ho chieu", "x_id_issue_place"),
            ("quoc tich", "x_nationality"),
            ("chieu cao", "x_height"),
            ("can nang", "x_weight"),
            ("nguyen quan", "x_hometown"),
            ("dia chi thuong tru", "x_permanent_address"),
            ("dia chi hien tai", "x_current_address"),
            ("trinh do hoc van", "x_education_level"),
            ("ten truong", "x_school_name"),
            ("so nam kinh nghiem", "x_years_experience"),
            ("cong viec hien tai", "x_current_job"),
            ("cong ty gan nhat", "x_last_company"),
            ("co the lam viec cuoi tuan", "x_weekend_available"),
            ("da tung lam viec tai mcdonald", "x_worked_mcdonalds"),
            ("ma gioi thieu", "x_referral_staff_id"),
            ("staff id", "x_referral_staff_id"),
            ("noi dung", "x_application_content"),
            ("ghi chu them cho nha tuyen dung", "x_application_content"),
            ("anh chan dung", "x_portrait_image"),
        ]
        for marker, canonical_name in canonical_name_map:
            if marker in normalized:
                field_name = canonical_name
                counter = 1
                while field_name in used_names:
                    suffix = f"_{counter}"
                    field_name = f"{canonical_name[: max(1, 60 - len(suffix))]}{suffix}"
                    counter += 1
                return field_name

        slug = normalized.replace(" ", "_")[:48] if normalized else f"q_{question.id}"
        base_name = f"x_psm_{slug}" if slug else f"x_psm_q_{question.id}"
        field_name = base_name
        counter = 1
        while field_name in used_names:
            suffix = f"_{counter}"
            field_name = f"{base_name[: max(1, 60 - len(suffix))]}{suffix}"
            counter += 1
        return field_name

    def _x_psm_should_skip_survey_question_for_webform(self, question):
        question_text = self._x_psm_normalize_plain_text((question.title or question.question or "").strip())
        if not question_text:
            return True

        # Bo qua cac cau hoi trung voi field he thong tren form apply.
        always_skip_markers = [
            "ho ten",
            "ho ten ban",
            "ho va ten",
            "ho va ten ban",
            "ten day du",
            "email",
            "cv",
            "ho so dinh kem",
        ]
        return any(marker in question_text for marker in always_skip_markers)

    def _x_psm_get_pre_interview_survey_for_webform(self):
        self.ensure_one()

        if (
            self.survey_id
            and self.survey_id.x_psm_survey_usage == "pre_interview"
            and (not self.survey_id.x_psm_0204_owner_job_id or self.survey_id.x_psm_0204_owner_job_id == self)
            and (
                not self.survey_id.x_psm_0204_owner_department_id
                or self.survey_id.x_psm_0204_owner_department_id == self.department_id
            )
        ):
            return self.survey_id.sudo()

        survey = self._x_psm_find_default_survey("pre_interview")
        return survey.sudo() if survey else False

    def _x_psm_sanitize_applicant_properties_definition(self, definitions):
        """Keep only keys accepted by applicant_properties_definition schema."""
        allowed_keys = {"name", "string", "type", "selection", "default"}
        sanitized = []
        for definition in definitions or []:
            if not isinstance(definition, dict):
                continue

            clean = {key: definition[key] for key in allowed_keys if key in definition}
            if clean.get("name") and clean.get("type"):
                sanitized.append(clean)
        return sanitized

    def _x_psm_get_applicant_properties_definition_from_survey(self, survey=False, include_metadata=False):
        self.ensure_one()
        survey = (survey or self._x_psm_get_pre_interview_survey_for_webform())
        if not survey:
            return []

        definitions = []
        used_names = set()

        questions = survey.question_ids.filtered(
            lambda q: not q.is_page
        ).sorted(lambda q: ((q.page_id.sequence if q.page_id else 0), q.sequence, q.id))
        for idx, question in enumerate(questions, start=1):
            if self._x_psm_should_skip_survey_question_for_webform(question):
                continue

            question_text = (question.title or question.question or "").strip()
            if not question_text:
                continue

            qtype = question.question_type or "char_box"
            definition_type = "char"
            selection = []

            if qtype == "text_box":
                definition_type = "text"
            elif qtype == "numerical_box":
                definition_type = "float"
            elif qtype == "date":
                definition_type = "date"
            elif qtype == "datetime":
                definition_type = "datetime"
            elif qtype == "simple_choice":
                definition_type = "selection"
                selection = [
                    [str(answer.id), answer.value]
                    for answer in question.suggested_answer_ids.sorted("sequence")
                    if answer.value
                ]
            elif qtype == "multiple_choice":
                # Website form hiện lưu dạng single value text/selection, nên map về text để không mất dữ liệu.
                definition_type = "text"

            field_name = self._x_psm_make_webform_field_name(question, used_names)
            used_names.add(field_name)

            definition = {
                "name": field_name,
                "string": question_text,
                "type": definition_type,
            }
            if selection:
                definition["selection"] = selection

            if include_metadata:
                definition.update(
                    {
                        "is_active": bool(question.x_psm_show_on_webform is not False),
                        "required": bool(question.constr_mandatory),
                        "sequence": question.sequence or (idx * 10),
                        "source_survey_question_id": question.id,
                        "mandatory_correct": bool(question.x_psm_0204_is_mandatory_correct),
                        "reject_when_wrong": bool(getattr(question, "x_psm_0204_is_reject_when_wrong", False)),
                        "source_survey_page_id": question.page_id.id if question.page_id else False,
                        "source_survey_page_title": (
                            (question.page_id.title or question.page_id.question or "").strip()
                            if question.page_id
                            else False
                        ),
                    }
                )
                correct_values = [
                    str(answer.id)
                    for answer in question.suggested_answer_ids.sorted("sequence")
                    if answer.is_correct
                ]
                if correct_values:
                    definition["correct_selection_values"] = correct_values

            definitions.append(definition)

        return definitions

    def _x_psm_refresh_applicant_properties_from_pre_interview_survey(self):
        self.ensure_one()

        survey = self._x_psm_get_pre_interview_survey_for_webform()
        if not survey:
            return False

        definitions = self._x_psm_get_applicant_properties_definition_from_survey(survey)
        if not definitions:
            return False

        self.sudo().write(
            {
                "applicant_properties_definition": self._x_psm_sanitize_applicant_properties_definition(definitions),
            }
        )
        return True

    def action_load_applicant_properties_from_survey(self):
        self.ensure_one()

        survey = self._x_psm_get_pre_interview_survey_for_webform()
        if not survey:
            raise exceptions.UserError(
                _("Chưa có survey Pre-Interview để load biểu mẫu Website. Vui lòng cấu hình Application Survey trước.")
            )

        definitions = self._x_psm_get_applicant_properties_definition_from_survey(survey)
        if not definitions:
            raise exceptions.UserError(
                _("Survey Pre-Interview chưa có câu hỏi hợp lệ để tạo biểu mẫu Website.")
            )

        self.sudo().write(
            {
                "applicant_properties_definition": self._x_psm_sanitize_applicant_properties_definition(definitions)
            }
        )

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": "Thanh cong",
                "message": f"Da load bieu mau Website tu survey: {survey.title}",
                "type": "success",
                "sticky": False,
            },
        }

    def action_load_default_fields(self):
        """Backward-compatible alias kept for legacy button bindings in old DB views."""
        self.ensure_one()
        return self.action_load_default_applicant_properties_definition()

    def action_load_default_applicant_properties_definition(self):
        self.ensure_one()

        survey = self._x_psm_get_pre_interview_survey_for_webform()
        if survey:
            definitions = self._x_psm_get_applicant_properties_definition_from_survey(survey)
            if definitions:
                self.sudo().write(
                    {
                        "applicant_properties_definition": self._x_psm_sanitize_applicant_properties_definition(
                            definitions
                        )
                    }
                )
                return {
                    "type": "ir.actions.client",
                    "tag": "display_notification",
                    "params": {
                        "title": "Thanh cong",
                        "message": f"Da tai bieu mau Website tu survey: {survey.title}",
                        "type": "success",
                        "sticky": False,
                    },
                }

        self.sudo().write(
            {
                "applicant_properties_definition": self._x_psm_get_default_applicant_properties_definition(),
            }
        )

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": "Thanh cong",
                "message": "Da tai cau hinh mac dinh cho Applicant Properties.",
                "type": "success",
                "sticky": False,
            },
        }

    def action_load_default_refuse_reasons(self):
        """Nap cac ly do tu choi mac dinh vao cau hinh Job"""
        self.ensure_one()

        default_reasons = [
            "TA_KHONG PHU HOP VOI NHU CAU HIEN TAI CUA CUA HANG",
            "TA_KHONG LAM T7/CN/LE TET",
            "TA_KHONG DI SOM/VE TRE/CA DEM",
            "KINH NGHIEM KHONG PHU HOP",
            "FAIL PHONG VAN/OJE (GHI RO LI DO FAIL)",
            "KHONG LIEN HE DUOC",
            "LY DO KHAC (VUI LONG GHI RO)",
            "CHUA DU TUOI",
            "KHONG CON NHU CAU NHAN VIEC (NO SHOW)",
        ]

        existing_reasons = self.job_refuse_reason_ids.mapped("name")

        vals_list = []
        for reason in default_reasons:
            if reason not in existing_reasons:
                reason_type = "text" if any(kw in reason.lower() for kw in ["fail phong van/oje", "ly do khac"]) else "checkbox"
                vals_list.append(
                    {
                        "job_id": self.id,
                        "name": reason,
                        "reason_type": reason_type,
                        "active": True,
                    }
                )

        if vals_list:
            self.env["hr.applicant.refuse.reason"].create(vals_list)

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": "Thanh cong",
                "message": f"Da tai {len(vals_list)} ly do mac dinh.",
                "type": "success",
                "sticky": False,
            },
        }

    def _is_interview_template_supported(self):
        self.ensure_one()
        return bool(self.recruitment_type == "store" and self.position_level == "management")

    def _get_oje_template_scope(self):
        self.ensure_one()
        if self.recruitment_type != "store":
            return False
        if self.position_level == "management":
            return "store_management"
        return "store_staff"

    def _x_psm_is_xfactor_label(self, value):
        normalized = (value or "").strip().lower().replace(" ", "")
        return "xfactor" in normalized or "x-factor" in (value or "").strip().lower()

    def _x_psm_extract_interview_skillset_tokens(self, value):
        raw_value = (value or "").strip()
        if " - " not in raw_value:
            return False, raw_value
        left, right = raw_value.split(" - ", 1)
        left = (left or "").strip()
        right = (right or "").strip()
        if not left or not right:
            return False, raw_value
        return left, right

    def _x_psm_prepare_interview_snapshot_line(self, question, sequence):
        question_text = (question.title or question.question or "").strip()
        if not question_text:
            return False

        line_kind_hint = (question.x_psm_interview_line_kind or "auto").strip()
        group_label = (question.x_psm_interview_group_label or "").strip()

        display_type = "question"
        label = False
        output_question_text = question_text
        group_kind = "question"

        if line_kind_hint == "subheader":
            display_type = "subheader"
            label = question_text
            output_question_text = False
            group_kind = "subheader"
        elif line_kind_hint == "skillset_child":
            group_kind = "skillset_child"
            split_left, split_right = self._x_psm_extract_interview_skillset_tokens(question_text)
            if split_left and split_right:
                if not group_label:
                    group_label = split_left
                if group_label and split_left.lower() == group_label.lower():
                    output_question_text = split_right
        elif line_kind_hint == "question":
            group_kind = "question"
        else:
            split_left, split_right = self._x_psm_extract_interview_skillset_tokens(question_text)
            if split_left and split_right:
                normalized_left = split_left.lower()
                if "skillset" in normalized_left:
                    group_kind = "skillset_child"
                    if not group_label:
                        group_label = split_left
                    output_question_text = split_right

        if group_kind != "skillset_child":
            group_label = False

        is_required = bool(question.constr_mandatory) if display_type == "question" else False
        return {
            "source_question_id": question.id,
            "sequence": sequence,
            "display_type": display_type,
            "label": label,
            "question_text": output_question_text,
            "x_psm_interview_group_kind": group_kind,
            "x_psm_interview_group_label": group_label,
            "is_required": is_required,
            "is_active": True,
        }

    def _x_psm_get_interview_survey(self):
        self.ensure_one()
        return self.x_psm_interview_survey_id.sudo()

    def _x_psm_get_oje_survey(self):
        self.ensure_one()
        return self.x_psm_oje_survey_id.sudo()

    def _x_psm_group_questions_by_page(self, survey):
        ordered_items = survey.question_and_page_ids.sorted(lambda q: (q.sequence, q.id))
        pages = ordered_items.filtered("is_page")

        grouped = []
        if pages:
            unpaged_questions = ordered_items.filtered(lambda q: not q.is_page and not q.page_id).sorted("sequence")
            if unpaged_questions:
                grouped.append((False, unpaged_questions))

            for page in pages:
                page_questions = ordered_items.filtered(lambda q, p=page: (not q.is_page) and q.page_id == p).sorted("sequence")
                if page_questions:
                    grouped.append((page, page_questions))
            return grouped

        questions = ordered_items.filtered(lambda q: not q.is_page).sorted("sequence")
        if questions:
            grouped.append((False, questions))
        return grouped

    def _x_psm_prepare_interview_snapshot_sections(self):
        self.ensure_one()
        survey = self._x_psm_get_interview_survey()
        if not survey:
            return []

        prepared_sections = []
        section_sequence = 10

        for idx, (page, questions) in enumerate(self._x_psm_group_questions_by_page(survey), start=1):
            section_name = (page.title if page else False) or (page.question if page else False) or _("Section %s") % idx
            lines = []
            line_sequence = 10

            for question in questions:
                line_payload = self._x_psm_prepare_interview_snapshot_line(question, line_sequence)
                if not line_payload:
                    continue
                lines.append(line_payload)
                line_sequence += 10

            if lines:
                prepared_sections.append(
                    {
                        "source_question_id": page.id if page else False,
                        "sequence": section_sequence,
                        "name": section_name,
                        "is_active": True,
                        "lines": lines,
                    }
                )
                section_sequence += 10

        return prepared_sections

    def _x_psm_prepare_oje_snapshot_sections(self):
        self.ensure_one()
        survey = self._x_psm_get_oje_survey()
        scope = self._get_oje_template_scope()
        if not survey or not scope:
            return []

        prepared_sections = []
        section_sequence = 10

        grouped = self._x_psm_group_questions_by_page(survey)
        for idx, (page, questions) in enumerate(grouped, start=1):
            page_title = (page.title if page else False) or (page.question if page else False) or _("Section %s") % idx
            objective_text = page.description if page and "description" in page._fields else False

            if scope == "store_staff":
                lines = []
                line_sequence = 10
                for question in questions:
                    question_text = (question.title or question.question or "").strip()
                    if not question_text:
                        continue
                    lines.append(
                        {
                            "source_question_id": question.id,
                            "sequence": line_sequence,
                            "name": question_text,
                            "question_text": question_text,
                            "line_kind": "staff_question",
                            "scope": scope,
                            "rating_mode": "staff_matrix",
                            "is_required": bool(question.constr_mandatory),
                            "is_active": True,
                            "field_type": "radio",
                            "text_max_score": 0.0,
                            "checkbox_score": 0.0,
                        }
                    )
                    line_sequence += 10

                if lines:
                    prepared_sections.append(
                        {
                            "source_question_id": page.id if page else False,
                            "sequence": section_sequence,
                            "name": page_title,
                            "section_kind": "staff_block",
                            "scope": scope,
                            "rating_mode": "staff_matrix",
                            "objective_text": objective_text,
                            "hint_html": False,
                            "behavior_html": False,
                            "is_active": True,
                            "lines": lines,
                        }
                    )
                    section_sequence += 10
                continue

            # store_management
            section_kind_hint = page.x_psm_oje_section_kind if page and page.x_psm_oje_section_kind else "auto"
            page_force_xfactor = section_kind_hint == "management_xfactor"
            if section_kind_hint == "auto" and self._x_psm_is_xfactor_label(page_title):
                page_force_xfactor = True

            task_lines = []
            xfactor_lines = []
            line_sequence = 10

            for question in questions:
                question_text = (question.title or question.question or "").strip()
                if not question_text:
                    continue

                line_kind_hint = question.x_psm_oje_line_kind or "auto"
                if line_kind_hint != "auto":
                    line_kind = line_kind_hint
                elif page_force_xfactor or self._x_psm_is_xfactor_label(question_text):
                    line_kind = "management_xfactor"
                else:
                    line_kind = "management_task"

                line_vals = {
                    "source_question_id": question.id,
                    "sequence": line_sequence,
                    "name": question_text,
                    "question_text": question_text,
                    "line_kind": line_kind,
                    "scope": scope,
                    "is_required": bool(question.constr_mandatory),
                    "is_active": True,
                }

                if line_kind == "management_xfactor":
                    line_vals.update(
                        {
                            "rating_mode": "xfactor_yes_no",
                            "field_type": "checkbox",
                            "text_max_score": 0.0,
                            "checkbox_score": 1.0,
                        }
                    )
                    xfactor_lines.append(line_vals)
                else:
                    line_vals.update(
                        {
                            "line_kind": "management_task",
                            "rating_mode": "management_1_5",
                            "field_type": "text",
                            "text_max_score": 5.0,
                            "checkbox_score": 0.0,
                        }
                    )
                    task_lines.append(line_vals)

                line_sequence += 10

            if task_lines:
                prepared_sections.append(
                    {
                        "source_question_id": page.id if page else False,
                        "sequence": section_sequence,
                        "name": page_title,
                        "section_kind": "management_dimension",
                        "scope": scope,
                        "rating_mode": "management_1_5",
                        "objective_text": objective_text,
                        "hint_html": False,
                        "behavior_html": False,
                        "is_active": True,
                        "lines": task_lines,
                    }
                )
                section_sequence += 10

            if xfactor_lines:
                section_name = page_title if page_force_xfactor else _("X-Factor")
                prepared_sections.append(
                    {
                        "source_question_id": page.id if page else False,
                        "sequence": section_sequence,
                        "name": section_name,
                        "section_kind": "management_xfactor",
                        "scope": scope,
                        "rating_mode": "xfactor_yes_no",
                        "objective_text": False,
                        "hint_html": False,
                        "behavior_html": False,
                        "is_active": True,
                        "lines": xfactor_lines,
                    }
                )
                section_sequence += 10

        return prepared_sections

    def _get_interview_config_signature(self):
        self.ensure_one()
        sections = self._x_psm_prepare_interview_snapshot_sections()
        payload = []
        for section in sections:
            payload.append(
                {
                    "source_question_id": section["source_question_id"],
                    "name": section["name"],
                    "lines": [
                        {
                            "source_question_id": line.get("source_question_id"),
                            "display_type": line.get("display_type"),
                            "label": line.get("label"),
                            "question_text": line.get("question_text"),
                            "x_psm_interview_group_kind": line.get("x_psm_interview_group_kind"),
                            "x_psm_interview_group_label": line.get("x_psm_interview_group_label"),
                            "is_required": line.get("is_required"),
                        }
                        for line in section["lines"]
                    ],
                }
            )
        return json.dumps(payload, sort_keys=True, ensure_ascii=False)

    def _x_psm_get_oje_config_signature(self):
        self.ensure_one()
        sections = self._x_psm_prepare_oje_snapshot_sections()
        payload = []
        for section in sections:
            payload.append(
                {
                    "source_question_id": section["source_question_id"],
                    "name": section["name"],
                    "section_kind": section["section_kind"],
                    "lines": [
                        {
                            "source_question_id": line["source_question_id"],
                            "line_kind": line["line_kind"],
                            "question_text": line["question_text"],
                        }
                        for line in section["lines"]
                    ],
                }
            )
        return json.dumps(payload, sort_keys=True, ensure_ascii=False)

    def _x_psm_get_default_template_selector(self, usage, scope=False):
        if usage == "pre_interview":
            return "pre_interview"
        if usage == "interview":
            return "interview"
        if usage == "oje":
            if scope == "store_staff":
                return "oje_store_staff"
            if scope == "store_management":
                return "oje_store_management"
        return False

    def _x_psm_find_default_survey(self, usage, scope=False):
        survey_model = self.env["survey.survey"].sudo()

        default_selector = self._x_psm_get_default_template_selector(usage, scope=scope)
        if default_selector:
            survey = survey_model.search(
                [
                    "|",
                    ("x_psm_0204_default_template_for", "=", default_selector),
                    ("x_psm_default_template_for", "=", default_selector),
                    ("x_psm_0204_owner_job_id", "=", False),
                    ("x_psm_0204_owner_department_id", "=", False),
                    ("x_psm_0204_is_runtime_isolated_copy", "=", False),
                    ("active", "=", True),
                ],
                limit=1,
            )
            if survey:
                return survey

        domain = [
            ("x_psm_survey_usage", "=", usage),
            ("x_psm_0204_owner_job_id", "=", False),
            ("x_psm_0204_owner_department_id", "=", False),
            ("x_psm_0204_is_runtime_isolated_copy", "=", False),
            ("active", "=", True),
        ]
        if usage == "oje" and scope:
            domain.append(("x_psm_oje_scope", "=", scope))
        return survey_model.search(domain, order="id asc", limit=1)

    def _x_psm_get_owner_department(self):
        self.ensure_one()
        return self.department_id.sudo()

    def _x_psm_ensure_owner_department(self):
        self.ensure_one()
        if not self.department_id:
            raise exceptions.UserError(
                _("Vui lòng chọn Phòng ban cho Job Position trước khi thao tác survey custom.")
            )
        return self.department_id.sudo()

    def _x_psm_get_survey_binding_field_name(self, usage):
        mapping = {
            "pre_interview": "survey_id",
            "interview": "x_psm_interview_survey_id",
            "oje": "x_psm_oje_survey_id",
        }
        return mapping.get(usage)

    def _x_psm_get_bound_survey(self, usage):
        self.ensure_one()
        field_name = self._x_psm_get_survey_binding_field_name(usage)
        if not field_name:
            return False
        return self[field_name].sudo()

    def _x_psm_set_bound_survey(self, usage, survey=False):
        self.ensure_one()
        field_name = self._x_psm_get_survey_binding_field_name(usage)
        if not field_name:
            return
        self[field_name] = survey.id if survey else False

    def _x_psm_is_master_template_survey(self, survey):
        return bool(
            survey
            and not survey.x_psm_0204_is_runtime_isolated_copy
            and not survey.x_psm_0204_owner_job_id
            and not survey.x_psm_0204_owner_department_id
            and (survey.x_psm_0204_default_template_for or survey.x_psm_default_template_for)
        )

    def _x_psm_find_existing_custom_survey(self, usage, scope=False):
        self.ensure_one()
        owner_department = self._x_psm_get_owner_department()
        if not owner_department:
            return self.env["survey.survey"]

        domain = [
            ("x_psm_0204_owner_job_id", "=", self.id),
            ("x_psm_0204_is_runtime_isolated_copy", "=", False),
            "|",
            ("x_psm_0204_owner_department_id", "=", owner_department.id),
            ("x_psm_0204_owner_department_id", "=", False),
            ("x_psm_survey_usage", "=", usage),
            ("active", "=", True),
        ]
        if usage == "oje" and scope:
            domain.append(("x_psm_oje_scope", "=", scope))

        existing = self.env["survey.survey"].sudo().search(domain, order="id desc", limit=1)
        if (
            existing
            and owner_department
            and not existing.x_psm_0204_owner_department_id
        ):
            existing.sudo().write({"x_psm_0204_owner_department_id": owner_department.id})
        return existing

    def _x_psm_get_template_source_survey(self, usage, current_survey=False, scope=False):
        self.ensure_one()
        if current_survey and current_survey.x_psm_survey_usage == usage:
            if usage != "oje" or not scope or current_survey.x_psm_oje_scope == scope:
                if self._x_psm_is_master_template_survey(current_survey):
                    return current_survey.sudo()
        return self._x_psm_find_default_survey(usage, scope=scope)

    def _x_psm_build_custom_survey_title(self, source_survey):
        self.ensure_one()
        department_name = self.department_id.display_name or _("No Department")
        return _("%(title)s - %(job)s - %(department)s (Custom)") % {
            "title": source_survey.title,
            "job": self.name,
            "department": department_name,
        }

    def _x_psm_ensure_custom_survey_title(self, survey, source_survey=False):
        self.ensure_one()
        if not survey:
            return survey

        source = source_survey
        if not source and survey.x_psm_0204_default_template_for:
            source = survey
        if not source and survey.x_psm_survey_usage:
            source = self._x_psm_find_default_survey(
                survey.x_psm_survey_usage,
                scope=survey.x_psm_oje_scope or False,
            )

        if not source:
            return survey

        expected_title = self._x_psm_build_custom_survey_title(source)
        if survey.title != expected_title:
            survey.sudo().write({"title": expected_title})
        return survey

    def _x_psm_clone_survey_for_job(self, source_survey, usage, scope=False):
        self.ensure_one()
        if not source_survey:
            raise exceptions.UserError(_("Khong tim thay survey nguon de clone."))

        owner_department = self._x_psm_ensure_owner_department()

        cloned_survey = source_survey.sudo().copy(
            {
                "title": self._x_psm_build_custom_survey_title(source_survey),
                "x_psm_survey_usage": usage,
                "x_psm_0204_is_runtime_isolated_copy": False,
                "x_psm_oje_scope": scope if usage == "oje" else False,
                "x_psm_default_template_for": False,
                "x_psm_0204_owner_job_id": self.id,
                "x_psm_0204_owner_department_id": owner_department.id,
                "active": True,
            }
        )
        return self._x_psm_ensure_custom_survey_title(cloned_survey.sudo(), source_survey=source_survey)

    def _x_psm_archive_existing_custom_survey(self, usage, scope=False):
        self.ensure_one()
        owner_department = self._x_psm_get_owner_department()
        if not owner_department:
            return self.env["survey.survey"]

        domain = [
            ("x_psm_0204_owner_job_id", "=", self.id),
            ("x_psm_0204_is_runtime_isolated_copy", "=", False),
            "|",
            ("x_psm_0204_owner_department_id", "=", owner_department.id),
            ("x_psm_0204_owner_department_id", "=", False),
            ("x_psm_survey_usage", "=", usage),
            ("active", "=", True),
        ]
        if usage == "oje" and scope:
            domain.append(("x_psm_oje_scope", "=", scope))

        custom_survey = self.env["survey.survey"].sudo().search(domain)
        if custom_survey:
            custom_survey.sudo().write({"active": False})
        return custom_survey

    def _x_psm_ensure_custom_survey_binding(self, usage, scope=False, source_survey=False):
        self.ensure_one()
        self._x_psm_ensure_owner_department()

        existing_custom = self._x_psm_find_existing_custom_survey(usage, scope=scope)
        if existing_custom:
            existing_custom = self._x_psm_ensure_custom_survey_title(
                existing_custom,
                source_survey=source_survey,
            )
            self._x_psm_set_bound_survey(usage, existing_custom)
            if usage == "pre_interview":
                self._x_psm_refresh_applicant_properties_from_pre_interview_survey()
            return existing_custom, False

        source = source_survey or self._x_psm_find_default_survey(usage, scope=scope)
        if not source:
            return False, False

        custom_survey = self._x_psm_clone_survey_for_job(source, usage, scope=scope)
        self._x_psm_set_bound_survey(usage, custom_survey)
        if usage == "pre_interview":
            self._x_psm_refresh_applicant_properties_from_pre_interview_survey()
        return custom_survey, True

    def _x_psm_overwrite_custom_from_master(self, usage, scope=False):
        """
        [Load Default] — Restore/overwrite custom survey content from master.

        Behaviour:
        - If no custom exists: create a new one from master (clone).
        - If custom exists: delete all questions and re-copy from master.
          Preserved: title, owner_job_id, owner_department_id, usage, scope, active.

        Returns:
            tuple(survey, was_freshly_created)
        """
        self.ensure_one()
        master = self._x_psm_find_default_survey(usage, scope=scope)
        if not master:
            return False, False

        self._x_psm_ensure_owner_department()
        existing = self._x_psm_find_existing_custom_survey(usage, scope=scope)

        if not existing:
            # No custom yet — create fresh from master
            custom = self._x_psm_clone_survey_for_job(master, usage, scope=scope)
            self._x_psm_set_bound_survey(usage, custom)
            if usage == "pre_interview":
                self._x_psm_refresh_applicant_properties_from_pre_interview_survey()
            return custom, True

        # Custom exists — overwrite all questions/sections from master
        custom = existing

        # Replace full structure/content from master using shared logic
        # to keep Load Default and master->custom propagate consistent.
        self.env["survey.survey"]._x_psm_replace_custom_content_from_master(master, custom)

        # Keep custom title consistent with this job
        self._x_psm_ensure_custom_survey_title(custom, source_survey=master)

        self._x_psm_set_bound_survey(usage, custom)
        if usage == "pre_interview":
            self._x_psm_refresh_applicant_properties_from_pre_interview_survey()
        return custom, False

    def _x_psm_auto_bind_custom_surveys_on_create(self):
        self.ensure_one()
        if not self.department_id:
            return False

        pre_master = self._x_psm_find_default_survey("pre_interview")
        if pre_master:
            self._x_psm_ensure_custom_survey_binding("pre_interview", source_survey=pre_master)

        if self._is_interview_template_supported():
            interview_master = self._x_psm_find_default_survey("interview")
            if interview_master:
                self._x_psm_ensure_custom_survey_binding("interview", source_survey=interview_master)

        oje_scope = self._get_oje_template_scope()
        if oje_scope:
            oje_master = self._x_psm_find_default_survey("oje", scope=oje_scope)
            if oje_master:
                self._x_psm_ensure_custom_survey_binding("oje", scope=oje_scope, source_survey=oje_master)

        return True

    def _x_psm_open_survey_dialog_action(self, survey, window_title):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": window_title,
            "res_model": "survey.survey",
            "res_id": survey.id,
            "view_mode": "form",
            "target": "new",
            "context": {
                **self.env.context,
                "form_view_initial_mode": "edit",
                "x_psm_allow_custom_survey_edit_job_id": self.id,
                "x_psm_allow_custom_survey_edit_department_id": self.department_id.id if self.department_id else False,
            },
        }

    def action_load_default_pre_interview_template(self):
        """Load Default: overwrite Application custom survey from master template."""
        self.ensure_one()
        survey, created = self._x_psm_overwrite_custom_from_master("pre_interview")
        if not survey:
            raise exceptions.UserError(_(
                "No Application master survey found (x_psm_survey_usage = pre_interview). "
                "Please configure a master survey first."
            ))
        msg = (
            _("Application Survey created from master: %s") % survey.title
            if created
            else _("Application Survey restored from master: %s") % survey.title
        )
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {"title": _("Done"), "message": msg, "type": "success", "sticky": False},
        }

    def action_load_default_interview_template(self):
        """Load Default: overwrite Interview custom survey from master template."""
        self.ensure_one()
        if not self._is_interview_template_supported():
            raise exceptions.UserError(_(
                "Interview survey is only supported for Store + Management jobs."
            ))
        survey, created = self._x_psm_overwrite_custom_from_master("interview")
        if not survey:
            raise exceptions.UserError(_(
                "No Interview master survey found. Please configure a master survey first."
            ))
        msg = (
            _("Interview Survey created from master: %s") % survey.title
            if created
            else _("Interview Survey restored from master: %s") % survey.title
        )
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {"title": _("Done"), "message": msg, "type": "success", "sticky": False},
        }

    def action_load_default_oje_template(self):
        """Load Default: overwrite OJE custom survey from master template."""
        self.ensure_one()
        scope = self._get_oje_template_scope()
        if not scope:
            raise exceptions.UserError(_(
                "OJE survey is only supported for Store jobs."
            ))
        survey, created = self._x_psm_overwrite_custom_from_master("oje", scope=scope)
        if not survey:
            raise exceptions.UserError(_("No OJE master survey found for scope %s.") % scope)
        msg = (
            _("OJE Survey created from master: %s") % survey.title
            if created
            else _("OJE Survey restored from master: %s") % survey.title
        )
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {"title": _("Done"), "message": msg, "type": "success", "sticky": False},
        }

    def action_open_pre_interview_survey_dialog(self):
        self.ensure_one()
        survey = self.survey_id.sudo()
        source_survey = False

        if survey and survey.x_psm_survey_usage != "pre_interview":
            raise exceptions.UserError(_("Survey duoc chon phai thuoc usage Pre-Interview."))

        if survey and survey.x_psm_0204_owner_job_id and survey.x_psm_0204_owner_job_id != self:
            raise exceptions.UserError(_("Survey custom nay thuoc Job khac, khong the mo/chinh sua tai Job hien tai."))
        if survey and survey.x_psm_0204_owner_department_id and survey.x_psm_0204_owner_department_id != self.department_id:
            raise exceptions.UserError(_("Survey custom nay thuoc Phong ban khac, khong the mo/chinh sua tai Job hien tai."))

        if survey and self._x_psm_is_master_template_survey(survey):
            source_survey = survey

        if not survey or source_survey:
            survey, _created = self._x_psm_ensure_custom_survey_binding(
                "pre_interview",
                source_survey=source_survey,
            )
            if not survey:
                raise exceptions.UserError(_("Chua co survey Application master de tao/goi survey custom."))

        return self._x_psm_open_survey_dialog_action(survey, _("Application Survey"))

    def action_open_interview_survey_dialog(self):
        self.ensure_one()
        if not self._is_interview_template_supported():
            raise exceptions.UserError(_("Chi ho tro thao tac Interview cho job Store + Management."))
        survey = self.x_psm_interview_survey_id.sudo()
        source_survey = False

        if survey and survey.x_psm_survey_usage != "interview":
            raise exceptions.UserError(_("Survey duoc chon phai thuoc usage Interview."))

        if survey and survey.x_psm_0204_owner_job_id and survey.x_psm_0204_owner_job_id != self:
            raise exceptions.UserError(_("Survey custom nay thuoc Job khac, khong the mo/chinh sua tai Job hien tai."))
        if survey and survey.x_psm_0204_owner_department_id and survey.x_psm_0204_owner_department_id != self.department_id:
            raise exceptions.UserError(_("Survey custom nay thuoc Phong ban khac, khong the mo/chinh sua tai Job hien tai."))

        if survey and self._x_psm_is_master_template_survey(survey):
            source_survey = survey

        if not survey or source_survey:
            survey, _created = self._x_psm_ensure_custom_survey_binding(
                "interview",
                source_survey=source_survey,
            )
            if not survey:
                raise exceptions.UserError(_("Chua co survey Interview master de tao/goi survey custom."))

        return self._x_psm_open_survey_dialog_action(survey, _("Interview Survey"))

    def action_open_oje_survey_dialog(self):
        self.ensure_one()
        scope = self._get_oje_template_scope()
        if not scope:
            raise exceptions.UserError(_("Chi ho tro thao tac OJE cho job thuoc khoi Cua hang."))
        survey = self.x_psm_oje_survey_id.sudo()
        source_survey = False

        if survey and survey.x_psm_survey_usage != "oje":
            raise exceptions.UserError(_("Survey duoc chon phai thuoc usage OJE."))
        if survey and survey.x_psm_oje_scope and survey.x_psm_oje_scope != scope:
            raise exceptions.UserError(_("Survey OJE duoc chon khong dung scope voi Job hien tai."))

        if survey and survey.x_psm_0204_owner_job_id and survey.x_psm_0204_owner_job_id != self:
            raise exceptions.UserError(_("Survey custom nay thuoc Job khac, khong the mo/chinh sua tai Job hien tai."))
        if survey and survey.x_psm_0204_owner_department_id and survey.x_psm_0204_owner_department_id != self.department_id:
            raise exceptions.UserError(_("Survey custom nay thuoc Phong ban khac, khong the mo/chinh sua tai Job hien tai."))

        if survey and self._x_psm_is_master_template_survey(survey):
            source_survey = survey

        if not survey or source_survey:
            survey, _created = self._x_psm_ensure_custom_survey_binding(
                "oje",
                scope=scope,
                source_survey=source_survey,
            )
            if not survey:
                raise exceptions.UserError(_("Chua co survey OJE master de tao/goi survey custom."))

        return self._x_psm_open_survey_dialog_action(survey, _("OJE Survey"))

    # ── Deprecated stubs (buttons removed from UI, kept to prevent RPC errors) ──

    def action_create_custom_pre_interview_survey(self):
        """[DEPRECATED] Use Load Default instead."""
        _logger.warning("[0204] action_create_custom_pre_interview_survey is deprecated. Redirecting to Load Default.")
        return self.action_load_default_pre_interview_template()

    def action_create_custom_interview_survey(self):
        """[DEPRECATED] Use Load Default instead."""
        _logger.warning("[0204] action_create_custom_interview_survey is deprecated. Redirecting to Load Default.")
        return self.action_load_default_interview_template()

    def action_create_custom_oje_survey(self):
        """[DEPRECATED] Use Load Default instead."""
        _logger.warning("[0204] action_create_custom_oje_survey is deprecated. Redirecting to Load Default.")
        return self.action_load_default_oje_template()

    def action_replace_custom_pre_interview_survey(self):
        """[DEPRECATED] Use Load Default instead."""
        _logger.warning("[0204] action_replace_custom_pre_interview_survey is deprecated. Redirecting to Load Default.")
        return self.action_load_default_pre_interview_template()

    def action_replace_custom_interview_survey(self):
        """[DEPRECATED] Use Load Default instead."""
        _logger.warning("[0204] action_replace_custom_interview_survey is deprecated. Redirecting to Load Default.")
        return self.action_load_default_interview_template()

    def action_replace_custom_oje_survey(self):
        """[DEPRECATED] Use Load Default instead."""
        _logger.warning("[0204] action_replace_custom_oje_survey is deprecated. Redirecting to Load Default.")
        return self.action_load_default_oje_template()

    def action_preview_interview_form(self):
        self.ensure_one()
        if not self._is_interview_template_supported():
            raise exceptions.UserError(_("Chi ho tro preview Interview cho job Store + Management."))
        if not self.x_psm_interview_survey_id:
            raise exceptions.UserError(_("Vui long cau hinh Survey Interview tren Job Position."))
        if not self._x_psm_prepare_interview_snapshot_sections():
            raise exceptions.UserError(_("Survey Interview chua co cau hoi de preview."))

        return {
            "type": "ir.actions.act_url",
            "name": _("Preview Interview Form"),
            "url": f"/recruitment/interview/job-preview/{self.id}",
            "target": "new",
        }

    def action_preview_oje_form(self):
        self.ensure_one()
        scope = self._get_oje_template_scope()
        if not scope:
            raise exceptions.UserError(_("Chi ho tro preview OJE cho job thuoc khoi Cua hang."))
        if not self.x_psm_oje_survey_id:
            raise exceptions.UserError(_("Vui long cau hinh Survey OJE tren Job Position."))
        if not self._x_psm_prepare_oje_snapshot_sections():
            raise exceptions.UserError(_("Survey OJE chua co cau hoi de preview."))

        return {
            "type": "ir.actions.act_url",
            "name": _("Preview OJE Form"),
            "url": f"/recruitment/oje/job-preview/{self.id}",
            "target": "new",
        }
