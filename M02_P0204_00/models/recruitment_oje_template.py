# -*- coding: utf-8 -*-
from odoo import models, fields, api, exceptions, _


class RecruitmentOjeTemplate(models.Model):
    _name = "recruitment.oje.template"
    _description = "Recruitment OJE Default Template"
    _order = "scope, id desc"

    name = fields.Char(string="Template Name", required=True)
    scope = fields.Selection(
        [
            ("store_staff", "Store Staff"),
            ("store_management", "Store Management"),
        ],
        string="Scope",
        required=True,
        index=True,
    )
    active = fields.Boolean(default=True)
    version = fields.Char(string="Version", default="1.0")
    intro_html = fields.Html(string="Intro")

    section_ids = fields.One2many(
        "recruitment.oje.template.section",
        "template_id",
        string="Sections",
    )

    @api.constrains("scope", "active")
    def _check_single_active_template_per_scope(self):
        for rec in self.filtered("active"):
            dup_count = self.search_count([
                ("id", "!=", rec.id),
                ("scope", "=", rec.scope),
                ("active", "=", True),
            ])
            if dup_count:
                raise exceptions.ValidationError(
                    _("Mỗi scope chỉ được có một template OJE đang hoạt động.")
                )

    def action_preview_oje_form(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_url",
            "name": _("Preview OJE Form"),
            "url": f"/recruitment/oje/template-preview/{self.id}",
            "target": "new",
        }


class RecruitmentOjeTemplateSection(models.Model):
    _name = "recruitment.oje.template.section"
    _description = "Recruitment OJE Default Template Section"
    _order = "sequence, id"

    template_id = fields.Many2one(
        "recruitment.oje.template",
        string="Template",
        required=True,
        ondelete="cascade",
    )
    scope = fields.Selection(related="template_id.scope", store=True, readonly=True)

    name = fields.Char(string="Section Title", required=True)
    sequence = fields.Integer(default=10)
    section_kind = fields.Selection(
        [
            ("staff_block", "Staff Block"),
            ("management_dimension", "Management Dimension"),
            ("management_xfactor", "Management X-Factor"),
        ],
        string="Section Kind",
        required=True,
    )
    objective_text = fields.Text(string="Objective")
    hint_html = fields.Html(string="Hints")
    behavior_html = fields.Html(string="Behavior Checklist")
    is_active = fields.Boolean(default=True)

    line_ids = fields.One2many(
        "recruitment.oje.template.line",
        "section_id",
        string="Lines",
    )
    line_count = fields.Integer(
        string="Question Count",
        compute="_compute_line_count",
    )

    @api.depends("line_ids", "line_ids.active")
    def _compute_line_count(self):
        for rec in self:
            rec.line_count = len(rec.line_ids.filtered("active"))


class RecruitmentOjeTemplateLine(models.Model):
    _name = "recruitment.oje.template.line"
    _description = "Recruitment OJE Default Template Line"
    _order = "sequence, id"

    section_id = fields.Many2one(
        "recruitment.oje.template.section",
        string="Section",
        required=True,
        ondelete="cascade",
    )
    template_id = fields.Many2one(
        related="section_id.template_id",
        store=True,
        readonly=True,
    )
    scope = fields.Selection(related="section_id.scope", store=True, readonly=True)

    sequence = fields.Integer(default=10)
    line_kind = fields.Selection(
        [
            ("staff_question", "Staff Question"),
            ("management_task", "Management Task"),
            ("management_xfactor", "Management X-Factor"),
        ],
        string="Line Kind",
        required=True,
    )
    question_text = fields.Text(string="Question / Task", required=True)
    is_required = fields.Boolean(default=True)
    active = fields.Boolean(default=True)

    @api.model_create_multi
    def create(self, vals_list):
        normalized_vals = []
        for vals in vals_list:
            normalized = dict(vals)
            section_id = normalized.get("section_id")
            if section_id and not normalized.get("line_kind"):
                section = self.env["recruitment.oje.template.section"].browse(section_id)
                if section.section_kind == "staff_block":
                    normalized["line_kind"] = "staff_question"
                elif section.section_kind == "management_dimension":
                    normalized["line_kind"] = "management_task"
                elif section.section_kind == "management_xfactor":
                    normalized["line_kind"] = "management_xfactor"
            normalized_vals.append(normalized)
        return super().create(normalized_vals)
