# -*- coding: utf-8 -*-
from odoo import models, fields, api
import logging

_logger = logging.getLogger(__name__)


class HrRecruitmentStage(models.Model):
    _inherit = 'hr.recruitment.stage'
    
    recruitment_type = fields.Selection([
        ('store', 'Khối Cửa Hàng'),
        ('office', 'Khối Văn Phòng'),
        ('management', 'Quản Lý'),
        ('staff', 'Nhân Viên'),
        ('both', 'Cả Hai'),
    ], string="Áp Dụng Cho", default='both', required=True,
       help="Loại tuyển dụng áp dụng stage này")

    office_pipeline_visible = fields.Boolean(
        string="Hiển thị trên pipeline Office",
        default=True,
        help="Bỏ chọn để stage không còn xuất hiện trong pipeline tuyển dụng khối văn phòng.",
    )

    candidate_email_enabled = fields.Boolean(
        string='Gửi Email tự động', default=False,
        help='Hệ thống sẽ tự động gửi email cho ứng viên khi hồ sơ chuyển sang vòng này (chỉ khi Job Position không ghi đè).'
    )
    candidate_email_template_id = fields.Many2one(
        'mail.template', string='Email Template Mặc Định',
        domain=[('model', '=', 'hr.applicant')],
        help='Mẫu email sẽ gửi cho ứng viên khi vào vòng này.'
    )

    @api.model
    def _auto_cleanup_redundant_stages(self):
        """Xóa cứng 18 stage thừa khi install/upgrade."""
        TO_DELETE = [
            # 6 stage "Cả Hai"
            ('New', 'both'),
            ('Qualification', 'both'),
            ('First Interview', 'both'),
            ('Second Interview', 'both'),
            ('Contract Proposal', 'both'),
            ('Contract Signed', 'both'),
            # New thừa cho staff / management
            ('New', 'staff'),
            ('New', 'management'),
            # Store thừa
            ('Review Tiêu chí', 'store'),
            ('Thử việc', 'store'),
            ('Đề xuất chính thức (FT/PT)', 'store'),
            ('Đề xuất chính thức', 'store'),
            ('Chính thức', 'store'),
            # Office thừa
            ('Review Tiêu chí', 'office'),
            ('Technical Test', 'office'),
            ('Thử việc', 'office'),
            ('Đề xuất chính thức', 'office'),
            ('Chính thức', 'office'),
        ]

        deleted = 0
        for name, rtype in TO_DELETE:
            stages = self.search([('name', '=', name), ('recruitment_type', '=', rtype)])
            if stages:
                # Chuyển applicant sang New (store) trước khi xóa
                apps = self.env['hr.applicant'].with_context(active_test=False).search([
                    ('stage_id', 'in', stages.ids)
                ])
                if apps:
                    fallback = self.search([
                        ('name', '=', 'New'), ('recruitment_type', '=', 'store'),
                        ('id', 'not in', stages.ids),
                    ], limit=1)
                    if fallback:
                        apps.write({'stage_id': fallback.id})

                count = len(stages)
                stages.unlink()
                deleted += count
                _logger.info("Deleted stage: '%s' (%s)", name, rtype)

        _logger.info("Cleanup done: deleted %d redundant stages", deleted)
