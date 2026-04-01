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
            return self.env.ref('rgm_workforce.action_report_adecco_xlsx').report_action(
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


class AdeccoReportAbstract(models.AbstractModel):
    """
    Report Abstract Model - Xử lý data cho QWeb template
    """
    _name = 'report.rgm_workforce.report_adecco_template'
    _description = 'Adecco Report Abstract'

    @api.model
    def _get_report_values(self, docids, data=None):
        """Chuẩn bị dữ liệu cho report"""
        employee_ids = data.get('employee_ids', [])
        date_from = data.get('date_from')
        date_to = data.get('date_to')
        
        employees = self.env['hr.employee'].browse(employee_ids)
        Attendance = self.env['hr.attendance']
        
        report_lines = []
        total_hours = 0
        total_amount = 0
        
        for emp in employees:
            # Tính tổng giờ làm
            attendances = Attendance.search([
                ('employee_id', '=', emp.id),
                ('check_in', '>=', date_from),
                ('check_out', '<=', date_to + ' 23:59:59'),
            ])
            
            worked_hours = sum(att.worked_hours for att in attendances)
            hourly_rate = emp.hourly_rate or 0
            amount = worked_hours * hourly_rate
            
            report_lines.append({
                'employee': emp,
                'barcode': emp.barcode or emp.id,
                'name': emp.name,
                'worked_hours': round(worked_hours, 2),
                'hourly_rate': hourly_rate,
                'amount': round(amount, 2),
            })
            
            total_hours += worked_hours
            total_amount += amount
        
        return {
            'doc_ids': docids,
            'doc_model': 'adecco.report.wizard',
            'docs': self.env['adecco.report.wizard'].browse(docids),
            'data': data,
            'date_from': date_from,
            'date_to': date_to,
            'report_lines': report_lines,
            'total_hours': round(total_hours, 2),
            'total_amount': round(total_amount, 2),
        }

