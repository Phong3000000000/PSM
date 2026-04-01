# controllers/api.py
from odoo import http
from odoo.http import request

class VoucherAPI(http.Controller):

    @http.route('/voucher/redeem/<int:voucher_id>',
                type='json',
                auth='user',
                methods=['POST'])
    def redeem_voucher(self, voucher_id):
        user = request.env.user
        employee = request.env['hr.employee'].sudo().search([
            ('uid', '=', user.id)
        ], limit=1)
        if not employee and user.email:
            employee = request.env['hr.employee'].sudo().search([
                ('work_email', '=', user.email)
            ], limit=1)

        if not employee:
            return {'error': 'Không tìm thấy nhân viên'}

        voucher = request.env['voucher.voucher'].sudo().browse(voucher_id)

        if voucher.quantity <= 0:
            return {'error': 'Voucher đã hết'}

        if employee.total_points < voucher.point_required:
            return {'error': 'Không đủ điểm'}

        # Trừ điểm
        employee.sudo().write({
            'total_points': employee.total_points - voucher.point_required
        })

        # Giảm số lượng voucher
        voucher.sudo().write({
            'quantity': voucher.quantity - 1
        })

        # Lưu lịch sử
        request.env['voucher.redeem'].sudo().create({
            'employee_id': employee.id,
            'voucher_id': voucher.id,
            'point_used': voucher.point_required
        })

        return {
            'success': True,
            'message': 'Đổi voucher thành công',
            'voucher_code': voucher.code
        }
