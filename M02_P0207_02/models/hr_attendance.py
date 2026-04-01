# -*- coding: utf-8 -*-
from odoo import models, fields

class HrAttendance(models.Model):
    _inherit = 'hr.attendance'

    # Raw data from Timekeeping Machine
    x_late_minutes = fields.Integer(string='Late Minutes')
    x_early_minutes = fields.Integer(string='Early Minutes')
    x_actual_location_id = fields.Many2one('hr.work.location', string='Actual Location')
    x_food_safety_fail = fields.Boolean(string='Food Safety Fail')
    x_delivery_orders_count = fields.Integer(string='Delivery Orders')

