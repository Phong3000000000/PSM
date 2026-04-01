# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import AccessError

class JobApprovalRequest(models.Model):
    _name = 'job.approval.request'
    _description = 'Yêu cầu Tuyển dụng'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Vị trí', required=True, tracking=True)
    
    department_id = fields.Many2one('hr.department', string='Phòng ban', tracking=True)
    company_id = fields.Many2one('res.company', string='Công ty', required=True, default=lambda self: self.env.company)
    
    no_of_recruitment = fields.Integer(string='Số lượng cần tuyển', default=1, tracking=True)
    
    recruitment_type = fields.Selection([
        ('store', 'Khối Cửa Hàng'),
        ('office', 'Khối Văn Phòng'),
    ], string='Loại Tuyển Dụng', tracking=True)

    position_level = fields.Selection([
        ('management', 'Quản Lý'),
        ('staff', 'Nhân Viên'),
    ], string='Cấp Bậc', tracking=True)

    requester_user_id = fields.Many2one('res.users', string='Người yêu cầu', default=lambda self: self.env.user, tracking=True)
    
    approver_user_id = fields.Many2one('res.users', string='Người duyệt', tracking=True)
    approver_employee_id = fields.Many2one('hr.employee', string='Nhân viên Duyệt', compute='_compute_approver_employee', store=True)

    state = fields.Selection([
        ('draft', 'Nháp'),
        ('submitted', 'Chờ Duyệt'),
        ('approved', 'Đã Duyệt'),
        ('rejected', 'Từ Chối')
    ], string='Trạng thái Phê duyệt', default='draft', tracking=True)

    reject_reason = fields.Text(string='Lý do từ chối', tracking=True)

    job_id = fields.Many2one('hr.job', string='Job Position (Đã tạo)', readonly=True, help='Link tới Job Position thật sau khi duyệt')

    @api.depends('approver_user_id')
    def _compute_approver_employee(self):
        for req in self:
            if req.approver_user_id:
                employee = self.env['hr.employee'].search([('user_id', '=', req.approver_user_id.id)], limit=1)
                req.approver_employee_id = employee.id if employee else False
            else:
                req.approver_employee_id = False

    def _get_requester_employee(self):
        self.ensure_one()
        if not self.requester_user_id:
            return False
        return self.env['hr.employee'].search([('user_id', '=', self.requester_user_id.id)], limit=1)

    def _get_default_approver_user(self):
        self.ensure_one()
        employee = self._get_requester_employee()
        if employee and employee.parent_id and employee.parent_id.user_id:
            approver_user = employee.parent_id.user_id
            if employee.department_id == self.department_id and employee.parent_id.department_id == self.department_id:
                return approver_user
            
        # Fallback 1: Manager of the department
        if self.department_id and self.department_id.manager_id and self.department_id.manager_id.user_id:
            return self.department_id.manager_id.user_id
            
        return False

    def _schedule_approval_activity(self):
        self.ensure_one()
        if not self.approver_user_id:
            return
            
        existing_activity = self.env['mail.activity'].search([
            ('res_model', '=', self._name),
            ('res_id', '=', self.id),
            ('user_id', '=', self.approver_user_id.id),
            ('activity_type_id', '=', self.env.ref('mail.mail_activity_data_todo').id)
        ], limit=1)
        
        if existing_activity:
            return

        note = f"""
            <p><b>Người yêu cầu:</b> {self.requester_user_id.name}</p>
            <p><b>Phòng ban:</b> {self.department_id.name or 'N/A'}</p>
            <p><b>Vị trí:</b> {self.name}</p>
            <p><b>Số lượng:</b> {self.no_of_recruitment}</p>
            <p><b>Khối tuyển dụng:</b> {dict(self._fields['recruitment_type'].selection).get(self.recruitment_type, 'N/A')}</p>
            <p><b>Cấp bậc:</b> {dict(self._fields['position_level'].selection).get(self.position_level, 'N/A')}</p>
        """

        self.activity_schedule(
            'mail.mail_activity_data_todo',
            user_id=self.approver_user_id.id,
            summary='Duyệt yêu cầu tuyển dụng mới',
            note=note,
            date_deadline=fields.Date.context_today(self)
        )

    def _close_approval_activity(self, feedback=''):
        self.ensure_one()
        activities = self.env['mail.activity'].search([
            ('res_model', '=', self._name),
            ('res_id', '=', self.id),
            ('user_id', '=', self.env.user.id),
            ('activity_type_id', '=', self.env.ref('mail.mail_activity_data_todo').id)
        ])
        for activity in activities:
            activity.action_feedback(feedback=feedback)

    @api.model_create_multi
    def create(self, vals_list):
        requests = super().create(vals_list)
        for req in requests:
            if req.state == 'submitted':
                approver = req._get_default_approver_user()
                if approver:
                    req.approver_user_id = approver.id
                    req._schedule_approval_activity()
        return requests

    def action_submit_approval(self):
        for record in self:
            record.state = 'submitted'
            if not record.approver_user_id:
                approver = record._get_default_approver_user()
                if approver:
                    record.approver_user_id = approver.id
            record._schedule_approval_activity()

    def action_approve(self):
        for record in self:
            if record.approver_user_id and self.env.user != record.approver_user_id and not self.env.user._is_admin():
                raise AccessError(f"Chỉ có {record.approver_user_id.name} mới có quyền duyệt yêu cầu này!")
                
            if not record.job_id:
                requested_qty = max(0, record.no_of_recruitment or 0)
                job_domain = [
                    ('name', '=', record.name),
                    ('department_id', '=', record.department_id.id),
                    ('recruitment_type', '=', record.recruitment_type),
                ]
                if record.position_level:
                    job_domain.append(('position_level', '=', record.position_level))

                # Ưu tiên cập nhật template có sẵn theo department/position.
                target_job = self.env['hr.job'].sudo().search(job_domain, limit=1)
                if target_job:
                    # Cộng dồn nhu cầu tuyển thay vì ghi đè.
                    target_job.write({
                        'no_of_recruitment': (target_job.no_of_recruitment or 0) + requested_qty,
                        'user_id': False,
                        'oje_evaluator_user_id': record.requester_user_id.id,
                    })
                    record.job_id = target_job.id
                else:
                    # Fallback: chưa có template thì tạo mới hr.job.
                    vals = {
                        'name': record.name,
                        'department_id': record.department_id.id,
                        'company_id': record.company_id.id,
                        'no_of_recruitment': requested_qty,
                        'user_id': False,
                        'oje_evaluator_user_id': record.requester_user_id.id,
                    }
                    if record.recruitment_type:
                        vals['recruitment_type'] = record.recruitment_type
                    if record.position_level:
                        vals['position_level'] = record.position_level

                    new_job = self.env['hr.job'].sudo().create(vals)
                    record.job_id = new_job.id
                    
            record.state = 'approved'
            record._close_approval_activity('Đã phê duyệt')

    def action_reject(self):
        self.ensure_one()
        return {
            'name': 'Lý do từ chối',
            'type': 'ir.actions.act_window',
            'res_model': 'reject.job.approval.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_request_id': self.id},
        }

    def action_reject_with_reason(self, reason):
        for record in self:
            if record.approver_user_id and self.env.user != record.approver_user_id and not self.env.user._is_admin():
                raise AccessError(f"Chỉ có {record.approver_user_id.name} mới có quyền từ chối yêu cầu này!")
            
            if not reason or not reason.strip():
                from odoo.exceptions import ValidationError
                raise ValidationError("Vui lòng nhập lý do từ chối!")

            record.write({
                'state': 'rejected',
                'reject_reason': reason.strip(),
            })
            record._close_approval_activity(f"Đã từ chối: {reason.strip()}")
