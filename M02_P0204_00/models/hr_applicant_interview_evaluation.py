# -*- coding: utf-8 -*-
from odoo import api, exceptions, fields, models, _


class HrApplicantInterviewEvaluation(models.Model):
    _name = "hr.applicant.interview.evaluation"
    _description = "Applicant Interview Evaluation"
    _order = "id desc"

    applicant_id = fields.Many2one("hr.applicant", string="Applicant", required=True, ondelete="cascade")
    job_id = fields.Many2one("hr.job", string="Job Position", required=True)
    evaluator_user_id = fields.Many2one("res.users", string="Evaluator")

    state = fields.Selection(
        [
            ("new", "New"),
            ("in_progress", "In Progress"),
            ("done", "Done"),
        ],
        string="State",
        default="new",
        required=True,
    )

    interview_date = fields.Date(string="Interview Date")
    interviewer_name = fields.Char(string="Interviewer")
    onboard_time = fields.Char(string="Onboard Time")
    submitted_at = fields.Datetime(string="Submitted At")
    overall_note = fields.Text(string="Overall Note")

    template_version = fields.Char(string="Template Version")
    config_signature = fields.Text(string="Config Signature")

    score_1_count = fields.Integer(string="Score 1 Count", compute="_compute_score_summary", store=True)
    score_2_count = fields.Integer(string="Score 2 Count", compute="_compute_score_summary", store=True)
    score_3_count = fields.Integer(string="Score 3 Count", compute="_compute_score_summary", store=True)
    score_4_count = fields.Integer(string="Score 4 Count", compute="_compute_score_summary", store=True)
    score_5_count = fields.Integer(string="Score 5 Count", compute="_compute_score_summary", store=True)

    weighted_total = fields.Float(string="Weighted Total", compute="_compute_score_summary", store=True)
    rated_line_count = fields.Integer(string="Rated Line Count", compute="_compute_score_summary", store=True)
    final_score = fields.Float(string="Final Score", compute="_compute_score_summary", store=True, digits=(16, 2))

    result = fields.Selection(
        [
            ("pass", "Pass"),
            ("reject", "Reject"),
        ],
        string="Final Result",
        compute="_compute_result",
        store=True,
    )

    stage_applied = fields.Boolean(string="Stage Applied", default=False)

    section_ids = fields.One2many(
        "hr.applicant.interview.evaluation.section",
        "evaluation_id",
        string="Sections",
    )
    line_ids = fields.One2many(
        "hr.applicant.interview.evaluation.line",
        "evaluation_id",
        string="Lines",
    )

    @api.depends("line_ids.selected_score", "line_ids.display_type", "line_ids.is_active")
    def _compute_score_summary(self):
        for rec in self:
            question_lines = rec.line_ids.filtered(lambda line: line.is_active and line.display_type == "question")
            rec.score_1_count = len(question_lines.filtered(lambda line: line.selected_score == 1))
            rec.score_2_count = len(question_lines.filtered(lambda line: line.selected_score == 2))
            rec.score_3_count = len(question_lines.filtered(lambda line: line.selected_score == 3))
            rec.score_4_count = len(question_lines.filtered(lambda line: line.selected_score == 4))
            rec.score_5_count = len(question_lines.filtered(lambda line: line.selected_score == 5))

            rec.rated_line_count = rec.score_1_count + rec.score_2_count + rec.score_3_count + rec.score_4_count + rec.score_5_count
            rec.weighted_total = (
                (1 * rec.score_1_count)
                + (2 * rec.score_2_count)
                + (3 * rec.score_3_count)
                + (4 * rec.score_4_count)
                + (5 * rec.score_5_count)
            )
            rec.final_score = (rec.weighted_total / rec.rated_line_count) if rec.rated_line_count else 0.0

    @api.depends("weighted_total", "rated_line_count")
    def _compute_result(self):
        for rec in self:
            if rec.rated_line_count <= 0:
                rec.result = "reject"
            else:
                raw_score = rec.weighted_total / rec.rated_line_count
                rec.result = "pass" if raw_score >= 3.0 else "reject"

    def _validate_before_submit(self):
        for rec in self:
            question_lines = rec.line_ids.filtered(lambda line: line.is_active and line.display_type == "question")
            if not question_lines:
                raise exceptions.UserError(_("Chua co dong Question active de danh gia Interview."))

            invalid_lines = question_lines.filtered(lambda line: line.selected_score not in (1, 2, 3, 4, 5))
            if invalid_lines:
                raise exceptions.UserError(_("Vui long chon diem 1..5 cho tat ca dong Question."))

    def action_submit(self):
        for rec in self:
            if rec.state == "done":
                raise exceptions.UserError(_("Phieu Interview da nop va bi khoa chinh sua."))

            rec._validate_before_submit()

            rec.write({
                "state": "done",
                "submitted_at": fields.Datetime.now(),
            })

            rec.applicant_id.sudo().action_apply_interview_evaluation_result()


class HrApplicantInterviewEvaluationSection(models.Model):
    _name = "hr.applicant.interview.evaluation.section"
    _description = "Applicant Interview Evaluation Section"
    _order = "sequence, id"

    evaluation_id = fields.Many2one(
        "hr.applicant.interview.evaluation",
        string="Evaluation",
        required=True,
        ondelete="cascade",
    )
    source_config_section_id = fields.Many2one(
        "survey.question",
        string="Source Survey Page",
        ondelete="set null",
    )

    sequence = fields.Integer(default=10)
    name = fields.Char(string="Section Title", required=True)
    is_active = fields.Boolean(default=True)

    line_ids = fields.One2many(
        "hr.applicant.interview.evaluation.line",
        "section_id",
        string="Lines",
    )


class HrApplicantInterviewEvaluationLine(models.Model):
    _name = "hr.applicant.interview.evaluation.line"
    _description = "Applicant Interview Evaluation Line"
    _order = "sequence, id"

    evaluation_id = fields.Many2one(
        "hr.applicant.interview.evaluation",
        string="Evaluation",
        required=True,
        ondelete="cascade",
    )
    section_id = fields.Many2one(
        "hr.applicant.interview.evaluation.section",
        string="Section",
        ondelete="cascade",
    )
    template_line_id = fields.Many2one(
        "survey.question",
        string="Source Survey Question",
        ondelete="set null",
    )

    sequence = fields.Integer(default=10)
    display_type = fields.Selection(
        [
            ("section", "Section"),
            ("subheader", "Sub Header"),
            ("question", "Question"),
        ],
        string="Display Type",
        default="question",
        required=True,
    )
    label = fields.Char(string="Label")
    question_text = fields.Text(string="Question")
    x_psm_interview_group_kind = fields.Selection(
        [
            ("none", "None"),
            ("question", "Question"),
            ("subheader", "Sub Header"),
            ("skillset_child", "Skillset Child"),
        ],
        string="Interview Group Kind",
        default="none",
    )
    x_psm_interview_group_label = fields.Char(string="Interview Group Label")
    is_active = fields.Boolean(default=True)
    is_required = fields.Boolean(default=True)

    selected_score = fields.Integer(string="Selected Score")
    line_comment = fields.Text(string="Comment")

    @api.constrains("selected_score", "display_type")
    def _check_selected_score(self):
        for rec in self:
            if rec.display_type != "question":
                continue
            if rec.selected_score and rec.selected_score not in (1, 2, 3, 4, 5):
                raise exceptions.ValidationError(_("Diem danh gia Interview chi hop le trong khoang 1..5."))
