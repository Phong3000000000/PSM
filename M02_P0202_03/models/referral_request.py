# -*- coding: utf-8 -*-
"""
Referral Program Extension (Request Workflow)
Extends employee.referral.program with RGM request workflow fields and approval.
(M02_P0202_03)
"""

from odoo import models, fields, api, _
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)


class ReferralRequest(models.Model):
    _inherit = 'employee.referral.program'

    # ── State extension ────────────────────────────────────────────────
    state = fields.Selection(
        selection_add=[
            ('pending_oc', 'OC Duyệt'),
            ('approved', 'OC đã duyệt'),
            ('rejected', 'OC từ chối'),
            ('published', 'Đã đăng tin'),
        ],
        ondelete={
            'pending_oc': 'set default',
            'approved': 'set default',
            'rejected': 'set default',
            'published': 'set default',
        }
    )

    # ── Request-specific fields ────────────────────────────────────────
    rgm_id = fields.Many2one(
        'res.users',
        string='Restaurant General Manager',
        default=lambda self: self.env.user,
        required=True,
        readonly=True,
        tracking=True
    )

    oc_id = fields.Many2one(
        'res.users',
        string='Người duyệt (OC)',
        compute='_compute_oc_id',
        store=True,
        tracking=True,
        help='Người quản lý trực tiếp (Line Manager) của người yêu cầu'
    )

    # Request position lines (separate from program.line_ids)
    request_line_ids = fields.One2many(
        'employee.referral.request.line',
        'program_id',
        string='Vị trí tuyển dụng (yêu cầu)'
    )

    # Recruitment session link
    recruitment_session_id = fields.Many2one(
        'mcd.recruitment.session',
        string='Đợt tuyển dụng',
        domain="[('state', 'in', ['ongoing', 'expired']), ('store_id', '=', store_id)]",
        help="Chọn đợt tuyển dụng để tự động điền danh sách vị trí"
    )

    # Approval integration
    approval_request_id = fields.Many2one(
        'approval.request',
        string='Mã phê duyệt',
        readonly=True,
        copy=False
    )

    # Approval tracking
    oc_user_id = fields.Many2one('res.users', string='OC duyệt', readonly=True, tracking=True)
    oc_approved_date = fields.Datetime(string='Ngày OC duyệt', readonly=True)
    hr_user_id = fields.Many2one('res.users', string='HR đăng tin', readonly=True, tracking=True)
    hr_published_date = fields.Datetime(string='Ngày đăng tin', readonly=True)
    rejection_reason = fields.Text(string='Lý do từ chối')

    # ── Computed ──────────────────────────────────────────────────────
    @api.depends('rgm_id')
    def _compute_oc_id(self):
        """Auto-find OC: Line Manager of the RGM requester"""
        for rec in self:
            rec.oc_id = False
            if rec.rgm_id:
                rgm_employee = self.env['hr.employee'].sudo().search([
                    ('user_id', '=', rec.rgm_id.id)
                ], limit=1)
                if rgm_employee and rgm_employee.parent_id:
                    rec.oc_id = rgm_employee.parent_id.user_id

    # ── Onchange ──────────────────────────────────────────────────────
    @api.onchange('recruitment_session_id')
    def _on_onchange_recruitment_session(self):
        if self.recruitment_session_id:
            self.store_id = self.recruitment_session_id.store_id
            self.request_line_ids = [(5, 0, 0)]
            lines = []
            for session_line in self.recruitment_session_id.line_ids:
                level_config = self.env['employee.referral.config'].sudo().get_config(
                    company_id=self.store_id.id if self.store_id else False
                )
                bonus = level_config.bonus_amount if level_config else 0
                lines.append((0, 0, {
                    'job_id': session_line.job_id.id,
                    'quantity': session_line.target_qty,
                    'job_type': session_line.job_type,
                    'date_start': session_line.date_start,
                    'date_end': session_line.date_end,
                    'wage': session_line.salary,
                    'bonus_amount': bonus,
                    'note': getattr(session_line, 'note', False),
                }))
            self.request_line_ids = lines

    # ── Create ────────────────────────────────────────────────────────
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('employee.referral.request') or _('New')
        return super().create(vals_list)

    # ── Portal ────────────────────────────────────────────────────────
    def action_open_portal(self):
        """Mở trang portal của chương trình giới thiệu này"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_url',
            'url': f'/referral/jobs/{self.id}',
            'target': 'new',
        }

    # ── Submissions ───────────────────────────────────────────────────
    def action_view_submissions(self):
        """Smart button to view submissions"""
        self.ensure_one()
        return {
            'name': _('Ứng viên giới thiệu'),
            'type': 'ir.actions.act_window',
            'res_model': 'employee.referral.submission',
            'view_mode': 'list,form',
            'domain': [('program_id', '=', self.id)],
        }

    # ── Workflow ──────────────────────────────────────────────────────
    def action_submit_to_oc(self):
        """RGM submit yêu cầu đến OC"""
        self.ensure_one()
        if not self.store_id:
            raise UserError(_('Vui lòng chọn cửa hàng!'))
        if not self.request_line_ids:
            raise UserError(_('Vui lòng thêm ít nhất một vị trí tuyển dụng!'))

        category = self.env['approval.category'].sudo().search(
            [('name', 'like', 'Phê duyệt Yêu cầu Giới thiệu Nhân sự')], limit=1
        )
        if not category:
            raise UserError(_('Không tìm thấy loại phê duyệt "Phê duyệt Yêu cầu Giới thiệu Nhân sự". Vui lòng kiểm tra lại cấu hình.'))

        table_rows = ""
        for line in self.request_line_ids:
            job_type = dict(line._fields['job_type'].selection).get(line.job_type)
            table_rows += f"""
                <tr>
                    <td style="border: 1px solid #ddd; padding: 8px;">{line.job_id.name}</td>
                    <td style="border: 1px solid #ddd; padding: 8px;">{job_type}</td>
                    <td style="border: 1px solid #ddd; padding: 8px; text-align: center;">{line.quantity}</td>
                    <td style="border: 1px solid #ddd; padding: 8px; text-align: right;">{line.bonus_amount:,} VNĐ</td>
                    <td style="border: 1px solid #ddd; padding: 8px; text-align: right;">{line.wage:,}</td>
                    <td style="border: 1px solid #ddd; padding: 8px;">{line.note or ''}</td>
                </tr>
            """

        html_reason = f"""
            <p>RGM gửi yêu cầu phát sinh giới thiệu nhân sự cho cửa hàng <b>{self.store_id.name}</b>.</p>
            <p><b>Đợt tuyển:</b> {self.recruitment_session_id.name if self.recruitment_session_id else "N/A"}</p>
            <br/>
            <table style="border-collapse: collapse; width: 100%; border: 1px solid #ddd; font-family: sans-serif;">
                <thead>
                    <tr style="background-color: #f2f2f2;">
                        <th style="border: 1px solid #ddd; padding: 8px; text-align: left;">Vị trí</th>
                        <th style="border: 1px solid #ddd; padding: 8px; text-align: left;">Loại</th>
                        <th style="border: 1px solid #ddd; padding: 8px; text-align: center;">Cần GT</th>
                        <th style="border: 1px solid #ddd; padding: 8px; text-align: right;">Thưởng</th>
                        <th style="border: 1px solid #ddd; padding: 8px; text-align: right;">Lương/h</th>
                        <th style="border: 1px solid #ddd; padding: 8px; text-align: left;">Ghi chú</th>
                    </tr>
                </thead>
                <tbody>
                    {table_rows}
                </tbody>
            </table>
            <br/>
            <p>Vui lòng xem xét và phê duyệt chương trình này.</p>
        """

        approval_vals = {
            'name': self.name,
            'category_id': category.id,
            'request_owner_id': self.env.user.id,
            'company_id': self.store_id.company_id.id if self.store_id.company_id else self.env.company.id,
            'reason': html_reason,
            'referral_request_id': self.id,
        }
        if self.oc_id:
            approval_vals['approver_ids'] = [(0, 0, {'user_id': self.oc_id.id})]

        approval = self.env['approval.request'].sudo().create(approval_vals)
        approval.sudo().action_confirm()
        self.sudo().write({
            'state': 'pending_oc',
            'approval_request_id': approval.id
        })
        _logger.info(f"Referral program {self.name} submitted to approval {approval.id}")
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Đã gửi phê duyệt!'),
                'message': _('Yêu cầu đã được gửi đến quản lý (OC) để duyệt trên module Phê duyệt.'),
                'type': 'success',
            }
        }

    def action_oc_approve(self):
        """OC approve"""
        self.ensure_one()
        self.write({
            'state': 'approved',
            'oc_user_id': self.env.user.id,
            'oc_approved_date': fields.Datetime.now(),
        })
        self.message_post(
            body=_('Đã được OC duyệt bởi %s') % self.env.user.name,
            message_type='notification'
        )
        _logger.info(f"Referral program {self.name} approved by OC {self.env.user.name}")

    def action_oc_reject(self):
        """OC reject"""
        return {
            'name': _('Lý do từ chối'),
            'type': 'ir.actions.act_window',
            'res_model': 'referral.request.reject.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_request_id': self.id}
        }

    def action_hr_publish(self):
        """HR publish via wizard"""
        self.ensure_one()
        return {
            'name': _('Tạo bài đăng'),
            'type': 'ir.actions.act_window',
            'res_model': 'referral.publish.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_request_id': self.id}
        }

    def action_close(self):
        """Close"""
        self.write({'state': 'closed'})

    # ── Notifications ─────────────────────────────────────────────────
    def _send_oc_notification(self):
        if self.oc_id:
            self.activity_schedule(
                'mail.mail_activity_data_todo',
                user_id=self.oc_id.id,
                summary=_('Duyệt yêu cầu giới thiệu nhân sự'),
                note=_('Yêu cầu %s từ %s đang chờ duyệt.') % (self.name, self.rgm_id.name),
                date_deadline=fields.Date.today()
            )

    def _send_rgm_rejection(self):
        if self.rgm_id:
            self.message_notify(
                partner_ids=[self.rgm_id.partner_id.id],
                body=_('Chương trình %s đã bị từ chối bởi OC. Lý do: %s') % (self.name, self.rejection_reason),
                subject=_('Yêu cầu bị từ chối'),
                subtype_xmlid='mail.mt_note',
            )


class ReferralRequestLine(models.Model):
    """Chi tiết vị trí tuyển dụng theo yêu cầu RGM"""
    _name = 'employee.referral.request.line'
    _description = 'Chi tiết vị trí tuyển dụng'

    program_id = fields.Many2one(
        'employee.referral.program',
        string='Chương trình',
        required=True,
        ondelete='cascade'
    )
    job_id = fields.Many2one('hr.job', string='Vị trí', required=True)
    quantity = fields.Integer(string='SL Cần giới thiệu', default=1, required=True)
    date_start = fields.Date(string='Ngày bắt đầu')
    date_end = fields.Date(string='Ngày kết thúc')
    wage = fields.Integer(string='Lương/giờ', default=0)
    bonus_amount = fields.Integer(string='Tiền thưởng', default=0)
    note = fields.Text(string='Ghi chú')
    job_type = fields.Selection([
        ('fulltime', 'Full-time'),
        ('parttime', 'Part-time')
    ], string='Loại công việc', required=True, default='fulltime')


class ReferralRequestRejectWizard(models.TransientModel):
    _name = 'referral.request.reject.wizard'
    _description = 'Wizard từ chối yêu cầu giới thiệu'

    request_id = fields.Many2one('employee.referral.program', required=True)
    rejection_reason = fields.Text(string='Lý do từ chối', required=True)

    def action_confirm_reject(self):
        self.ensure_one()
        self.request_id.write({
            'state': 'rejected',
            'rejection_reason': self.rejection_reason,
            'oc_user_id': self.env.user.id,
            'oc_approved_date': fields.Datetime.now(),
        })
        self.request_id.activity_feedback(['mail.mail_activity_data_todo'])
        self.request_id._send_rgm_rejection()
        self.request_id.message_post(
            body=_('Bị từ chối bởi %s. Lý do: %s') % (self.env.user.name, self.rejection_reason),
            message_type='notification'
        )
        return {'type': 'ir.actions.act_window_close'}
