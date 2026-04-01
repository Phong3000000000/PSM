# -*- coding: utf-8 -*-
from odoo import models, fields, api

class HrJobOjeConfigLine(models.Model):
    _name = 'hr.job.oje.config.line'
    _description = 'OJE Configuration Line'
    _order = 'sequence, id'

    job_id = fields.Many2one('hr.job', string='Job Position', ondelete='cascade', required=True)
    sequence = fields.Integer(string='Sequence', default=10)
    is_active = fields.Boolean(string='Active', default=True)
    name = fields.Char(string='Criterion Label', required=True)
    field_type = fields.Selection([
        ('text', 'Text (Comment + Manual Score)'),
        ('radio', 'Radio (Select one)'),
        ('checkbox', 'Checkbox (Yes/No)'),
    ], string='Field Type', default='text', required=True)
    is_required = fields.Boolean(string='Required', default=True)
    
    col_size = fields.Selection([
        ('12', '1 Hàng (1/1)'),
        ('6', 'Nửa hàng (1/2)')
    ], string='Chiều rộng cột (Portal)', default='6', help='Chỉ định chiều rộng của cột lựa chọn trên Portal')

    text_max_score = fields.Float(string='Max Score (Text)', default=5.0)
    checkbox_score = fields.Float(string='Score (Checkbox)', default=1.0)
    
    option_ids = fields.One2many('hr.job.oje.config.option', 'line_id', string='Options')

    def action_open_options(self):
        """Dummy method kept to prevent ParseError during module upgrade.
        (Odoo validates old views in DB before applying new XML that removes the button)"""
        pass

class HrJobOjeConfigOption(models.Model):
    _name = 'hr.job.oje.config.option'
    _description = 'OJE Configuration Option'
    _order = 'sequence, id'

    line_id = fields.Many2one('hr.job.oje.config.line', string='Config Line', ondelete='cascade', required=True)
    sequence = fields.Integer(string='Sequence', default=10)
    name = fields.Char(string='Option Name', required=True)
    value = fields.Char(string='Option Value', required=True)
    score = fields.Float(string='Score', default=0.0)
