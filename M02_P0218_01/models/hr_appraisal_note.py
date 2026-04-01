# -*- coding: utf-8 -*-

from odoo import models, fields


class HrAppraisalNote(models.Model):
    _inherit = 'hr.appraisal.note'
    
    score = fields.Float(
        string='Score',
        help='Score threshold for this rating level'
    )
