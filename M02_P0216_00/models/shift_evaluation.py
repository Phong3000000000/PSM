# -*- coding: utf-8 -*-

from odoo import models, fields, api


class ShiftEvaluation(models.Model):
    _name = 'shift.evaluation'
    _description = 'Shift Evaluation'
    _order = 'date desc, shift'

    name = fields.Char(
        string='Tên',
        compute='_compute_name',
        store=True
    )
    date = fields.Date(
        string='Ngày',
        required=True,
        default=fields.Date.context_today
    )
    mic_id = fields.Many2one(
        'hr.employee',
        string='MIC (Người phụ trách)',
        required=True
    )
    shift = fields.Selection([
        ('morning', 'Sáng'),
        ('afternoon', 'Chiều'),
        ('evening', 'Tối'),
    ], string='Ca làm', required=True, default='morning')
    company_id = fields.Many2one(
        'res.company',
        string='Công ty',
        required=True,
        default=lambda self: self.env.company
    )
    employee_ids = fields.Many2many(
        'hr.employee',
        'shift_evaluation_employee_rel',
        'shift_id',
        'employee_id',
        string='Nhân viên'
    )
    employee_count = fields.Integer(
        string='Số nhân viên',
        compute='_compute_employee_count',
        store=True
    )
    state = fields.Selection([
        ('draft', 'Nháp'),
        ('in_progress', 'Đang xử lý'),
        ('done', 'Hoàn thành'),
        ('cancelled', 'Đã hủy'),
    ], string='Trạng thái', default='draft', tracking=True)
    department_id = fields.Many2one(
        'hr.department',
        string='Phòng ban'
    )
    post_shift_ids = fields.One2many(
        'post.shift',
        'shift_evaluation_id',
        string='Post Shift Scores'
    )

    @api.onchange('employee_ids')
    def _onchange_employee_ids(self):
        """Tự động đồng bộ danh sách chấm điểm khi chọn nhân viên"""
        if not self.employee_ids:
            self.post_shift_ids = [(5, 0, 0)]
            return

        existing_employees = self.post_shift_ids.mapped('employee_id')
        new_employees = self.employee_ids - existing_employees
        removed_employees = existing_employees - self.employee_ids

        commands = []
        
        # Xóa các dòng của nhân viên không còn trong danh sách
        for line in self.post_shift_ids:
            if line.employee_id in removed_employees:
                commands.append((2, line.id))
        
        # Thêm dòng mới cho nhân viên vừa được chọn
        for employee in new_employees:
            commands.append((0, 0, {
                'employee_id': employee.id,
                'score': 0.0,
            }))
            
        if commands:
            self.post_shift_ids = commands

    @api.depends('employee_ids')
    def _compute_employee_count(self):
        for record in self:
            record.employee_count = len(record.employee_ids)

    @api.depends('date', 'shift', 'mic_id')
    def _compute_name(self):
        shift_labels = dict(self._fields['shift'].selection)
        for record in self:
            shift_label = shift_labels.get(record.shift, '')
            mic_name = record.mic_id.name if record.mic_id else ''
            date_str = record.date.strftime('%d/%m/%Y') if record.date else ''
            record.name = f"{date_str} - {shift_label} - {mic_name}"

    def action_start(self):
        self.write({'state': 'in_progress'})

    def action_done(self):
        self.write({'state': 'done'})

    def action_cancel(self):
        self.write({'state': 'cancelled'})

    def action_draft(self):
        self.write({'state': 'draft'})

    def action_open_post_shift(self):
        """Tạo PostShift records cho các nhân viên nếu chưa có, sau đó mở list"""
        self.ensure_one()
        PostShift = self.env['post.shift']
        
        # Tạo PostShift cho các nhân viên chưa có record
        existing_employees = self.post_shift_ids.mapped('employee_id')
        for employee in self.employee_ids:
            if employee not in existing_employees:
                PostShift.create({
                    'shift_evaluation_id': self.id,
                    'employee_id': employee.id,
                })
        
        # Mở list view
        return {
            'name': f'Chấm điểm - {self.name}',
            'type': 'ir.actions.act_window',
            'res_model': 'post.shift',
            'view_mode': 'list',
            'domain': [('shift_evaluation_id', '=', self.id)],
            'context': {
                'default_shift_evaluation_id': self.id,
            },
            'target': 'current',
        }

    def action_view_detail(self):
        """Mở form view của record này"""
        self.ensure_one()
        return {
            'name': self.name,
            'type': 'ir.actions.act_window',
            'res_model': 'shift.evaluation',
            'view_mode': 'form',
            'res_id': self.id,
            'target': 'current',
        }


