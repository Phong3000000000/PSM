# -*- coding: utf-8 -*-
from datetime import datetime
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class AdeccoReportWizard(models.TransientModel):
    """
    Wizard để chọn tham số cho báo cáo Adecco
    Sử dụng Odoo Report chuẩn (QWeb)
    """
    _name = 'adecco.report.wizard'
    _description = 'Wizard xuất báo cáo Adecco'

    date_from = fields.Date(
        string='Từ ngày',
        required=True,
        default=lambda self: fields.Date.today().replace(day=1)
    )
    date_to = fields.Date(
        string='Đến ngày',
        required=True,
        default=fields.Date.today
    )
    
    employee_ids = fields.Many2many(
        'hr.employee',
        string='Nhân viên',
        domain=[('employment_type', '=', 'part_time')],
        help='Để trống để xuất tất cả nhân viên Part-time'
    )

    def action_print_report(self):
        """In báo cáo PDF"""
        self.ensure_one()
        
        # Tìm nhân viên Part-time
        domain = [('employment_type', '=', 'part_time')]
        if self.employee_ids:
            domain.append(('id', 'in', self.employee_ids.ids))
        
        employees = self.env['hr.employee'].search(domain)
        
        if not employees:
            raise UserError(_('Không tìm thấy nhân viên Part-time nào!'))
        
        # Lọc chỉ những nhân viên đã xác nhận công tháng
        # (Step 13-14: Report chỉ xuất những nhân viên có employee_confirmed = True)
        month = '%02d' % self.date_from.month
        year = self.date_from.year
        
        MonthClosing = self.env['workforce.month.closing']
        confirmed_employees = []
        
        for emp in employees:
            closing = MonthClosing.search([
                ('employee_id', '=', emp.id),
                ('period_month', '=', month),
                ('period_year', '=', year),
                ('employee_confirmed', '=', True),
            ], limit=1)
            if closing:
                confirmed_employees.append(emp.id)
        
        if not confirmed_employees:
            raise UserError(_('Không có nhân viên Part-time nào đã xác nhận công tháng %s/%s!') % (month, year))
        
        # Gọi report action
        return self.env.ref('M02_P0206_00.action_report_adecco').report_action(
            self, 
            data={
                'employee_ids': confirmed_employees,
                'date_from': self.date_from.strftime('%Y-%m-%d'),
                'date_to': self.date_to.strftime('%Y-%m-%d'),
            }
        )
    
    def action_print_xlsx(self):
        """In báo cáo Excel (nếu có module report_xlsx)"""
        self.ensure_one()
        
        domain = [('employment_type', '=', 'part_time')]
        if self.employee_ids:
            domain.append(('id', 'in', self.employee_ids.ids))
        
        employees = self.env['hr.employee'].search(domain)
        
        if not employees:
            raise UserError(_('Không tìm thấy nhân viên Part-time nào!'))
        
        # Thử gọi xlsx report nếu có
        try:
            return self.env.ref('M02_P0206_00.action_report_adecco_xlsx').report_action(
                self,
                data={
                    'employee_ids': employees.ids,
                    'date_from': self.date_from.strftime('%Y-%m-%d'),
                    'date_to': self.date_to.strftime('%Y-%m-%d'),
                }
            )
        except Exception:
            # Fallback to PDF
            return self.action_print_report()


        return {
            'type': 'ir.actions.act_window',
            'name': 'Gửi báo cáo',
            'res_model': 'adecco.report.wizard',
            'view_mode': 'form',
            'res_id': self.id,
            'target': 'new',
        }

