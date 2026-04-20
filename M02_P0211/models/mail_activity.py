# -*- coding: utf-8 -*-
from odoo import models, fields, api

class MailActivity(models.Model):
    _inherit = 'mail.activity'

    def action_done(self):
        """Khi người dùng bấm Xong từ đồng hồ/chatter -> Tự gạt cần gạt trong hồ sơ nhân viên."""
        # Tìm các Task Onboarding liên quan
        onboarding_tasks = self.env['x_psm.hr.employee.onboarding.task'].sudo().search([
            ('x_psm_activity_id', 'in', self.ids),
            ('x_psm_is_done', '=', False)
        ])
        # Tìm các Task Đào tạo liên quan
        training_tasks = self.env['x_psm.hr.employee.training.task'].sudo().search([
            ('x_psm_activity_id', 'in', self.ids),
            ('x_psm_is_done', '=', False)
        ])

        # Đánh dấu Xong cho các Task (Dùng context để tránh bị vòng lặp logic ngược lại)
        if onboarding_tasks:
            onboarding_tasks.with_context(skip_activity_done=True).write({'x_psm_is_done': True})
        if training_tasks:
            training_tasks.with_context(skip_activity_done=True).write({'x_psm_is_done': True})

        return super(MailActivity, self).action_done()
