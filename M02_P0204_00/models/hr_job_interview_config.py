# -*- coding: utf-8 -*-
from odoo import api, exceptions, fields, models, _


class HrJobInterviewConfigSection(models.Model):
    _name = "hr.job.interview.config.section"
    _description = "Job Interview Configuration Section"
    _order = "sequence, id"

    job_id = fields.Many2one("hr.job", string="Job Position", required=True, ondelete="cascade")
    sequence = fields.Integer(default=10)
    is_active = fields.Boolean(default=True)

    name = fields.Char(string="Section Title", required=True)
    is_from_master = fields.Boolean(default=False)
    source_template_section_id = fields.Many2one(
        "recruitment.interview.template.section",
        string="Source Template Section",
        ondelete="set null",
    )

    line_ids = fields.One2many(
        "hr.job.interview.config.line",
        "section_id",
        string="Lines",
    )
    line_count = fields.Integer(string="Question Count", compute="_compute_line_count")

    @api.depends("line_ids", "line_ids.is_active")
    def _compute_line_count(self):
        for rec in self:
            rec.line_count = len(rec.line_ids.filtered(lambda line: line.is_active and line.display_type == "question"))


class HrJobInterviewConfigLine(models.Model):
    _name = "hr.job.interview.config.line"
    _description = "Job Interview Configuration Line"
    _order = "sequence, id"

    job_id = fields.Many2one("hr.job", string="Job Position", required=True, ondelete="cascade")
    section_id = fields.Many2one(
        "hr.job.interview.config.section",
        string="Section",
        required=True,
        ondelete="cascade",
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
    is_active = fields.Boolean(default=True)
    is_required = fields.Boolean(default=True)

    is_from_master = fields.Boolean(default=False)
    source_template_line_id = fields.Many2one(
        "recruitment.interview.template.line",
        string="Source Template Line",
        ondelete="set null",
    )

    @api.constrains("display_type", "label", "question_text")
    def _check_line_content(self):
        for rec in self:
            if rec.display_type == "question" and not (rec.question_text or rec.label):
                raise exceptions.ValidationError(_("Dong kieu Question bat buoc co noi dung."))
            if rec.display_type in ("section", "subheader") and not (rec.label or rec.question_text):
                raise exceptions.ValidationError(_("Dong tieu de bat buoc co Label."))

    def _normalize_vals_with_section(self, vals):
        normalized = dict(vals)
        section_id = normalized.get("section_id")
        if not section_id:
            return normalized

        section = self.env["hr.job.interview.config.section"].browse(section_id)
        if section and section.job_id and not normalized.get("job_id"):
            normalized["job_id"] = section.job_id.id

        display_type = normalized.get("display_type")
        if display_type in ("section", "subheader") and normalized.get("question_text") and not normalized.get("label"):
            normalized["label"] = normalized.get("question_text")
        if display_type == "question" and normalized.get("label") and not normalized.get("question_text"):
            normalized["question_text"] = normalized.get("label")

        return normalized

    @api.model_create_multi
    def create(self, vals_list):
        normalized_vals = [self._normalize_vals_with_section(vals) for vals in vals_list]
        return super().create(normalized_vals)

    def write(self, vals):
        vals = self._normalize_vals_with_section(vals)
        return super().write(vals)
