# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError

class ApprovalRequest(models.Model):
    _inherit = 'approval.request'

    referral_request_id = fields.Many2one(
        'employee.referral.program',
        string='Chương trình giới thiệu liên kết',
        readonly=True
    )

    # ── Computed fields from the request owner's employee profile ──────────
    owner_job_id = fields.Many2one(
        'hr.job',
        compute='_compute_owner_info', store=True,
        string='Chức vụ', readonly=True
    )
    owner_store_id = fields.Many2one(
        'hr.department',
        compute='_compute_owner_info', store=True,
        string='Cửa hàng / Phòng ban', readonly=True
    )

    @api.depends('request_owner_id')
    def _compute_owner_info(self):
        for rec in self:
            emp = rec.request_owner_id.employee_id
            rec.owner_job_id = emp.job_id if emp else False
            rec.owner_store_id = emp.department_id if emp else False

    # ── Selectable session – filtered by owner's department ───────────────
    owner_session_id = fields.Many2one(
        'mcd.recruitment.session',
        string='Đợt tuyển dụng',
        domain="[('store_id', '=', owner_store_id)]"
    )

    # ── Referral campaign dates ────────────────────────────────────────────
    referral_date_start = fields.Date(string='Ngày bắt đầu')
    referral_date_end = fields.Date(string='Ngày kết thúc')

    # ── Candidate count for smart button ────────────────────────────────────
    submission_count = fields.Integer(
        string='Ứng viên',
        compute='_compute_submission_count',
    )

    def _compute_submission_count(self):
        for rec in self:
            if rec.referral_request_id:
                rec.submission_count = self.env['employee.referral.submission'].sudo().search_count([
                    ('program_id', '=', rec.referral_request_id.id)
                ])
            else:
                rec.submission_count = 0

    # ── Standalone position lines (editable, auto-filled from session) ──────
    approval_position_ids = fields.One2many(
        'approval.request.position', 'approval_id',
        string='Vị trí tuyển dụng'
    )

    @api.onchange('owner_session_id')
    def _onchange_owner_session_id(self):
        """Auto-fill positions and dates from the selected recruitment session."""
        self.approval_position_ids = [(5, 0, 0)]
        if self.owner_session_id:
            session = self.owner_session_id
            # Auto-fill dates from session
            self.referral_date_start = getattr(session, 'date_start', False) or getattr(session, 'start_date', False)
            self.referral_date_end = getattr(session, 'date_end', False) or getattr(session, 'end_date', False)
            # Auto-fill positions from session lines
            new_lines = []
            for line in session.line_ids:
                new_lines.append((0, 0, {
                    'job_id': line.job_id.id,
                    'job_type': line.job_type,
                    'quantity': line.target_qty,
                    'bonus_amount': line.bonus,
                    'wage': line.salary,
                    'note': line.note,
                }))
            self.approval_position_ids = new_lines

    # ── Mirror fields from linked Referral Program ─────────────────────────
    referral_store_id = fields.Many2one(
        'hr.department', related='referral_request_id.store_id',
        string='Cửa hàng (RR)', readonly=False)
    referral_recruitment_session_id = fields.Many2one(
        'mcd.recruitment.session', related='referral_request_id.recruitment_session_id',
        string='Đợt tuyển dụng (RR)', readonly=False)
    referral_rgm_id = fields.Many2one(
        'res.users', related='referral_request_id.rgm_id',
        string='Restaurant General Manager', readonly=False)
    referral_oc_id = fields.Many2one(
        'res.users', related='referral_request_id.oc_id',
        string='Người duyệt (OC)', readonly=True)
    referral_description = fields.Html(
        related='referral_request_id.description',
        string='Mô tả yêu cầu', readonly=False)
    referral_line_ids = fields.One2many(
        'employee.referral.request.line', related='referral_request_id.request_line_ids',
        string='Chi tiết vị trí', readonly=False)

    def action_confirm(self):
        """Validate at least one approver before submitting."""
        for req in self:
            if not req.approver_ids:
                raise UserError(_('Chưa chọn người duyệt. Vui lòng thêm ít nhất một người phê duyệt trước khi gửi.'))
        return super().action_confirm()

    def action_view_referral_submissions(self):
        """Smart button: open submissions linked to this approval's referral program."""
        self.ensure_one()
        program = self.sudo().referral_request_id
        return {
            'type': 'ir.actions.act_window',
            'name': 'Ứng viên',
            'res_model': 'employee.referral.submission',
            'view_mode': 'list,form',
            'domain': [('program_id', '=', program.id)] if program else [],
        }

    def action_approve(self, approver=None):
        """Handle approval: Map back to the referral program state,
        or auto-create a new referral program in 'approved' state."""
        res = super().action_approve(approver=approver)
        for request in self:
            if request.request_status != 'approved':
                continue

            if request.referral_request_id:
                # Flow cũ: approval được tạo từ form referral → sync state
                request.referral_request_id.action_oc_approve()
            else:
                # Flow mới: approval tạo trực tiếp → tự tạo chương trình đã duyệt
                # Lấy config tiền thưởng cho store
                config = self.env['employee.referral.config'].sudo().get_config(
                    request.owner_store_id.id if request.owner_store_id else None
                )
                config_bonus = config.bonus_amount if config else 0

                line_vals = []
                for pos in request.approval_position_ids:
                    # Bonus: LUÔN lấy từ config theo level của hr.job
                    bonus = 0
                    if config and pos.job_id:
                        job_level = pos.job_id.level if 'level' in pos.job_id._fields else False
                        if job_level:
                            tier = config.bonus_tier_ids.filtered(lambda t: t.level == job_level)
                            bonus = tier[0].bonus_amount if tier else config_bonus
                        else:
                            bonus = config_bonus
                    else:
                        bonus = config_bonus
                    # Salary: lấy từ wage, fallback sang bonus_amount (RGM có thể nhập nhầm cột)
                    salary = pos.wage or pos.bonus_amount or 0

                    line_vals.append((0, 0, {
                        'job_id': pos.job_id.id,
                        'job_type': pos.job_type or 'fulltime',
                        'positions_needed': pos.quantity or 1,
                        'bonus_override': bonus,
                        'salary': salary,
                    }))

                program = self.env['employee.referral.program'].sudo().create({
                    'name': request.name,
                    'store_id': request.owner_store_id.id,
                    'rgm_id': request.request_owner_id.id,
                    'recruitment_session_id': request.owner_session_id.id or False,
                    'state': 'approved',
                    'oc_user_id': self.env.user.id,
                    'oc_approved_date': fields.Datetime.now(),
                    'description': request.referral_description,
                    'start_date': request.referral_date_start,
                    'end_date': request.referral_date_end,
                    'line_ids': line_vals,
                })

                request.referral_request_id = program.id

                program.message_post(
                    body=_('Phê duyệt được tạo từ yêu cầu %s. HR có thể đăng tin tuyển dụng.') % request.name,
                    message_type='notification',
                )

                # Gửi thông báo Odoo cho tất cả user thuộc nhóm Referals: HR
                hr_group = self.env.ref('M02_P0202_03.group_referral_hr', raise_if_not_found=False)
                if hr_group:
                    # Dùng SQL để lấy partner_id của các user trong nhóm (Odoo 19 compatible)
                    self.env.cr.execute(
                        """
                        SELECT p.id FROM res_groups_users_rel r
                        JOIN res_users u ON u.id = r.uid
                        JOIN res_partner p ON p.id = u.partner_id
                        WHERE r.gid = %s AND u.active = true
                        """,
                        [hr_group.id]
                    )
                    partner_ids = [row[0] for row in self.env.cr.fetchall()]
                    if partner_ids:
                        program.message_notify(
                            partner_ids=partner_ids,
                            subject=_('Yêu cầu tạo bài đăng tuyển dụng'),
                            body=_(
                                '📢 OC <b>%s</b> vừa duyệt chương trình giới thiệu nhân sự:<br/>'
                                '<b>%s</b><br/>'
                                'Vui lòng vào Referals để tạo bài viết đăng tin tuyển dụng.'
                            ) % (self.env.user.name, program.name),
                            email_layout_xmlid='mail.mail_notification_light',
                        )
        return res

    def action_refuse(self, approver=None):
        """Handle refusal: Link back to the referral program state."""
        res = super().action_refuse(approver=approver)
        for request in self:
            if request.referral_request_id and request.request_status == 'refused':
                request.referral_request_id.write({
                    'state': 'rejected',
                    'rejection_reason': request.reason or _('Từ chối qua module Phê duyệt'),
                    'oc_user_id': self.env.user.id,
                    'oc_approved_date': fields.Datetime.now(),
                })
        return res
