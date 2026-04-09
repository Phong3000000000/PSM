# -*- coding: utf-8 -*-
from odoo import models

# x_psm_0205_recruitment_type and office_pipeline_visible are now owned by M02_P0204_00.
# This file is kept for compatibility but no longer declares those fields.


class HrRecruitmentStage(models.Model):
    _inherit = "hr.recruitment.stage"
