# -*- coding: utf-8 -*-
"""
Referral Program Model (Core)
Chương trình giới thiệu nhân sự (M02_P0204_01)
"""

from odoo import models, fields, api, _
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)

class ReferralProgramLine(models.Model):
    _name = 'employee.referral.program.line'
    _description = 'Chi tiet vi tri tuyen dung'
    
    program_id = fields.Many2one('employee.referral.program', string='Chuong trinh', required=True, ondelete='cascade')
    job_id = fields.Many2one('hr.job', string='Vi tri', required=True)
    positions_needed = fields.Integer(string='So luong', default=1)
    salary = fields.Float(string='Luong (VND)', default=0)
    job_type = fields.Selection([
        ('fulltime', 'Full-time'),
        ('parttime', 'Part-time'),
    ], string='Hinh thuc', default='fulltime')
    
    # Bonus configuration per line
    bonus_amount = fields.Float(
        string='Tien thuong (VND)',
        compute='_compute_bonus_amount',
        inverse='_inverse_bonus_amount',
        store=True
    )
    bonus_override = fields.Float(string='Tien thuong (override)')
    
    @api.depends('bonus_override', 'program_id.store_id')
    def _compute_bonus_amount(self):
        for rec in self:
            if rec.bonus_override:
                rec.bonus_amount = rec.bonus_override
            else:
                config = self.env['employee.referral.config'].sudo().get_config(
                    rec.program_id.store_id.id if rec.program_id.store_id else None
                )
                rec.bonus_amount = config.bonus_amount if config else 500000

    def _inverse_bonus_amount(self):
        for rec in self:
            rec.bonus_override = rec.bonus_amount


