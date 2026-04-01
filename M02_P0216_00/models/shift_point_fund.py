# -*- coding: utf-8 -*-
from odoo.exceptions import AccessError
from odoo import models, fields, api, _

class ShiftPointFund(models.Model):
    _name = 'shift.point.fund'
    _description = 'Kho điểm'

    name = fields.Char(string='Tên', required=True)
    score = fields.Float(string='Điểm', required=True, default=200)
    fund_type = fields.Selection([
        ('all', 'Tổng'),
        ('department', 'Department'),
        ('EOTM', 'EOTM'),
        ('EOTQ', 'EOTQ')
    ], string='Loại', required=True, default='all')

    company_id = fields.Many2one('res.company', string='Chi nhánh')
    department_id = fields.Many2one('hr.department', string='Phòng ban')
    
    employee_ids = fields.Many2many(
        'hr.employee',
        string='Nhân viên',
        compute='_compute_employees'
    )

    @api.onchange('fund_type', 'company_id', 'department_id')
    def _onchange_fund_type_or_company(self):
        if self.fund_type == 'EOTM':
            company_count = self.env['res.company'].search_count([])
            self.score = 100 * company_count
            self.name = 'EOTM'
        elif self.fund_type == 'EOTQ':
            self.name = 'EOTQ'
        elif self.fund_type == 'department' and self.department_id:
            self.name = self.department_id.name
        elif self.fund_type == 'department' and self.company_id:
            self.name = self.company_id.name

    @api.depends('department_id', 'company_id')
    def _compute_employees(self):
        for record in self:
            if record.department_id:
                employees = self.env['hr.employee'].search([
                    ('department_id', '=', record.department_id.id)
                ])
            elif record.company_id:
                employees = self.env['hr.employee'].search([
                    ('company_id', '=', record.company_id.id)
                ])
            else:
                employees = self.env['hr.employee']
            record.employee_ids = employees

    def action_open_grant_form(self):
        """Mở form cấp điểm với kho điểm đã chọn sẵn"""
        self.ensure_one()
        # Get employee_id from context (passed from button in employee list)
        employee_id = self.env.context.get('employee_id')
        # # Check access rights
        # is_rgm = self.env.user.has_group('M02_P0216_00.group_regional_general_manager')
        
        # employee = self.env['hr.employee'].search([('user_id', '=', self.env.user.id)], limit=1)
        # is_dept_manager = False
        # if employee:
        #     is_dept_manager = self.env['hr.department'].search_count([('manager_id', '=', employee.id)]) > 0
            
        # if not is_rgm and not is_dept_manager:
        #      raise AccessError(_("Chỉ Quản lý phòng ban hoặc RGM mới có quyền thực hiện hành động này!"))

        return {
            'type': 'ir.actions.act_window',
            'name': 'Cấp điểm',
            'res_model': 'point.grant',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_fund_id': self.id,
                'default_employee_id': employee_id,
            }
        }
    def _check_hr_access(self):
        """Kiểm tra user có phải nhân viên phòng HR không"""
        if not self.env.user.has_group('M02_P0216_00.group_hr_department'):
            # Hoặc kiểm tra qua department
            employee = self.env['hr.employee'].search([('user_id', '=', self.env.user.id)], limit=1)
            hr_dept = self.env.ref('M02_P0216_00.dep_hq_hr', raise_if_not_found=False)
            
            if not employee or not hr_dept or employee.department_id != hr_dept:
                raise AccessError(_("Chỉ nhân viên phòng HR mới có quyền truy cập Kho điểm!"))

    # @api.model
    # def search_read(self, domain=None, fields=None, offset=0, limit=None, order=None):
    #     """Override search_read để kiểm tra quyền khi xem danh sách"""
    #     self._check_hr_access()
    #     return super(ShiftPointFund, self).search_read(domain, fields, offset, limit, order)

    # @api.model_create_multi
    # def create(self, vals_list):
    #     self._check_hr_access()
    #     return super(ShiftPointFund, self).create(vals_list)

    # def write(self, vals):
    #     self._check_hr_access()
    #     return super(ShiftPointFund, self).write(vals)

    def action_generate_funds(self):
        """Tạo kho điểm hàng loạt cho tất cả Chi nhánh và Phòng ban"""
        # 1. Tạo kho điểm cho tất cả Chi nhánh (Companies)
        companies = self.env['res.company'].search([])
        for company in companies:
            # Check if fund exists for this company
            existing_fund = self.search([
                ('company_id', '=', company.id),
                ('fund_type', '=', 'department') 
            ], limit=1)
            
            if not existing_fund:
                self.create({
                    'name': company.name,
                    'fund_type': 'department',
                    'company_id': company.id,
                    'score': 200
                })

        # 2. Tạo kho điểm cho tất cả Phòng ban (Departments)
        departments = self.env['hr.department'].search([])
        for dept in departments:
             # Check if fund exists for this department
            existing_fund = self.search([
                ('department_id', '=', dept.id),
                ('fund_type', '=', 'department')
            ], limit=1)

            if not existing_fund:
                self.create({
                    'name': dept.name,
                    'fund_type': 'department',
                    'department_id': dept.id,
                    'score': 200
                })
       
        
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }
