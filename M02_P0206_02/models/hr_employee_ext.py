# -*- coding: utf-8 -*-
from odoo import models, fields, api


class HrEmployeeExt(models.Model):
    """
    Mở rộng hr.employee để thêm kỹ năng và giới hạn giờ làm
    """
    _inherit = 'hr.employee'
    
    # Kỹ năng theo trạm/vai trò
    skill_role_ids = fields.Many2many(
        'planning.role',
        'employee_skill_role_rel',
        'employee_id',
        'role_id',
        string='Kỹ năng làm việc',
        help='Các trạm/vai trò mà nhân viên đã được đào tạo và có thể đảm nhận'
    )
    
    _sql_constraints = [
        ('user_id_uniq', 'unique(user_id)', 'Mỗi tài khoản (User) chỉ được liên kết với một Nhân viên (Employee) duy nhất. Vui lòng kiểm tra lại!')
    ]
    
    # Loại hình hợp đồng (cho mục đích scheduling)
    employment_type = fields.Selection([
        ('full_time', 'Full-time'),
        ('part_time', 'Part-time'),
    ], string='Loại hình', default='full_time')
    
    # Giới hạn giờ làm việc
    min_hours_week = fields.Float(
        string='Giờ tối thiểu/tuần',
        default=20.0,
        help='Số giờ làm việc tối thiểu mỗi tuần'
    )
    max_hours_week = fields.Float(
        string='Giờ tối đa/tuần',
        default=48.0,
        help='Số giờ làm việc tối đa mỗi tuần (không tính OT)'
    )
    
    # Khả năng làm việc
    availability_ids = fields.One2many(
        'employee.availability',
        'employee_id',
        string='Khung giờ rảnh/bận'
    )
    
    # Hourly rate (cho Part-time)
    hourly_rate = fields.Float(
        string='Lương theo giờ',
        help='Áp dụng cho nhân viên Part-time'
    )
    
    # Kỹ năng theo trạm (Station Skills - cho VLH Engine)
    station_skill_ids = fields.Many2many(
        'workforce.station',
        'employee_station_skill_rel',
        'employee_id',
        'station_id',
        string='Trạm được phép làm',
        help='Danh sách các trạm mà nhân viên được đào tạo và có thể đảm nhận (dấu "v" trong Proficiency Matrix)'
    )
    
    # Hourly Cost (cho tính L%)
    hourly_cost = fields.Float(
        string='Chi phí theo giờ',
        help='Chi phí nhân sự theo giờ (bao gồm lương + phụ cấp). Dùng để tính L%'
    )
    
    def get_week_worked_hours(self, date_start, date_end):
        """
        Tính tổng giờ làm việc đã đăng ký trong khoảng thời gian
        Dùng để kiểm tra max_hours_week
        """
        self.ensure_one()
        PlanningSlot = self.env['planning.slot']
        
        slots = PlanningSlot.search([
            ('resource_id', '=', self.resource_id.id),
            ('start_datetime', '>=', date_start),
            ('end_datetime', '<=', date_end),
            ('approval_state', 'in', ['to_approve', 'approved']),
        ])
        
        total_hours = sum(slots.mapped('allocated_hours'))
        return total_hours

