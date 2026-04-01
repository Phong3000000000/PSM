# -*- coding: utf-8 -*-
from odoo import models, fields, api


class PlanningSlotExt(models.Model):
    """
    Mở rộng planning.slot để thêm các trường cho workflow đăng ký
    Thêm mail.thread để hỗ trợ notification và activity
    """
    _name = 'planning.slot'
    _inherit = ['planning.slot', 'mail.thread', 'mail.activity.mixin']
    
    period_id = fields.Many2one(
        'planning.period',
        string='Kỳ đăng ký',
        ondelete='set null',
        index=True
    )
    
    sequence = fields.Integer(string='Thứ tự', default=10)
    is_active = fields.Boolean(string='Đang hoạt động', default=True)
    
    store_id = fields.Many2one(
        'hr.department', 
        string='Cửa hàng (Áp dụng)',
        help='Nếu để trống, mẫu này áp dụng cho tất cả cửa hàng.'
    )
    
    max_capacity = fields.Integer(
        string='Số người tối đa',
        default=1,
        help='Số nhân viên tối đa có thể đăng ký ca này'
    )
    
    approval_state = fields.Selection([
        ('open', 'Còn chỗ'),
        ('to_approve', 'Chờ duyệt'),
        ('approved', 'Đã duyệt'),
        ('rejected', 'Từ chối'),
    ], default='open', string='Trạng thái duyệt', tracking=True)
    
    registered_by = fields.Many2one(
        'res.users',
        string='Người đăng ký',
        help='Portal user đã đăng ký ca này'
    )
    registered_date = fields.Datetime(
        string='Ngày đăng ký',
        readonly=True
    )
    
    reject_reason = fields.Text(
        string='Lý do từ chối'
    )
    
    store_id = fields.Many2one(
        'hr.department',
        string='Cửa hàng',
        help='Cửa hàng (Phòng ban) của ca làm việc này'
    )
    
    def get_shift_type(self):
        """Helper xác định loại ca (Sáng/Chiều/Tối) dựa vào giờ bắt đầu"""
        self.ensure_one()
        if not self.start_datetime:
            return 'morning'
        hour = self.start_datetime.hour
        if 5 <= hour < 13:
            return 'morning'
        elif 13 <= hour < 21:
            return 'afternoon'
        else:
            return 'night'
    
    def action_approve(self):
        """RGM duyệt ca đã đăng ký"""
        for slot in self:
            if slot.approval_state == 'to_approve':
                slot.approval_state = 'approved'
                # Gửi notification cho nhân viên
                if slot.resource_id and slot.resource_id.user_id:
                    slot.message_post(
                        body='Ca làm việc của bạn đã được duyệt!',
                        partner_ids=[slot.resource_id.user_id.partner_id.id],
                        message_type='notification'
                    )
    
    def action_reject(self):
        """RGM từ chối ca đã đăng ký - Mở lại cho người khác"""
        for slot in self:
            if slot.approval_state == 'to_approve':
                # Lưu thông tin nhân viên bị từ chối để gửi notification
                rejected_user = slot.registered_by
                rejected_employee = slot.resource_id
                
                # Reset slot cho người khác đăng ký
                slot.write({
                    'approval_state': 'open',  # Mở lại để đăng ký
                    'resource_id': False,
                    'registered_by': False,
                    'registered_date': False,
                })
                
                # Gửi notification cho nhân viên bị từ chối
                if rejected_user and rejected_user.partner_id:
                    slot.message_post(
                        body='Ca làm việc của bạn (%s - %s) đã bị từ chối. Lý do: %s' % (
                            slot.start_datetime.strftime('%d/%m/%Y %H:%M'),
                            slot.end_datetime.strftime('%H:%M'),
                            slot.reject_reason or 'Không có lý do cụ thể'
                        ),
                        partner_ids=[rejected_user.partner_id.id],
                        message_type='notification'
                    )
    
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('period_id'):
                period = self.env['planning.period'].browse(vals['period_id'])
                if period.state == 'open':
                    vals['state'] = 'published'
        return super().create(vals_list)

    def write(self, vals):
        if vals.get('period_id'):
            period = self.env['planning.period'].browse(vals['period_id'])
            if period.state == 'open':
                vals['state'] = 'published'
        return super().write(vals)

    def action_reopen(self):
        """Mở lại slot cho đăng ký"""
        for slot in self:
            slot.write({
                'approval_state': 'open',
                'resource_id': False,
                'registered_by': False,
                'registered_date': False,
            })

