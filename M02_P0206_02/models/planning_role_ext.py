# -*- coding: utf-8 -*-
from odoo import models, fields


class PlanningRoleExt(models.Model):
    """
    Mở rộng planning.role để liên kết với workforce.station
    Cho phép mapping role → station cho VLH Engine skill filtering
    """
    _inherit = 'planning.role'
    
    station_id = fields.Many2one(
        'workforce.station',
        string='Trạm làm việc',
        help='Liên kết Role với Trạm để áp dụng skill filtering'
    )
