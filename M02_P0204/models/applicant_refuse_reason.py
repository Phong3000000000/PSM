# -*- coding: utf-8 -*-
"""
Override applicant.get.refuse.reason để đồng bộ stage_id = Reject
và x_psm_0205_document_approval_status = 'refused' sau khi wizard Refuse xác nhận.
Đồng thời gửi email từ chối tuỳ chỉnh của module 0204.
"""
from odoo import models, fields, api, exceptions
import logging

_logger = logging.getLogger(__name__)


class HrApplicantRefuseReason(models.Model):
    _inherit = 'hr.applicant.refuse.reason'

    job_id = fields.Many2one('hr.job', string='Job Position', ondelete='cascade', index=True,
                             help='Lý do từ chối gắn với vị trí tuyển dụng cụ thể.')
    reason_type = fields.Selection([
        ('checkbox', 'Checkbox (Mặc định)'),
        ('text', 'Bắt buộc nhập Lý do chi tiết')
    ], string='Loại', default='checkbox', required=True)


class ApplicantGetRefuseReasonLine(models.TransientModel):
    _name = 'x_psm_applicant_get_refuse_reason_line'
    _description = 'Dòng lý do từ chối'

    wizard_id = fields.Many2one('applicant.get.refuse.reason', string='Wizard', ondelete='cascade')
    job_refuse_reason_id = fields.Many2one('hr.applicant.refuse.reason', string='Lý do cấu hình', required=True)
    name = fields.Char(related='job_refuse_reason_id.name', string='Tiêu đề', readonly=True)
    reason_type = fields.Selection(related='job_refuse_reason_id.reason_type', readonly=True)
    
    is_selected = fields.Boolean(string='Chọn', default=False)
    custom_text = fields.Char(string='Lý do chi tiết')

    is_selected = fields.Boolean(string='Chọn', default=False)
    custom_text = fields.Char(string='Lý do chi tiết')


class ApplicantGetRefuseReason(models.TransientModel):
    _inherit = 'applicant.get.refuse.reason'

    refuse_reason_ids = fields.Many2many('hr.applicant.refuse.reason', string='Lý do từ chối (Tại vị trí)')
    source_action = fields.Selection([
        ('archive_applicant', 'Archive Applicant'),
        ('reject_stage', 'Reject Stage'),
        ('reject_survey', 'Reject Survey'),
        ('reject_documents', 'Reject Documents'),
    ], string='Hành động gốc', default='archive_applicant')

    job_id = fields.Many2one('hr.job', string='Job Position', readonly=True)
    
    wizard_line_ids = fields.One2many('x_psm_applicant_get_refuse_reason_line', 'wizard_id', string='Danh sách lý do')

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        active_ids = self.env.context.get('active_ids', [])
        if active_ids:
            applicants = self.env['hr.applicant'].browse(active_ids)
            job_ids = applicants.mapped('job_id')
            if len(job_ids) > 1:
                raise exceptions.UserError('Chỉ có thể từ chối nhiều ứng viên cùng một lúc nếu họ ứng tuyển vào cùng một vị trí.')
            if job_ids:
                res['job_id'] = job_ids[0].id
                active_reasons = self.env['hr.applicant.refuse.reason'].search([('job_id', '=', job_ids[0].id), ('active', '=', True)], order='sequence asc')
                # Nếu flow manual từ Odoo mặc định vào, user bắt buộc cấu hình lý do riêng cho Job
                if not active_reasons:
                    raise exceptions.UserError(f'Vị trí "{job_ids[0].name}" chưa được cấu hình lý do từ chối (active). Vui lòng cấu hình trước khi reject.')
                
                # Auto-fix data for legacy reasons that were created as checkbox but should be text
                for r in active_reasons:
                    if r.reason_type == 'checkbox' and any(kw in r.name.lower() for kw in ['fail phóng vấn/oje', 'lý do khác']):
                        r.reason_type = 'text'

                # Pre-populate lines
                lines = []
                for r in active_reasons:
                    lines.append((0, 0, {
                        'job_refuse_reason_id': r.id,
                        'is_selected': False,
                    }))
                res['wizard_line_ids'] = lines

        return res

    def action_refuse_reason_apply(self):
        """
        Override: gọi super() giữ toàn bộ logic Refuse mặc định,
        sau đó đồng bộ stage_id = Reject + x_psm_0205_document_approval_status = 'refused'
        + reject_reason = tên lý do từ chối
        + gửi email từ chối custom.
        """
        rejection_template = self.env.ref(
            'M02_P0204.email_rejection', raise_if_not_found=False
        )
        sys_refuse_reason = self.env.ref('M02_P0204.system_refuse_reason', raise_if_not_found=False)

        # Trỏ refuse_reason_id (bắt buộc của Odoo) về record hệ thống
        if sys_refuse_reason:
            self.refuse_reason_id = sys_refuse_reason.id

        selected_lines = self.wizard_line_ids.filtered(lambda l: l.is_selected)

        if not selected_lines:
            raise exceptions.UserError('Vui lòng chọn ít nhất một lý do từ chối.')
            
        for line in selected_lines:
            if line.reason_type == 'text' and not line.custom_text:
                raise exceptions.UserError(f'Vui lòng nhập "Lý do chi tiết" cho phần: {line.name}')

        res = super().action_refuse_reason_apply()

        applicants = self.applicant_ids
        refuse_texts = []
        selected_reason_ids = selected_lines.mapped('job_refuse_reason_id.id')
        
        for line in selected_lines:
            if line.reason_type == 'text' and line.custom_text:
                refuse_texts.append(f"{line.name}: {line.custom_text}")
            else:
                refuse_texts.append(line.name)
                
        refuse_name = " | ".join(refuse_texts)
        send_email = getattr(self, 'send_email', False)

        for rec in applicants:
            try:
                stage = rec._x_psm_resolve_stage(
                    'Reject',
                    ilike=True,
                    stage_type=rec._get_pipeline_stage_type(),
                )

                vals = {
                    'active': True,          # Restore: native Refuse archive ứng viên, cần hiển thị lại ở stage Reject
                    'x_psm_0205_document_approval_status': 'refused',
                    'reject_reason': refuse_name,
                    'refuse_reason_m2m_ids': [(6, 0, selected_reason_ids)],
                }
                if stage:
                    vals['stage_id'] = stage.id

                rec.with_context(
                    active_test=False,       # Cần truy cập cả record đã bị archive
                    skip_rejection_email=True,
                    skip_stage_email=True,   # Ensure we don't send duplicate stage email during this write
                    allow_reject_without_wizard=True,
                ).write(vals)

                _logger.info(
                    "[REFUSE_SYNC] Applicant %s synced to Reject (stage=%s, reason=%s)",
                    rec.id, stage.id if stage else None, refuse_name
                )

                # Gửi email từ chối custom (email_rejection) nếu chưa gửi qua wizard
                rejection_template = rec._get_email_template_resolution(
                    event_code="reject",
                    fallback_xml_id='M02_P0204.email_rejection'
                )

                if not send_email and rejection_template and rec.email_from:
                    try:
                        rec._send_mail_async(rejection_template, rec.id)
                        _logger.info(
                            "[REFUSE_EMAIL] Sent dynamic rejection email to applicant %s (%s)",
                            rec.id, rec.email_from
                        )
                    except Exception as mail_err:
                        _logger.warning(
                            "[REFUSE_EMAIL] Failed to send rejection email to %s: %s",
                            rec.email_from, str(mail_err)
                        )

            except Exception as e:
                _logger.warning(
                    "[REFUSE_SYNC] Failed to sync applicant %s: %s", rec.id, str(e)
                )

        return res