class ReferralProgram(models.Model):
    _name = 'employee.referral.program'
    _description = 'Chương trình giới thiệu nhân sự'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

    name = fields.Char(string='Tên chương trình', required=True, tracking=True)
    
    # request_id moved to P0202 (Extension)
    
    line_ids = fields.One2many(
        'employee.referral.program.line',
        'program_id',
        string='Các vị trí tuyển dụng'
    )
    
    # Program dates
    start_date = fields.Date(
        string='Ngày bắt đầu',
        default=fields.Date.today,
        tracking=True
    )
    
    end_date = fields.Date(string='Ngày kết thúc', tracking=True)
    
    # State
    state = fields.Selection([
        ('draft', 'Nháp'),
        ('approved', 'OC đã duyệt'),
        ('active', 'Đang mở'),
        ('closed', 'Đã đóng'),
    ], string='Trạng thái', default='draft', tracking=True)
    
    store_id = fields.Many2one(
        'hr.department',
        string='Cửa hàng / Phòng ban'
    )
    
    description = fields.Html(string='Mô tả chương trình')
    
    # Statistics placeholders (Overridden in P0202)
    submission_count = fields.Integer(string='Số lượng giới thiệu', default=0)
    registered_count = fields.Integer(string='Số lượng ứng viên', default=0)
    hired_count = fields.Integer(string='Số lượng tuyển', default=0)
    completed_count = fields.Integer(string='Số lượng hoàn thành', default=0)

    def action_load_demo_data(self):
        """Tạo dữ liệu mẫu chương trình tuyển dụng để test"""
        from datetime import date, timedelta

        stores = self.env['hr.department'].search([], limit=3)
        if not stores:
            from odoo.exceptions import UserError
            raise UserError(_('Chưa có phòng ban nào! Vui lòng tạo trước trong HR → Departments.'))
        if not stores:
            from odoo.exceptions import UserError
            raise UserError(_('Chưa có công ty/cửa hàng nào!'))

        jobs = self.env['hr.job'].search([], limit=6)
        if not jobs:
            from odoo.exceptions import UserError
            raise UserError(_('Chưa có vị trí công việc nào! Vui lòng tạo trước.'))

        today = date.today()
        DEMO = [
            {'job_idx': 0, 'qty': 3, 'salary': 8_000_000,  'job_type': 'fulltime',  'bonus': 1_000_000, 'days': 60},
            {'job_idx': 1, 'qty': 5, 'salary': 6_500_000,  'job_type': 'parttime',  'bonus': 500_000,   'days': 45},
            {'job_idx': 2, 'qty': 2, 'salary': 12_000_000, 'job_type': 'fulltime',  'bonus': 2_000_000, 'days': 90},
            {'job_idx': 3, 'qty': 4, 'salary': 7_000_000,  'job_type': 'parttime',  'bonus': 700_000,   'days': 30},
            {'job_idx': 4, 'qty': 1, 'salary': 15_000_000, 'job_type': 'fulltime',  'bonus': 3_000_000, 'days': 120},
            {'job_idx': 5, 'qty': 3, 'salary': 9_000_000,  'job_type': 'fulltime',  'bonus': 1_500_000, 'days': 60},
        ]

        created = 0
        for i, demo in enumerate(DEMO):
            job = jobs[demo['job_idx']] if demo['job_idx'] < len(jobs) else jobs[0]
            store = stores[i % len(stores)]
            prog_name = f'[DEMO] Tuyển {job.name} - {store.name} Q{(i % 4) + 1}/{today.year}'

            if self.search([('name', '=', prog_name)], limit=1):
                continue

            prog = self.create({
                'name': prog_name,
                'store_id': store.id,
                'start_date': today,
                'end_date': today + timedelta(days=demo['days']),
                'state': 'draft',
            })
            
            self.env['employee.referral.program.line'].create({
                'program_id': prog.id,
                'job_id': job.id,
                'positions_needed': demo['qty'],
                'salary': demo['salary'],
                'job_type': demo['job_type'],
                'bonus_override': demo['bonus'],
            })
            created += 1

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Tao du lieu mau thanh cong!'),
                'message': (_('Da tao %d chuong trinh tuyen dung mau.') % created)
                           if created else _('Du lieu mau da ton tai, khong tao them.'),
                'type': 'success',
                'sticky': False,
            }
        }

    def action_activate(self):
        """Activate program"""
        self.ensure_one()
        self.write({'state': 'active'})
        
        # 1. Update Job Position Target for each line
        for line in self.line_ids:
            if line.job_id:
                line.job_id.sudo().write({
                    'no_of_recruitment': line.positions_needed
                })

        # 2. Send Email to all employees (optional)
        try:
            self._send_announcement_email()
        except Exception as e:
            _logger.warning("Could not send announcement email: %s", e)
        
        # 3. Global Notifications & Internal News (optional)
        try:
            config = self.env['employee.referral.config'].sudo().get_config()
            if config and config.news_blog_id:
                positions_text = ''.join(
                    f"<li><b>{l.job_id.name}</b>: {l.positions_needed} vị trí</li>"
                    for l in self.line_ids
                )
                content = f"""
                    <div class="referral-news-content">
                        <p>📢 <b>CƠ HỘI NGHỀ NGHIỆP TẠI {self.store_id.name}</b></p>
                        <p>Chúng tôi đang tìm kiếm đồng đội cho các vị trí:</p>
                        <ul>
                            {positions_text}
                        </ul>
                        
                        <div class="mt-4">
                            <h5>Mô tả chương trình</h5>
                            {self.description or ''}
                        </div>
                        
                        <p>Bạn có biết ai phù hợp? Hãy giới thiệu ngay để nhận thưởng!</p>
                        <p class="mt-3">
                            <a href="/referral/jobs/{self.id}" class="btn btn-primary">
                                Xem chi tiết & Giới thiệu
                            </a>
                        </p>
                    </div>
                """
                self.env['blog.post'].create({
                    'blog_id': config.news_blog_id.id,
                    'name': f"TUYỂN DỤNG: {self.name}",
                    'subtitle': f"Nhiều vị trí hấp dẫn",
                    'is_published': True,
                    'author_id': self.env.user.partner_id.id,
                    'content': content,
                })
            else:
                _logger.info("Skipping blog post: no config or no news_blog_id configured.")
        except Exception as e:
            _logger.warning("Could not create blog post: %s", e)

    
    def action_close(self):
        """Close program"""
        self.write({'state': 'closed'})

    def _send_announcement_email(self):
        """Send announcement to all employees"""
        template = self.env.ref('M02_P0202_01.email_referral_program_announce_v2', raise_if_not_found=False)
        # Note: Template is in M02_P0202_01. P0204 cannot reference P0202 data easily unless it's available at runtime.
        # Since this is a soft reference (ref), it will work if P0202 is installed.
        # But conceptually, P0204 runs "before" P0202.
        # Ideally, move the email template to P0204? Or keep the method here.
        # I'll keep it here.
        
        if template:
            employees = self.env['hr.employee'].search([
                ('work_email', '!=', False),
                ('active', '=', True)
            ])
            for employee in employees:
                try:
                    template.with_context(employee=employee).send_mail(self.id, force_send=False)
                except Exception as e:
                    _logger.warning(f"Failed to send announcement to {employee.name}: {e}")
