# -*- coding: utf-8 -*-
from odoo import models, fields

class HrWorkEntry(models.Model):
    _inherit = 'hr.work.entry'

    # --- Group 1: Time Definition ---
    x_is_holiday = fields.Boolean(string='Is Holiday')
    x_is_weekend = fields.Boolean(string='Is Weekend')
    x_shift_category = fields.Selection([
        ('normal', 'Normal'),
        ('half_night', 'Half Night'),
        ('full_night', 'Full Night')
    ], string='Shift Category', default='normal')

    # --- Group 2: Attendance Data ---
    # duration is already present in standard Odoo
    x_night_working_hours = fields.Float(string='Night Working Hours')
    x_break_deducted = fields.Boolean(string='Break Deducted')

    # --- Group 5: Context & Location ---
    # --- Group 5: Context & Location ---
    x_actual_location_id = fields.Many2one('hr.work.location', string='Actual Work Location')
    x_region_code = fields.Char(string='Region Code', related='x_actual_location_id.name', store=True)

    # --- Group 6 & 7: Variable Pay & Flags ---
    x_delivery_orders_count = fields.Integer(string='Delivery Orders Count')
    x_food_safety_fail = fields.Boolean(string='Food Safety Fail')

    # --- Group 8: Penalties ---
    x_late_minutes = fields.Integer(string='Late Minutes (Min)')
    x_early_minutes = fields.Integer(string='Early Minutes (Min)')

