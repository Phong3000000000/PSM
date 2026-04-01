# -*- coding: utf-8 -*-

from odoo import models, fields


class ResCompany(models.Model):
    _inherit = 'res.company'

    shift_evaluation_ids = fields.One2many(
        'shift.evaluation',
        'company_id',
        string='Shift Evaluations'
    )

    def action_open_all_evaluations(self):
        self.ensure_one()
        return {
            'name': 'Shift Evaluations - ' + self.name,
            'type': 'ir.actions.act_window',
            'res_model': 'shift.evaluation',
            'view_mode': 'list,form',
            'domain': [('company_id', '=', self.id)],
            'context': {
                'default_company_id': self.id,
                'search_default_group_date': 1,
            },
            'target': 'current',
        }
