# -*- coding: utf-8 -*-
from odoo import models, fields, api


class HrJobOjeConfigSection(models.Model):
    _name = 'hr.job.oje.config.section'
    _description = 'Job OJE Configuration Section'
    _order = 'sequence, id'

    job_id = fields.Many2one('hr.job', string='Job Position', ondelete='cascade', required=True)
    sequence = fields.Integer(string='Sequence', default=10)
    is_active = fields.Boolean(string='Active', default=True)

    name = fields.Char(string='Section Title', required=True)
    section_kind = fields.Selection([
        ('staff_block', 'Staff Block'),
        ('management_dimension', 'Management Dimension'),
        ('management_xfactor', 'Management X-Factor'),
        ('legacy', 'Legacy'),
    ], string='Section Kind', default='staff_block', required=True)

    objective_text = fields.Text(string='Objective')
    hint_html = fields.Html(string='Hints')
    behavior_html = fields.Html(string='Behavior Checklist')

    scope = fields.Selection([
        ('store_staff', 'Store Staff'),
        ('store_management', 'Store Management'),
    ], string='Scope')

    rating_mode = fields.Selection([
        ('staff_matrix', 'Staff Matrix NI/GD/EX/OS'),
        ('management_1_5', 'Management Score 1..5'),
        ('xfactor_yes_no', 'X-Factor Yes/No'),
        ('legacy_generic', 'Legacy Generic'),
    ], string='Rating Mode', default='legacy_generic')

    is_from_master = fields.Boolean(string='From Master Template', default=False)
    source_template_section_id = fields.Many2one(
        'recruitment.oje.template.section',
        string='Source Template Section',
        ondelete='set null',
    )

    line_ids = fields.One2many(
        'hr.job.oje.config.line',
        'section_id',
        string='Lines',
    )
    line_count = fields.Integer(
        string='Question Count',
        compute='_compute_line_count',
    )

    @api.depends('line_ids', 'line_ids.is_active')
    def _compute_line_count(self):
        for rec in self:
            rec.line_count = len(rec.line_ids.filtered('is_active'))


class HrJobOjeConfigLine(models.Model):
    _name = 'hr.job.oje.config.line'
    _description = 'OJE Configuration Line'
    _order = 'sequence, id'

    job_id = fields.Many2one('hr.job', string='Job Position', ondelete='cascade', required=True)
    section_id = fields.Many2one(
        'hr.job.oje.config.section',
        string='Section',
        ondelete='cascade',
    )

    sequence = fields.Integer(string='Sequence', default=10)
    is_active = fields.Boolean(string='Active', default=True)

    scope = fields.Selection([
        ('store_staff', 'Store Staff'),
        ('store_management', 'Store Management'),
    ], string='Scope')

    line_kind = fields.Selection([
        ('legacy', 'Legacy'),
        ('staff_question', 'Staff Question'),
        ('management_task', 'Management Task'),
        ('management_xfactor', 'Management X-Factor'),
    ], string='Line Kind', default='legacy', required=True)

    rating_mode = fields.Selection([
        ('staff_matrix', 'Staff Matrix NI/GD/EX/OS'),
        ('management_1_5', 'Management Score 1..5'),
        ('xfactor_yes_no', 'X-Factor Yes/No'),
        ('legacy_generic', 'Legacy Generic'),
    ], string='Rating Mode', default='legacy_generic')

    is_from_master = fields.Boolean(string='From Master Template', default=False)
    source_template_line_id = fields.Many2one(
        'recruitment.oje.template.line',
        string='Source Template Line',
        ondelete='set null',
    )

    question_text = fields.Text(string='Question / Task')
    name = fields.Char(string='Criterion Label', required=True)

    field_type = fields.Selection([
        ('text', 'Text (Comment + Manual Score)'),
        ('radio', 'Radio (Select one)'),
        ('checkbox', 'Checkbox (Yes/No)'),
    ], string='Field Type', default='text', required=True)
    is_required = fields.Boolean(string='Required', default=True)
    
    col_size = fields.Selection([
        ('12', '1 Hàng (1/1)'),
        ('6', 'Nửa hàng (1/2)')
    ], string='Chiều rộng cột (Portal)', default='6', help='Chỉ định chiều rộng của cột lựa chọn trên Portal')

    text_max_score = fields.Float(string='Max Score (Text)', default=5.0)
    checkbox_score = fields.Float(string='Score (Checkbox)', default=1.0)
    
    option_ids = fields.One2many('hr.job.oje.config.option', 'line_id', string='Options')

    def _derive_line_kind_from_section(self, section):
        mapping = {
            'staff_block': 'staff_question',
            'management_dimension': 'management_task',
            'management_xfactor': 'management_xfactor',
        }
        return mapping.get(section.section_kind)

    def _derive_field_type_from_line_kind(self, line_kind):
        mapping = {
            'staff_question': 'radio',
            'management_task': 'text',
            'management_xfactor': 'checkbox',
        }
        return mapping.get(line_kind)

    def _normalize_vals_with_section(self, vals):
        normalized = dict(vals)
        section_id = normalized.get('section_id')
        if not section_id:
            return normalized

        section = self.env['hr.job.oje.config.section'].browse(section_id)
        if not normalized.get('job_id'):
            normalized['job_id'] = section.job_id.id

        if section.scope and not normalized.get('scope'):
            normalized['scope'] = section.scope
        if section.rating_mode and (not normalized.get('rating_mode') or normalized.get('rating_mode') == 'legacy_generic'):
            normalized['rating_mode'] = section.rating_mode

        derived_line_kind = self._derive_line_kind_from_section(section)
        if derived_line_kind and (not normalized.get('line_kind') or normalized.get('line_kind') == 'legacy'):
            normalized['line_kind'] = derived_line_kind

        if not normalized.get('field_type'):
            auto_field_type = self._derive_field_type_from_line_kind(normalized.get('line_kind'))
            if auto_field_type:
                normalized['field_type'] = auto_field_type

        if normalized.get('question_text') and not normalized.get('name'):
            normalized['name'] = normalized.get('question_text')
        elif normalized.get('name') and not normalized.get('question_text'):
            normalized['question_text'] = normalized.get('name')

        return normalized

    @api.model_create_multi
    def create(self, vals_list):
        normalized_vals = [self._normalize_vals_with_section(vals) for vals in vals_list]
        return super().create(normalized_vals)

    def write(self, vals):
        vals = self._normalize_vals_with_section(vals)

        if vals.get('name') and 'question_text' not in vals:
            vals['question_text'] = vals.get('name')
        elif vals.get('question_text') and 'name' not in vals:
            vals['name'] = vals.get('question_text')

        return super().write(vals)

    def action_open_options(self):
        """Dummy method kept to prevent ParseError during module upgrade.
        (Odoo validates old views in DB before applying new XML that removes the button)"""
        pass

class HrJobOjeConfigOption(models.Model):
    _name = 'hr.job.oje.config.option'
    _description = 'OJE Configuration Option'
    _order = 'sequence, id'

    line_id = fields.Many2one('hr.job.oje.config.line', string='Config Line', ondelete='cascade', required=True)
    sequence = fields.Integer(string='Sequence', default=10)
    name = fields.Char(string='Option Name', required=True)
    value = fields.Char(string='Option Value', required=True)
    score = fields.Float(string='Score', default=0.0)
