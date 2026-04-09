# -*- coding: utf-8 -*-
from odoo import fields, models


class HrJobLevel(models.Model):
    _inherit = 'hr.job.level'

    x_psm_0205_max_interview_round = fields.Integer(
        string='So vong phong van',
        default=2,
        help='So vong phong van toi da ap dung cho cac Job Position thuoc level nay.',
    )
