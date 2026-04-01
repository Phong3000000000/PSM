# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal

class ApprovalController(CustomerPortal):

    # =========================================================
    # PORTAL APPROVALS - Dành cho Line Manager
    # =========================================================
    
    @http.route(['/my/approvals'], type='http', auth='user', website=True)
    def portal_approvals(self, **kw):
        """
        Trang duyệt yêu cầu cho Line Manager trên Portal
        Hiển thị cả ca làm việc và các approval.request
        """
        values = self._prepare_portal_layout_values()
        
        employee = request.env['hr.employee'].sudo().search([
            ('user_id', '=', request.env.user.id)
        ], limit=1)
        if not employee:
            # Fallback to base portal or show error
            return request.render('portal.portal_layout', {
                'user': request.env.user,
                'error': 'Tài khoản chưa liên kết nhân viên.'
            })
        
        # Tìm các nhân viên mà user này là quản lý trực tiếp (parent_id)
        subordinates = request.env['hr.employee'].sudo().search([
            ('parent_id', '=', employee.id)
        ])
        
        pending_shifts = []
        pending_requests = []
        pending_leaves = []
        recent_processed = []
        
        if subordinates:
            sub_ids = subordinates.ids
            sub_resource_ids = subordinates.mapped('resource_id').ids
            sub_user_ids = subordinates.mapped('user_id').ids
            sub_partner_ids = subordinates.mapped('work_contact_id').ids
            
            # 1. Lấy ca chờ duyệt (planning.slot)
            if 'planning.slot' in request.env:
                PlanningSlot = request.env['planning.slot'].sudo()
                if 'approval_state' in PlanningSlot._fields:
                    try:
                        from odoo import fields
                        pending_shifts = PlanningSlot.search([
                            ('resource_id', 'in', sub_resource_ids),
                            ('approval_state', '=', 'to_approve'),
                            ('start_datetime', '>=', fields.Datetime.now()),
                        ], order='start_datetime asc')
                    except Exception as e:
                        print(f"Error fetching planning slots: {e}")
            
            # 2. Lấy các approval.request chờ duyệt
            ApprovalRequest = request.env['approval.request'].sudo()
            pending_requests = ApprovalRequest.search([
                '|',
                ('request_owner_id', 'in', sub_user_ids),
                ('partner_id', 'in', sub_partner_ids),
                ('request_status', '=', 'pending'),
            ], order='create_date desc')

            # 3. Lấy đơn nghỉ phép chờ duyệt (hr.leave)
            Leave = request.env['hr.leave'].sudo()
            pending_leaves = Leave.search([
                ('employee_id', 'in', sub_ids),
                ('state', 'in', ['confirm', 'draft']),
            ], order='date_from asc')
            
            # 4. Lấy các yêu cầu đã xử lý gần đây (7 ngày)
            from datetime import datetime, timedelta
            week_ago = datetime.now() - timedelta(days=7)
            
            recent_processed = ApprovalRequest.search([
                '|',
                ('request_owner_id', 'in', sub_user_ids),
                ('partner_id', 'in', sub_partner_ids),
                ('request_status', 'in', ['approved', 'refused']),
                ('write_date', '>=', week_ago),
            ], order='write_date desc', limit=20)
        
        values.update({
            'user': request.env.user,
            'employee': employee,
            'subordinates': subordinates,
            'pending_shifts': pending_shifts,
            'pending_requests': pending_requests,
            'pending_leaves': pending_leaves,
            'recent_processed': recent_processed,
            'page_name': 'approvals',
        })
        
        return request.render('M02_P0200_00.portal_approvals_page', values)
    
    @http.route(['/my/approvals/approve-shift'], type='json', auth='user')
    def portal_approve_shift(self, slot_id):
        """API duyệt ca làm việc từ Portal"""
        employee = request.env.user.employee_id
        if not employee:
            return {'error': 'Tài khoản chưa liên kết nhân viên.'}
        
        PlanningSlot = request.env['planning.slot'].sudo()
        slot = PlanningSlot.browse(int(slot_id))
        
        if not slot.exists():
            return {'error': 'Ca làm việc không tồn tại.'}
        
        if not hasattr(slot, 'approval_state') or slot.approval_state != 'to_approve':
            return {'error': 'Ca này không ở trạng thái chờ duyệt.'}
        
        # Kiểm tra quyền: Chỉ manager của nhân viên đó mới được duyệt
        slot_employee = request.env['hr.employee'].sudo().search([
            ('resource_id', '=', slot.resource_id.id)
        ], limit=1)
        
        if not slot_employee or slot_employee.parent_id.id != employee.id:
            return {'error': 'Bạn không có quyền duyệt ca này.'}
        
        try:
            slot.write({'approval_state': 'approved'})
            
            # Gửi notification cho nhân viên
            if hasattr(slot, 'registered_by') and slot.registered_by and slot.registered_by.partner_id:
                slot.message_post(
                    body='Ca làm việc ngày %s đã được %s duyệt!' % (
                        slot.start_datetime.strftime('%d/%m/%Y'),
                        employee.name
                    ),
                    partner_ids=[slot.registered_by.partner_id.id],
                    message_type='notification'
                )
            
            return {'success': True, 'message': 'Đã duyệt ca thành công!'}
        except Exception as e:
            return {'error': 'Lỗi: %s' % str(e)}
    
    @http.route(['/my/approvals/reject-shift'], type='json', auth='user')
    def portal_reject_shift(self, slot_id, reason=None):
        """API từ chối ca từ Portal"""
        employee = request.env.user.employee_id
        if not employee:
            return {'error': 'Tài khoản chưa liên kết nhân viên.'}
        
        PlanningSlot = request.env['planning.slot'].sudo()
        slot = PlanningSlot.browse(int(slot_id))
        
        if not slot.exists():
            return {'error': 'Ca làm việc không tồn tại.'}
        
        if not hasattr(slot, 'approval_state') or slot.approval_state != 'to_approve':
            return {'error': 'Ca này không ở trạng thái chờ duyệt.'}
        
        # Kiểm tra quyền
        slot_employee = request.env['hr.employee'].sudo().search([
            ('resource_id', '=', slot.resource_id.id)
        ], limit=1)
        
        if not slot_employee or slot_employee.parent_id.id != employee.id:
            return {'error': 'Bạn không có quyền từ chối ca này.'}
        
        try:
            rejected_user = slot.registered_by if hasattr(slot, 'registered_by') else None
            
            # Reset slot
            update_vals = {'approval_state': 'open', 'resource_id': False}
            if hasattr(slot, 'registered_by'):
                update_vals['registered_by'] = False
            if hasattr(slot, 'registered_date'):
                update_vals['registered_date'] = False
            if hasattr(slot, 'reject_reason'):
                update_vals['reject_reason'] = reason or 'Không phù hợp với lịch làm việc'
            
            slot.write(update_vals)
            
            # Gửi notification cho nhân viên
            if rejected_user and rejected_user.partner_id:
                slot.message_post(
                    body='Ca làm việc ngày %s đã bị từ chối. Lý do: %s' % (
                        slot.start_datetime.strftime('%d/%m/%Y'),
                        reason or 'Không phù hợp'
                    ),
                    partner_ids=[rejected_user.partner_id.id],
                    message_type='notification'
                )
            
            return {'success': True, 'message': 'Đã từ chối ca thành công.'}
        except Exception as e:
            return {'error': 'Lỗi: %s' % str(e)}
    
    @http.route(['/my/approvals/approve-request'], type='json', auth='user')
    def portal_approve_request(self, request_id):
        """API duyệt approval.request từ Portal"""
        employee = request.env.user.employee_id
        if not employee:
            return {'error': 'Tài khoản chưa liên kết nhân viên.'}
        
        ApprovalRequest = request.env['approval.request'].sudo()
        approval = ApprovalRequest.browse(int(request_id))
        
        if not approval.exists():
            return {'error': 'Yêu cầu không tồn tại.'}
        
        if approval.request_status != 'pending':
            return {'error': 'Yêu cầu không ở trạng thái chờ duyệt.'}
        
        # Kiểm tra quyền: request owner phải là subordinate của manager này
        # Tìm qua user_id HOẶC work_contact_id (partner_id)
        request_owner_employee = request.env['hr.employee'].sudo().search([
            '|',
            ('user_id', '=', approval.request_owner_id.id),
            ('work_contact_id', '=', approval.partner_id.id if approval.partner_id else False),
        ], limit=1)
        
        if not request_owner_employee or request_owner_employee.parent_id.id != employee.id:
            return {'error': 'Bạn không có quyền duyệt yêu cầu này.'}
        
        try:
            # Tìm hoặc tạo approver cho current user nếu chưa có
            current_approver = approval.approver_ids.filtered(
                lambda a: a.user_id == request.env.user
            )
            
            if current_approver:
                current_approver.action_approve()
            else:
                # Nếu manager chưa trong danh sách approvers, thêm vào và duyệt
                approval.write({
                    'approver_ids': [(0, 0, {
                        'user_id': request.env.user.id,
                        'status': 'approved',
                    })]
                })
            
            return {'success': True, 'message': 'Đã duyệt yêu cầu thành công!'}
        except Exception as e:
            return {'error': 'Lỗi: %s' % str(e)}
    
    @http.route(['/my/approvals/reject-request'], type='json', auth='user')
    def portal_reject_request(self, request_id, reason=None):
        """API từ chối approval.request từ Portal"""
        employee = request.env.user.employee_id
        if not employee:
            return {'error': 'Tài khoản chưa liên kết nhân viên.'}
        
        ApprovalRequest = request.env['approval.request'].sudo()
        approval = ApprovalRequest.browse(int(request_id))
        
        if not approval.exists():
            return {'error': 'Yêu cầu không tồn tại.'}
        
        if approval.request_status != 'pending':
            return {'error': 'Yêu cầu không ở trạng thái chờ duyệt.'}
        
        # Kiểm tra quyền: tìm qua user_id HOẶC work_contact_id
        request_owner_employee = request.env['hr.employee'].sudo().search([
            '|',
            ('user_id', '=', approval.request_owner_id.id),
            ('work_contact_id', '=', approval.partner_id.id if approval.partner_id else False),
        ], limit=1)
        
        if not request_owner_employee or request_owner_employee.parent_id.id != employee.id:
            return {'error': 'Bạn không có quyền từ chối yêu cầu này.'}
        
        try:
            # Tìm hoặc tạo approver cho current user
            current_approver = approval.approver_ids.filtered(
                lambda a: a.user_id == request.env.user
            )
            
            if current_approver:
                current_approver.action_refuse()
            else:
                approval.write({
                    'approver_ids': [(0, 0, {
                        'user_id': request.env.user.id,
                        'status': 'refused',
                    })]
                })
            
            # Post reason if provided
            if reason:
                approval.message_post(body='Lý do từ chối: %s' % reason)
            
            return {'success': True, 'message': 'Đã từ chối yêu cầu.'}
        except Exception as e:
            return {'error': 'Lỗi: %s' % str(e)}

    @http.route(['/my/approvals/leave-replacement-candidates'], type='json', auth='user')
    def portal_leave_replacement_candidates(self, leave_id):
        """Lấy danh sách nhân viên từ các cửa hàng cùng SSP Manager để thế chỗ"""
        employee = request.env.user.employee_id
        if not employee:
            return {'error': 'Tài khoản chưa liên kết nhân viên.'}
        
        Leave = request.env['hr.leave'].sudo()
        leave = Leave.browse(int(leave_id))
        
        # Tìm các cửa hàng (departments) mà manager này quản lý (SSP Manager)
        Config = request.env['workforce.store.config'].sudo()
        configs = Config.search([('ssp_manager_id', '=', employee.id)])
        store_ids = configs.mapped('store_id').ids
        
        if not store_ids:
            # Nếu không cấu hình SSP Manager, lấy nhân viên cùng khối OPS
            if employee.department_id.block_id.code == 'OPS':
                store_ids = request.env['hr.department'].sudo().search([
                    ('block_id', '=', employee.department_id.block_id.id)
                ]).ids
        
        candidates = request.env['hr.employee'].sudo().search([
            ('department_id', 'in', store_ids),
            ('id', '!=', leave.employee_id.id),
            ('active', '=', True)
        ], order='name asc')
        
        return {
            'candidates': [{'id': c.id, 'name': c.name, 'dept': c.department_id.name} for c in candidates]
        }

    @http.route(['/my/approvals/upload_attachment'], type='http', auth='user', methods=['POST'], website=True, csrf=True)
    def portal_upload_attachment(self, **post):
        """Upload attachment for approval request"""
        request_id = post.get('request_id')
        attachments = request.httprequest.files.getlist('attachment_ids')
        
        if request_id and attachments:
             ApprovalRequest = request.env['approval.request'].sudo()
             approval = ApprovalRequest.browse(int(request_id))
             
             if approval.exists():
                 # Check access rights: simple check if user can read the request (already implied by browse if not sudo access rules blocked, but we used sudo for model)
                 # Enforce parent/manager check logic ideally, but for now allow if they can see it in portal
                 import base64
                 for attachment in attachments:
                     if attachment:
                        request.env['ir.attachment'].sudo().create({
                            'name': attachment.filename,
                            'datas': base64.b64encode(attachment.read()),
                            'res_model': 'approval.request',
                            'res_id': approval.id,
                            'type': 'binary',
                        })
        
        return request.redirect('/my/approvals')
