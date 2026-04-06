# -*- coding: utf-8 -*-
from odoo import api, exceptions, fields, models, _


class RecruitmentInterviewTemplate(models.Model):
    _name = "recruitment.interview.template"
    _description = "Recruitment Interview Default Template"
    _order = "id desc"

    name = fields.Char(string="Template Name", required=True)
    version = fields.Char(string="Version", default="1.0")
    active = fields.Boolean(default=True)
    intro_html = fields.Html(string="Intro")
    section_ids = fields.One2many(
        "recruitment.interview.template.section",
        "template_id",
        string="Sections",
    )

    @api.constrains("active")
    def _check_single_active_template(self):
        for rec in self.filtered("active"):
            duplicate = self.search_count([
                ("id", "!=", rec.id),
                ("active", "=", True),
            ])
            if duplicate:
                raise exceptions.ValidationError(_("Chi duoc phep mot template Interview dang active."))

    def action_preview_interview_form(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_url",
            "name": _("Preview Interview Form"),
            "url": f"/recruitment/interview/template-preview/{self.id}",
            "target": "new",
        }


class RecruitmentInterviewTemplateSection(models.Model):
    _name = "recruitment.interview.template.section"
    _description = "Recruitment Interview Default Template Section"
    _order = "sequence, id"

    template_id = fields.Many2one(
        "recruitment.interview.template",
        string="Template",
        required=True,
        ondelete="cascade",
    )
    name = fields.Char(string="Section Title", required=True)
    sequence = fields.Integer(default=10)
    is_active = fields.Boolean(default=True)

    line_ids = fields.One2many(
        "recruitment.interview.template.line",
        "section_id",
        string="Lines",
    )
    line_count = fields.Integer(string="Question Count", compute="_compute_line_count")

    @api.depends("line_ids", "line_ids.is_active")
    def _compute_line_count(self):
        for rec in self:
            rec.line_count = len(rec.line_ids.filtered(lambda line: line.is_active and line.display_type == "question"))


class RecruitmentInterviewTemplateLine(models.Model):
    _name = "recruitment.interview.template.line"
    _description = "Recruitment Interview Default Template Line"
    _order = "sequence, id"

    section_id = fields.Many2one(
        "recruitment.interview.template.section",
        string="Section",
        required=True,
        ondelete="cascade",
    )
    template_id = fields.Many2one(related="section_id.template_id", store=True, readonly=True)

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

    @api.constrains("display_type", "label", "question_text")
    def _check_line_content(self):
        for rec in self:
            if rec.display_type == "question" and not (rec.question_text or rec.label):
                raise exceptions.ValidationError(_("Dong kieu Question bat buoc co noi dung."))
            if rec.display_type in ("section", "subheader") and not (rec.label or rec.question_text):
                raise exceptions.ValidationError(_("Dong tieu de bat buoc co Label."))

    @api.model_create_multi
    def create(self, vals_list):
        normalized_vals = []
        for vals in vals_list:
            normalized = dict(vals)
            display_type = normalized.get("display_type") or "question"
            if display_type in ("section", "subheader") and not normalized.get("label") and normalized.get("question_text"):
                normalized["label"] = normalized.get("question_text")
            if display_type == "question" and not normalized.get("question_text") and normalized.get("label"):
                normalized["question_text"] = normalized.get("label")
            normalized_vals.append(normalized)
        return super().create(normalized_vals)

    def write(self, vals):
        vals = dict(vals)
        display_type = vals.get("display_type")
        if display_type in ("section", "subheader") and vals.get("question_text") and "label" not in vals:
            vals["label"] = vals.get("question_text")
        if display_type == "question" and vals.get("label") and "question_text" not in vals:
            vals["question_text"] = vals.get("label")
        return super().write(vals)
