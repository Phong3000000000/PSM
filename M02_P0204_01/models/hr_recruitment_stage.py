# -*- coding: utf-8 -*-
from odoo import models, fields, api

class HrRecruitmentStage(models.Model):
    _inherit = 'hr.recruitment.stage'
    
    recruitment_type = fields.Selection([
        ('store', 'Khối Cửa Hàng'),
        ('office', 'Khối Văn Phòng'),
        ('both', 'Cả Hai'),
    ], string="Áp Dụng Cho", default='both', required=True,
       help="Loại tuyển dụng áp dụng stage này")
