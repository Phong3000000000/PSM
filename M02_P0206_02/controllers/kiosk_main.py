# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request


class KioskRatingController(http.Controller):
    """Controller xử lý API từ Kiosk popup"""
    
    @http.route('/attendance/rating', type='json', auth='user')
    def save_rating(self, employee_id, rating, note='', confirmed_hours=0):
        """Lưu đánh giá cuối ca"""
        AttendanceRating = request.env['attendance.rating'].sudo()
        
        # Tìm attendance record cuối cùng của nhân viên
        attendance = request.env['hr.attendance'].sudo().search([
            ('employee_id', '=', employee_id),
            ('check_out', '=', False),
        ], limit=1)
        
        rating_vals = {
            'employee_id': employee_id,
            'performance_rating': rating,
            'note': note,
            'confirmed_hours': confirmed_hours,
            'is_confirmed': True,
            'attendance_id': attendance.id if attendance else False,
        }
        
        rating_record = AttendanceRating.create(rating_vals)
        
        # Liên kết rating với attendance
        if attendance:
            attendance.write({'rating_id': rating_record.id})
        
        return {'success': True, 'rating_id': rating_record.id}

