# -*- coding: utf-8 -*-
from odoo import models, fields, api

class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    job_grade_id = fields.Many2one('hr.job.grade', string='Job Grade', groups='hr.group_hr_user')
    job_level_id = fields.Many2one('hr.job.level', string='Job Level', groups='hr.group_hr_user')

    @api.onchange('job_level_id')
    def _onchange_job_level_id(self):
        if self.job_level_id:
            self.job_grade_id = self.job_level_id.grade_id
    
