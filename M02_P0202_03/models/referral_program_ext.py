# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError

class ReferralProgram(models.Model):
    _inherit = 'employee.referral.program'

    # ── Phân quyền theo phòng ban / cá nhân ─────────────────────────
    target_department_ids = fields.Many2many(
        'hr.department',
        string='Giới hạn phòng ban',
        help='Để trống = mọi nhân viên đều thấy. Chọn phòng ban = chỉ NV thuộc phòng ban đó thấy.'
    )
    target_employee_ids = fields.Many2many(
        'hr.employee',
        string='Giới hạn cá nhân',
        help='Chọn cụ thể nhân viên được phép tham gia chương trình này.'
    )

    submission_ids = fields.One2many(
        'employee.referral.submission',
        'program_id',
        string='Danh sách giới thiệu'
    )
    
    # Statistics computation override (non-stored = always fresh)
    submission_count = fields.Integer(compute='_compute_statistics')
    registered_count = fields.Integer(compute='_compute_statistics')
    hired_count = fields.Integer(compute='_compute_statistics')
    completed_count = fields.Integer(compute='_compute_statistics')


    @api.depends('submission_ids', 'submission_ids.state')
    def _compute_statistics(self):
        for rec in self:
            submissions = rec.submission_ids
            rec.submission_count = len(submissions)
            rec.registered_count = len(submissions.filtered(lambda s: s.state in ['registered', 'interviewing', 'hired', 'probation', 'completed']))
            rec.hired_count = len(submissions.filtered(lambda s: s.state in ['hired', 'probation', 'completed']))
            rec.completed_count = len(submissions.filtered(lambda s: s.state == 'completed'))

    def action_activate(self):
        """Activate program and track HR publish info"""
        super(ReferralProgram, self).action_activate()
        if hasattr(self, 'hr_user_id'):
            self.write({
                'hr_user_id': self.env.user.id,
                'hr_published_date': fields.Datetime.now(),
            })


    def _check_auto_close(self):
        """Auto close program if hired count meets total positions needed"""
        for rec in self:
            if rec.state != 'active':
                continue
            total_needed = sum(rec.line_ids.mapped('positions_needed'))
            if total_needed and rec.hired_count >= total_needed:
                rec.action_close()
                rec.message_post(
                    body=_('Chương trình đã tự động đóng do đã tuyển đủ số lượng (%s/%s) ứng viên.')
                         % (rec.hired_count, total_needed),
                    message_type='notification'
                )

    def action_hr_publish(self):
        """HR publish via wizard"""
        self.ensure_one()
        return {
            'name': _('Tạo bài đăng'),
            'type': 'ir.actions.act_window',
            'res_model': 'referral.publish.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_program_id': self.id}
        }

    def action_close(self):
        """Override to close program — chỉ đóng khi đã tuyển đủ tất cả vị trí"""
        for rec in self:
            unfilled = []
            for line in rec.line_ids:
                filled = len(rec.submission_ids.filtered(
                    lambda s: s.job_id == line.job_id and s.state in ('hired', 'probation', 'completed')
                ))
                needed = line.positions_needed or 0
                if filled < needed:
                    unfilled.append(
                        _('%s: %d/%d') % (line.job_id.name or '?', filled, needed)
                    )
            if unfilled:
                raise UserError(_(
                    'Chưa tuyển đủ các vị trí sau:\n%s\n\nVui lòng hoàn thành tuyển dụng trước khi đóng chương trình.'
                ) % '\n'.join(unfilled))
        super(ReferralProgram, self).action_close()

    def action_open_portal(self):
        """Open portal referral jobs detail page for this program"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_url',
            'url': f'/referral/jobs/{self.id}',
            'target': 'new',
        }


    def action_view_submissions(self):
        """View all submissions"""
        return {
            'name': _('Danh sách giới thiệu'),
            'type': 'ir.actions.act_window',
            'res_model': 'employee.referral.submission',
            'view_mode': 'list,form',
            'domain': [('program_id', '=', self.id)],
            'context': {'default_program_id': self.id}
        }
        
    @api.model
    def run_cron_auto_close_programs(self):
        """Cron job to auto close programs based on end_date and filled positions"""
        # 1. Close by end_date
        today = fields.Date.today()
        expired_programs = self.search([
            ('state', '=', 'active'),
            ('end_date', '<', today)
        ])
        for prog in expired_programs:
            prog.action_close()
            prog.message_post(
                body=_('Chương trình đã tự động đóng do hết hạn (Ngày kết thúc: %s)') % prog.end_date,
                message_type='notification'
            )
        
        # 2. Close by filled positions (Optional/Already exists as _check_auto_close, but let's call it here for reinforcement)
        active_programs = self.search([('state', '=', 'active')])
        active_programs._check_auto_close()
