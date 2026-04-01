# -*- coding: utf-8 -*-
"""
Referral Configuration
Cấu hình thưởng giới thiệu nhân sự - hỗ trợ mức thưởng theo cấp bậc (Manager/Crew)
"""

from odoo import models, fields, api, _


class ReferralConfigBonusTier(models.Model):
    _name = 'employee.referral.config.bonus.tier'
    _description = 'Mức thưởng theo cấp bậc'
    _order = 'level'

    config_id = fields.Many2one(
        'employee.referral.config',
        string='Cấu hình',
        required=True,
        ondelete='cascade'
    )
    def _get_level_selection(self):
        selection = []
        if 'level' in self.env['hr.job']._fields:
            field = self.env['hr.job']._fields['level']
            if field.selection:
                if callable(field.selection):
                    selection = field.selection(self.env['hr.job'])
                else:
                    selection = field.selection
        if not selection:
            selection = [
                ('manager', 'Quản lý (Manager)'),
                ('crew', 'Nhân viên (Crew)'),
                ('other', 'Khác'),
            ]
        return selection

    level = fields.Selection(
        selection='_get_level_selection',
        string='Cấp bậc', 
        required=True
    )

    bonus_amount = fields.Float(
        string='Số tiền thưởng (VNĐ)',
        required=True,
        default=500000
    )
    note = fields.Char(string='Ghi chú')


class ReferralConfig(models.Model):
    _name = 'employee.referral.config'
    _description = 'Cấu hình thưởng giới thiệu'
    _rec_name = 'name'

    name = fields.Char(string='Tên cấu hình', default='Cấu hình mặc định', required=True)
    company_id = fields.Many2one('res.company', string='Công ty', default=lambda self: self.env.company)
    is_default = fields.Boolean(string='Đang áp dụng', default=False, readonly=True)

    # Bonus tiers by job level
    bonus_tier_ids = fields.One2many(
        'employee.referral.config.bonus.tier',
        'config_id',
        string='Mức thưởng theo cấp bậc'
    )

    # Flat fallback bonus (if no tier matches)
    bonus_amount = fields.Float(
        string='Số tiền thưởng mặc định (VND)',
        default=100000,
        help='Số tiền thưởng mặc định cho mỗi ứng viên pass thử việc'
    )

    probation_days = fields.Integer(
        string='Số ngày thử việc',
        default=60,
        help='Số ngày thử việc trước khi xác nhận thưởng'
    )

    auto_create_payslip_input = fields.Boolean(
        string='Tự động tạo bonus trong payslip',
        default=True,
        help='Tự động tạo entry bonus trong phiếu lương khi ứng viên pass thử việc'
    )

    payslip_input_type_id = fields.Many2one(
        'hr.payslip.input.type',
        string='Loại input payslip',
        help='Input type để tạo bonus trong payslip'
    )

    active = fields.Boolean(default=True)

    announcement_channel_id = fields.Many2one(
        'discuss.channel',
        string='Kênh thông báo',
        help='Kênh để đăng bài thông báo tuyển dụng tự động'
    )

    news_blog_id = fields.Many2one(
        'blog.blog',
        string='Trang tin tức',
        help='Blog để đăng tin tuyển dụng (VD: Tin tức nội bộ)'
    )

    default_post_template = fields.Html(
        string='Nội dung bài viết mẫu',
        help='Nội dung mặc định sẽ hiện ra khi tạo Bài viết giới thiệu mới',
        default='<p>Tham gia giới thiệu ứng viên cho nhà hàng của chúng tôi để nhận phần thưởng hấp dẫn!</p>'
    )

    def action_apply(self):
        """Đặt cấu hình này làm mặc định – chỉ 1 config được áp dụng tại một thời điểm."""
        self.ensure_one()
        self.search([('id', '!=', self.id)]).write({'is_default': False})
        self.write({'is_default': True})
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Đã áp dụng!'),
                'message': _('Cấu hình "%s" đã được đặt làm mặc định.') % self.name,
                'type': 'success',
                'next': {'type': 'ir.actions.client', 'tag': 'reload'},
            }
        }

    @api.model
    def get_config(self, company_id=None, level=None):
        """
        Lấy cấu hình đang áp dụng (is_default=True).
        Nếu truyền level → trả về bonus tier tương ứng (có bonus_amount).
        Nếu không tìm thấy tier → trả về config chính (cũng có bonus_amount).
        """
        # Ưu tiên config is_default
        config = self.search([('is_default', '=', True), ('active', '=', True)], limit=1)
        if not config:
            config = self.search([('active', '=', True)], limit=1)
        if not config:
            return self.browse()

        if level:
            tier = config.bonus_tier_ids.filtered(lambda t: t.level == level)
            if tier:
                return tier[0]
        return config


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    referral_bonus_amount = fields.Float(
        string='Số tiền thưởng giới thiệu',
        config_parameter='employee_referral.bonus_amount',
        default=500000
    )

    referral_probation_days = fields.Integer(
        string='Số ngày thử việc',
        config_parameter='employee_referral.probation_days',
        default=60
    )
