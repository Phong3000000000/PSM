# -*- coding: utf-8 -*-
from odoo import models, api

class AdeccoReportAbstract(models.AbstractModel):
    """
    Report Abstract Model - Xử lý data cho QWeb template
    """
    _name = 'report.m02_p0206_00.report_adecco_template'
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
