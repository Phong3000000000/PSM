# -*- coding: utf-8 -*-
from datetime import datetime, timedelta
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class SmartSchedulerWizard(models.TransientModel):
    """
    Wizard sinh lịch làm việc tự động từ dữ liệu Forecast
    """
    _name = 'smart.scheduler.wizard'
    _description = 'Wizard Sinh Lịch Thông Minh'

    period_id = fields.Many2one(
        'planning.period',
        string='Kỳ đăng ký',
        required=True
    )
    
    use_forecast = fields.Boolean(
        string='Dựa trên VLH Forecast',
        default=True,
        help='Nếu bật, hệ thống sẽ tính số slot dựa trên dữ liệu Forecast'
    )
    
    # Cấu hình ca làm việc
    shift_template_ids = fields.Many2many(
        'workforce.shift.template',
        string='Mẫu ca làm việc',
        required=True,
        domain="[('is_active', '=', True)]"
    )
    
    # Giới hạn nhân sự
    min_headcount = fields.Integer(
        string='Min nhân sự/ca',
        default=2
    )
    max_headcount = fields.Integer(
        string='Max nhân sự/ca',
        default=8
    )
    
    # Role mặc định
    default_role_id = fields.Many2one(
        'planning.role',
        string='Vai trò mặc định'
    )
    
    def action_generate(self):
        """Sinh slots dựa trên forecast và config"""
        self.ensure_one()
        
        if not self.period_id:
            raise UserError(_('Vui lòng chọn Kỳ đăng ký!'))
        
        if self.period_id.state != 'draft':
            raise UserError(_('Chỉ có thể sinh lịch cho kỳ đang ở trạng thái Nháp!'))
        
        PlanningSlot = self.env['planning.slot']
        Forecast = self.env['workforce.forecast']
        
        date_from = self.period_id.date_from
        date_to = self.period_id.date_to
        
        slots_created = 0
        current_date = date_from
        
        # Sắp xếp template (chạy theo sequence)
        sorted_templates = self.shift_template_ids.sorted('sequence')
        
        while current_date <= date_to:
            for template in sorted_templates:
                slots_created += self._create_shift_slots(
                    current_date,
                    template.start_hour,
                    template.end_hour,
                    Forecast,
                    PlanningSlot,
                    is_peak=template.is_peak
                )
            
            current_date += timedelta(days=1)
        
        # Thông báo kết quả
        self.period_id.message_post(
            body=_('Đã sinh %s ca làm việc từ %s đến %s.') % (
                slots_created,
                date_from.strftime('%d/%m/%Y'),
                date_to.strftime('%d/%m/%Y')
            ),
            message_type='notification'
        )
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Ca làm việc đã tạo'),
            'res_model': 'planning.slot',
            'view_mode': 'list,gantt',
            'domain': [('period_id', '=', self.period_id.id)],
            'context': {'default_period_id': self.period_id.id},
        }
    
    def _create_shift_slots(self, date, start_hour, end_hour, Forecast, PlanningSlot, is_peak=False):
        """
        Tạo slots cho một ca làm việc
        Return: Số slots đã tạo
        """
        # Tính số nhân sự cần dựa trên forecast
        if self.use_forecast:
            # Lấy forecast trung bình trong khung giờ này
            forecasts = Forecast.search([
                ('date', '=', date),
                ('hour', '>=', start_hour),
                ('hour', '<', end_hour),
            ])
            if forecasts:
                avg_staff = sum(forecasts.mapped('staff_needed')) / len(forecasts)
                headcount = max(self.min_headcount, min(int(avg_staff), self.max_headcount))
            else:
                headcount = self.min_headcount
        else:
            headcount = self.min_headcount
        
        # Nếu là peak hour, thêm người (hoặc logic tùy biến khác nếu cần)
        if is_peak:
            # Ví dụ: Peak shift thường cần ít nhất 1 người thêm nếu ko dùng forecast,
            # hoặc logic riêng. Ở đây giữ logic cũ: +2 nhưng ko quá max
            headcount = min(headcount + 2, self.max_headcount)
        
        # Tạo datetime
        start_dt = datetime.combine(date, datetime.min.time()) + timedelta(hours=start_hour)
        # Handle overnight shift: nếu end_hour < start_hour thì là ngày hôm sau
        if end_hour < start_hour:
             end_dt = datetime.combine(date + timedelta(days=1), datetime.min.time()) + timedelta(hours=end_hour)
        else:
             end_dt = datetime.combine(date, datetime.min.time()) + timedelta(hours=end_hour)

        slots_created = 0
        for i in range(headcount):
            PlanningSlot.create({
                'start_datetime': start_dt,
                'end_datetime': end_dt,
                'period_id': self.period_id.id,
                'role_id': self.default_role_id.id if self.default_role_id else False,
                'state': 'draft',
                'approval_state': 'open',
                'allocated_hours': (end_dt - start_dt).total_seconds() / 3600.0,
            })
            slots_created += 1
        
        return slots_created

