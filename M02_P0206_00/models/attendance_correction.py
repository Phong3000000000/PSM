# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class AttendanceCorrection(models.Model):
    """
    Yêu cầu sửa công từ nhân viên
    Giới hạn tối đa 3 lần/tháng
    """
    _name = 'attendance.correction'
    _description = 'Yêu cầu sửa công'
    _order = 'create_date desc'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    employee_id = fields.Many2one(
        'hr.employee',
        string='Nhân viên',
        required=True,
        default=lambda self: self.env.user.employee_id
    )
    
    attendance_id = fields.Many2one(
        'hr.attendance',
        string='Bản ghi chấm công gốc'
    )
    
    date = fields.Date(
        string='Ngày cần sửa',
        required=True,
        default=fields.Date.today
    )
    
    # Giờ gốc (readonly, lấy từ attendance)
    original_check_in = fields.Datetime(
        string='Giờ vào gốc',
        readonly=True
    )
    original_check_out = fields.Datetime(
        string='Giờ ra gốc',
        readonly=True
    )
    
    # Giờ yêu cầu sửa
    requested_check_in = fields.Datetime(
        string='Giờ vào yêu cầu'
    )
    requested_check_out = fields.Datetime(
        string='Giờ ra yêu cầu'
    )
    
    reason = fields.Text(
        string='Lý do',
        required=True
    )
    
    state = fields.Selection([
        ('draft', 'Chờ duyệt'),
        ('approved', 'Đã duyệt'),
        ('rejected', 'Từ chối'),
    ], default='draft', string='Trạng thái', tracking=True)
    
    reject_reason = fields.Text(
        string='Lý do từ chối'
    )
    
    approved_by = fields.Many2one(
        'res.users',
        string='Người duyệt',
        readonly=True
    )
    approved_date = fields.Datetime(
        string='Ngày duyệt',
        readonly=True
    )
    
    @api.model
    def check_monthly_quota(self, employee_id):
        """
        Kiểm tra còn quota sửa công không (Max 3/tháng)
        Return: (còn_quota: bool, đã_dùng: int)
        """
        first_day = fields.Date.today().replace(day=1)
        count = self.search_count([
            ('employee_id', '=', employee_id),
            ('create_date', '>=', first_day),
        ])
        return count < 3, count
    
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            employee_id = vals.get('employee_id') or self.env.user.employee_id.id
            has_quota, count = self.check_monthly_quota(employee_id)
            if not has_quota:
                raise UserError(
                    _('Bạn đã hết lượt sửa công trong tháng này (%s/3). '
                      'Vui lòng gặp trực tiếp RGM để giải quyết.') % count
                )
        return super().create(vals_list)
    
    def action_approve(self):
        """RGM duyệt yêu cầu sửa công"""
        self.ensure_one()
        if self.state != 'draft':
            raise UserError(_('Chỉ có thể duyệt yêu cầu đang chờ!'))
        
        # Cập nhật hr.attendance nếu có
        if self.attendance_id:
            update_vals = {}
            if self.requested_check_in:
                update_vals['check_in'] = self.requested_check_in
            if self.requested_check_out:
                update_vals['check_out'] = self.requested_check_out
            if update_vals:
                self.attendance_id.write(update_vals)
        
        self.write({
            'state': 'approved',
            'approved_by': self.env.uid,
            'approved_date': fields.Datetime.now(),
        })
        
        # Notify nhân viên
        if self.employee_id.user_id:
            self.message_post(
                body=_('Yêu cầu sửa công của bạn đã được duyệt.'),
                partner_ids=[self.employee_id.user_id.partner_id.id],
                message_type='notification'
            )
    
    def action_reject(self):
        """RGM từ chối yêu cầu sửa công"""
        self.ensure_one()
        if self.state != 'draft':
            raise UserError(_('Chỉ có thể từ chối yêu cầu đang chờ!'))
        
        self.state = 'rejected'
        
        # Notify nhân viên
        if self.employee_id.user_id:
            self.message_post(
                body=_('Yêu cầu sửa công của bạn đã bị từ chối. Lý do: %s') % (self.reject_reason or 'Không có'),
                partner_ids=[self.employee_id.user_id.partner_id.id],
                message_type='notification'
            )

