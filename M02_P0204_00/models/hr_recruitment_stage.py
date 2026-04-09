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
    def _x_psm_resolve_cleanup_fallback_stage(self, applicant, deleting_stage_ids):
        """Resolve fallback stage before deleting obsolete stages."""
        stage_model = self.with_context(active_test=False)

        if applicant.recruitment_type == 'store' and applicant.position_level == 'staff':
            target = self.env.ref('M02_P0204_00.stage_staff_interview_oje', raise_if_not_found=False)
            if target and target.id not in deleting_stage_ids:
                return target
            target = stage_model.search([
                ('name', '=', 'Interview & OJE'),
                ('recruitment_type', 'in', ['staff', 'both']),
                ('id', 'not in', deleting_stage_ids),
            ], order='sequence asc', limit=1)
            if target:
                return target

        if applicant.recruitment_type == 'store' and applicant.position_level == 'management':
            target = self.env.ref('M02_P0204_00.stage_mgmt_interview', raise_if_not_found=False)
            if target and target.id not in deleting_stage_ids:
                return target
            target = stage_model.search([
                ('name', '=', 'Interview'),
                ('recruitment_type', 'in', ['management', 'both']),
                ('id', 'not in', deleting_stage_ids),
            ], order='sequence asc', limit=1)
            if target:
                return target

        office_screening = self.env.ref('M02_P0205_00.stage_office_screening', raise_if_not_found=False)
        if office_screening and office_screening.id not in deleting_stage_ids:
            return office_screening

        stage_type = False
        if hasattr(applicant, '_get_pipeline_stage_type'):
            stage_type = applicant._get_pipeline_stage_type()

        domain = [
            ('id', 'not in', deleting_stage_ids),
            ('fold', '=', False),
        ]
        if stage_type:
            domain.append(('recruitment_type', 'in', [stage_type, 'both']))
        fallback = stage_model.search(domain, order='sequence asc', limit=1)
        if fallback:
            return fallback

        return stage_model.search([
            ('id', 'not in', deleting_stage_ids),
        ], order='sequence asc', limit=1)

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
            # Survey Passed thừa cho store flow hiện tại
            ('Survey Passed', 'staff'),
            ('Survey Passed', 'management'),
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
                # Chuyển applicant sang stage hợp lệ trước khi xóa
                apps = self.env['hr.applicant'].with_context(active_test=False).search([
                    ('stage_id', 'in', stages.ids)
                ])
                if apps:
                    for applicant in apps:
                        fallback = self._x_psm_resolve_cleanup_fallback_stage(applicant, stages.ids)
                        if fallback:
                            applicant.write({'stage_id': fallback.id})

                count = len(stages)
                stages.unlink()
                deleted += count
                _logger.info("Deleted stage: '%s' (%s)", name, rtype)

        _logger.info("Cleanup done: deleted %d redundant stages", deleted)

    @api.model
    def _x_psm_archive_obsolete_stage_cleanup_server_action(self):
        """Archive obsolete manual cleanup action kept from older releases."""
        action = self.env.ref('M02_P0204_00.action_migrate_and_clean_stages', raise_if_not_found=False)
        if not action or not action.exists():
            return

        updates = {}
        # Odoo 19 ir.actions.server does not always expose `active`; keep this hook
        # schema-safe by only writing fields that exist on the model.
        if 'active' in action._fields:
            updates['active'] = False
        if 'binding_model_id' in action._fields and action.binding_model_id:
            updates['binding_model_id'] = False
        if updates:
            action.sudo().write(updates)
            _logger.info("Archived obsolete server action action_migrate_and_clean_stages")
