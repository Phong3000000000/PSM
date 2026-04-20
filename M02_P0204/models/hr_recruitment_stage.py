# -*- coding: utf-8 -*-
from odoo import models, fields, api
import logging

_logger = logging.getLogger(__name__)


class HrRecruitmentStage(models.Model):
    _inherit = 'hr.recruitment.stage'
    
    recruitment_type = fields.Selection([
        ('office', 'RST'),
        ('staff', 'OPS (Nhân viên)'),
        ('management', 'OPS (Quản lý)'),
    ], string="Áp Dụng Cho", default='staff', required=True,
       help="Nhóm pipeline áp dụng stage này")

    office_pipeline_visible = fields.Boolean(
        string="Hiển thị trên pipeline Office",
        default=True,
        help="Bỏ chọn để stage không còn xuất hiện trong pipeline tuyển dụng khối văn phòng.",
    )

    @api.model
    def _x_psm_resolve_cleanup_fallback_stage(self, applicant, deleting_stage_ids):
        """Resolve fallback stage before deleting obsolete stages."""
        stage_model = self.with_context(active_test=False)
        job_scope_domain = []
        if applicant.job_id:
            job_scope_domain = [
                '|',
                ('job_ids', '=', False),
                ('job_ids', '=', applicant.job_id.id),
            ]

        if applicant.recruitment_type == 'store' and applicant.position_level == 'staff':
            target = self.env.ref('M02_P0204.stage_staff_interview_oje', raise_if_not_found=False)
            if target and target.id not in deleting_stage_ids:
                return target
            target = stage_model.search(job_scope_domain + [
                ('name', '=', 'Interview & OJE'),
                ('recruitment_type', '=', 'staff'),
                ('id', 'not in', deleting_stage_ids),
            ], order='sequence asc', limit=1)
            if target:
                return target

        if applicant.recruitment_type == 'store' and applicant.position_level == 'management':
            target = self.env.ref('M02_P0204.stage_mgmt_interview', raise_if_not_found=False)
            if target and target.id not in deleting_stage_ids:
                return target
            target = stage_model.search(job_scope_domain + [
                ('name', '=', 'Interview'),
                ('recruitment_type', '=', 'management'),
                ('id', 'not in', deleting_stage_ids),
            ], order='sequence asc', limit=1)
            if target:
                return target

        stage_type = False
        if hasattr(applicant, '_get_pipeline_stage_type'):
            stage_type = applicant._get_pipeline_stage_type()
        if not stage_type:
            return stage_model.browse()

        if stage_type == 'office':
            office_screening = self.env.ref('M02_P0205.stage_office_screening', raise_if_not_found=False)
            if office_screening and office_screening.id not in deleting_stage_ids:
                return office_screening

        domain = [
            ('id', 'not in', deleting_stage_ids),
            ('fold', '=', False),
        ]
        domain = job_scope_domain + domain
        domain.append(('recruitment_type', '=', stage_type))
        if stage_type == 'office':
            domain.extend([
                '|',
                ('office_pipeline_visible', '=', True),
                ('recruitment_type', '!=', 'office'),
            ])
        fallback = stage_model.search(domain, order='sequence asc', limit=1)
        if fallback:
            return fallback

        return stage_model.search(job_scope_domain + [
            ('id', 'not in', deleting_stage_ids),
            ('recruitment_type', '=', stage_type),
        ], order='sequence asc', limit=1)

    @api.model
    def _auto_cleanup_redundant_stages(self):
        """Xóa cứng stage thừa khi install/upgrade.

        Chỉ cleanup các stage legacy không còn dùng trong contract 3 family.
        """
        TO_DELETE = [
            # New thừa cho staff / management
            ('New', 'staff'),
            ('New', 'management'),
            # Survey Passed thừa cho OPS flow hiện tại
            ('Survey Passed', 'staff'),
            ('Survey Passed', 'management'),
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
        action = self.env.ref('M02_P0204.action_migrate_and_clean_stages', raise_if_not_found=False)
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
