# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class HrJobGrade(models.Model):
    _name = 'hr.job.grade'
    _description = 'Job Grade'
    _parent_name = 'parent_id'
    _parent_store = True
    _order = 'sequence, name'

    name = fields.Char(string='Job Grade', required=True)
    complete_name = fields.Char(
        string='Career Path',
        compute='_compute_complete_name',
        store=True,
        recursive=True,
    )
    global_grade = fields.Char(string='Global Grade')
    mercer_min = fields.Integer(string='Mercer IPE Min')
    mercer_max = fields.Integer(string='Mercer IPE Max')
    parent_id = fields.Many2one(
        'hr.job.grade',
        string='Parent Grade',
        index=True,
        ondelete='restrict',
    )
    parent_path = fields.Char(index=True)
    child_ids = fields.One2many('hr.job.grade', 'parent_id', string='Next Grades')
    child_count = fields.Integer(string='Next Grade Count', compute='_compute_child_count')
    level_ids = fields.One2many('hr.job.level', 'grade_id', string='Levels')
    level_count = fields.Integer(string='Level Count', compute='_compute_level_count')
    sequence = fields.Integer(string='Sequence', default=10)
    active = fields.Boolean(string='Active', default=True)

    def _compute_level_count(self):
        for record in self:
            record.level_count = len(record.level_ids)

    @api.depends('name', 'parent_id.complete_name')
    def _compute_complete_name(self):
        for record in self:
            if record.parent_id:
                record.complete_name = '%s / %s' % (record.parent_id.complete_name, record.name)
            else:
                record.complete_name = record.name

    def _compute_child_count(self):
        for record in self:
            record.child_count = len(record.child_ids)

    @api.constrains('parent_id')
    def _check_parent_id(self):
        if not self._check_recursion():
            raise ValidationError(_('You cannot create a recursive career path.'))

    def action_open_career_path(self):
        self.ensure_one()
        return {
            'name': _('Career Path'),
            'type': 'ir.actions.act_window',
            'res_model': 'hr.job.grade',
            'view_mode': 'list,form',
            'domain': [('id', 'child_of', self.id)],
            'context': {'default_parent_id': self.id},
            'target': 'current',
        }
