# -*- coding: utf-8 -*-
from odoo import models, fields, api

class CreateJobTemplatesWizard(models.TransientModel):
    _name = 'create.job.templates.wizard'
    _description = 'Tạo hr.job Templates cho từng Department × Position'

    recruitment_type = fields.Selection([
        ('store', 'Khối Cửa Hàng'),
        ('office', 'Khối Văn Phòng'),
    ], string='Loại Tuyển Dụng', required=True, default='store')

    position_level = fields.Selection([
        ('management', 'Quản Lý'),
        ('staff', 'Nhân Viên'),
    ], string='Cấp Bậc', required=True)

    def action_create_templates(self):
        """No-op: Chức năng tạo template tự động đã bị gỡ bỏ theo yêu cầu."""
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Thông báo',
                'message': 'Chức năng tạo template tự động đã bị gỡ bỏ. Vui lòng sử dụng Module 200.',
                'type': 'warning',
            }
        }

    def action_create_all_templates(self):
        """No-op: Chức năng tạo template tự động đã bị gỡ bỏ theo yêu cầu."""
        return self.action_create_templates()
