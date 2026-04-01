# -*- coding: utf-8 -*-

from odoo import models, fields


class HrDepartment(models.Model):
    _inherit = 'hr.department'

    shift_evaluation_ids = fields.One2many(
        'shift.evaluation',
        'department_id',
        string='Shift Evaluations'
    )

    def action_open_all_evaluations(self):
        self.ensure_one()
        return {
            'name': 'Shift Evaluations - ' + self.name,
            'type': 'ir.actions.act_window',
            'res_model': 'shift.evaluation',
            'view_mode': 'list,form',
            'domain': [('department_id', '=', self.id)],
            'context': {
                'default_department_id': self.id,
                'search_default_group_date': 1,
            },
            'target': 'current',
        }
