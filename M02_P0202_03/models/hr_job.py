# -*- coding: utf-8 -*-
from odoo import models, fields, api


class HrJob(models.Model):
    _inherit = 'hr.job'

    referral_program_count = fields.Integer(
        string='Chương trình tuyển dụng',
        compute='_compute_referral_program_count',
    )

    def _compute_referral_program_count(self):
        for job in self:
            job.referral_program_count = self.env['employee.referral.program.line'].search_count([
                ('job_id', '=', job.id),
                ('program_id.state', '=', 'active'),
            ])

    def action_view_referral_programs(self):
        """Mở danh sách chương trình giới thiệu đang tuyển vị trí này."""
        self.ensure_one()
        program_lines = self.env['employee.referral.program.line'].search([
            ('job_id', '=', self.id),
            ('program_id.state', '=', 'active'),
        ])
        program_ids = program_lines.mapped('program_id').ids
        return {
            'type': 'ir.actions.act_window',
            'name': 'Chương trình tuyển dụng',
            'res_model': 'employee.referral.program',
            'view_mode': 'list,form',
            'domain': [('id', 'in', program_ids)],
            'context': {'default_state': 'active'},
        }
