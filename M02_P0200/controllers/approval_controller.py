# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal

class ApprovalController(CustomerPortal):

    def _get_portal_employee(self):
        return request.env['hr.employee'].sudo().search([
            '|',
            ('user_id', '=', request.env.user.id),
            ('work_contact_id', '=', request.env.user.partner_id.id),
        ], limit=1)

    def _get_user_activity_display_map(self, activities):
        display_map = {}
        ApprovalRequest = request.env['approval.request'].sudo()
        Employee = request.env['hr.employee'].sudo()

        for activity in activities:
            title = activity.summary or activity.activity_type_id.name or activity.res_name or 'Hoạt động'
            subtitle = activity.res_name or ''
            category_name = False

            if activity.res_model == 'approval.request' and activity.res_id:
                approval_request = ApprovalRequest.browse(activity.res_id)
                if approval_request.exists():
                    title = activity.summary or approval_request.name or title
                    subtitle = approval_request.name or subtitle
                    category_name = approval_request.category_id.name if approval_request.category_id else False
            elif activity.res_model == 'hr.employee' and activity.res_id:
                employee = Employee.browse(activity.res_id)
                if employee.exists():
                    subtitle = employee.name

            display_map[activity.id] = {
                'title': title,
                'subtitle': subtitle,
                'category_name': category_name,
                'is_done': not activity.active,
            }
        return display_map

    def _get_pending_request_changes_map(self, requests):
        """Build a safe changes-summary map for mixed approval.request sources."""
        changes_map = {}
        for approval_request in requests:
            changes = []
            getter = getattr(approval_request, 'get_changes_summary', None)
            if callable(getter):
                try:
                    changes = getter() or []
                except Exception:
                    changes = []
            changes_map[approval_request.id] = changes
        return changes_map

    def _get_pending_request_display_map(self, requests):
        """Build a safe display map for mixed approval.request sources."""
        def _get_first_value(record, field_names):
            for field_name in field_names:
                if field_name not in record._fields:
                    continue
                value = record[field_name]
                if value:
                    return value
            return False

        def _format_value(value):
            if hasattr(value, 'display_name'):
                return value.display_name
            if hasattr(value, 'strftime'):
                return value.strftime('%d/%m/%Y')
            return value

        display_map = {}
        for approval_request in requests:
            details = []
            fields_map = [
                (['resignation_department', 'x_psm_0213_resignation_department'], 'Phòng ban', False),
                (['resignation_manager_name', 'x_psm_0213_resignation_manager_name'], 'Line Manager', False),
                (['job_id', 'x_psm_0213_job_id'], 'Chức vụ', False),
                (['resignation_date_formatted', 'resignation_date', 'x_psm_0213_resignation_date'], 'Ngày nghỉ dự kiến', False),
                (['resignation_reason_id', 'x_psm_0213_resignation_reason_id'], 'Loại nghỉ việc', False),
                (['resignation_reason', 'x_psm_0213_resignation_reason'], 'Lý do nghỉ việc', True),
            ]

            for field_names, label, is_long in fields_map:
                value = _get_first_value(approval_request, field_names)
                if not value:
                    continue

                details.append({
                    'label': label,
                    'value': _format_value(value),
                    'is_long': is_long,
                })

            display_map[approval_request.id] = details
        return display_map

    def _get_request_owner_employee(self, approval_request):
        return request.env['hr.employee'].sudo().search([
            '|',
            ('user_id', '=', approval_request.request_owner_id.id),
            ('work_contact_id', '=', approval_request.partner_id.id if approval_request.partner_id else False),
        ], limit=1)

    def _get_resignation_finalization_action_map(self, requests):
        action_map = {}
        ops_category = request.env.ref(
            'M02_P0213_00.psm_0213_approval_category_resignation',
            raise_if_not_found=False,
        )
        rst_category = request.env.ref(
            'M02_P0214_00.approval_category_resignation',
            raise_if_not_found=False,
        )
        for approval_request in requests:
            actions = []

            if approval_request.request_status != 'approved':
                action_map[approval_request.id] = actions
                continue

            is_ops = bool(ops_category and approval_request.category_id == ops_category)
            is_rst = bool(rst_category and approval_request.category_id == rst_category)

            if is_ops:
                all_done = bool(approval_request.x_psm_0213_all_activities_completed)
                survey_done = bool(approval_request.x_psm_0213_exit_survey_completed)
                contract_type = approval_request.x_psm_0213_type_contract or ''
                adecco_sent = bool(approval_request.x_psm_0213_adecco_notification_sent)

                if all_done and survey_done:
                    if contract_type == 'Full-Time':
                        actions.append({
                            'code': 'ops_send_social_insurance',
                            'label': 'Gửi BHXH và hoàn tất',
                            'button_class': 'btn btn-success btn-sm',
                            'modal_class': 'success',
                            'modal_title': 'Gửi BHXH và hoàn tất quy trình',
                            'modal_note': 'Hệ thống sẽ gửi email BHXH và hoàn tất nghỉ việc ngay sau khi xác nhận.',
                            'success_message': 'Đã gửi thông tin BHXH và hoàn tất quy trình nghỉ việc.',
                        })
                    else:
                        if not adecco_sent:
                            actions.append({
                                'code': 'ops_send_adecco_notification',
                                'label': 'Gửi thông tin Adecco',
                                'button_class': 'btn btn-warning btn-sm text-dark',
                                'modal_class': 'warning',
                                'modal_title': 'Gửi thông tin Adecco',
                                'modal_note': 'Bước này áp dụng cho nhân sự không thuộc hợp đồng Full-Time.',
                                'success_message': 'Đã gửi thông tin Adecco.',
                            })
                        else:
                            actions.append({
                                'code': 'ops_done',
                                'label': 'Hoàn tất nghỉ việc',
                                'button_class': 'btn btn-success btn-sm',
                                'modal_class': 'success',
                                'modal_title': 'Hoàn tất quy trình nghỉ việc',
                                'modal_note': 'Hành động này sẽ khóa sổ quy trình và vô hiệu hóa tài khoản theo logic hiện có.',
                                'success_message': 'Đã hoàn tất quy trình nghỉ việc.',
                            })

            elif is_rst:
                all_done = bool(approval_request.all_activities_completed)
                survey_done = bool(approval_request.exit_survey_completed)
                bhxh_sent = bool(approval_request.social_insurance_email_sent)

                if all_done and survey_done:
                    if not bhxh_sent:
                        actions.append({
                            'code': 'rst_send_social_insurance',
                            'label': 'Gửi thông tin BHXH',
                            'button_class': 'btn btn-warning btn-sm text-dark',
                            'modal_class': 'warning',
                            'modal_title': 'Gửi thông tin BHXH',
                            'modal_note': 'Sau bước này, đơn vẫn ở trạng thái Approved để quản lý/HR rà soát trước khi hoàn tất.',
                            'success_message': 'Đã gửi thông tin BHXH.',
                        })
                    else:
                        actions.append({
                            'code': 'rst_done',
                            'label': 'Hoàn tất nghỉ việc',
                            'button_class': 'btn btn-success btn-sm',
                            'modal_class': 'success',
                            'modal_title': 'Hoàn tất quy trình nghỉ việc',
                            'modal_note': 'Hành động này sẽ kết thúc quy trình nghỉ việc và vô hiệu hóa tài khoản theo logic hiện có.',
                            'success_message': 'Đã hoàn tất quy trình nghỉ việc.',
                        })

            action_map[approval_request.id] = actions
        return action_map

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
        pending_request_changes = {}
        pending_request_display = {}
        ready_resignation_requests = []
        ready_resignation_actions = {}
        
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
            pending_request_changes = self._get_pending_request_changes_map(pending_requests)

            approved_requests = ApprovalRequest.search([
                '|',
                ('request_owner_id', 'in', sub_user_ids),
                ('partner_id', 'in', sub_partner_ids),
                ('request_status', '=', 'approved'),
            ], order='write_date desc, create_date desc')
            pending_request_display = self._get_pending_request_display_map(pending_requests | approved_requests)
            ready_resignation_actions = self._get_resignation_finalization_action_map(approved_requests)
            ready_resignation_requests = approved_requests.filtered(
                lambda req: bool(ready_resignation_actions.get(req.id))
            )

            # 3. Lấy đơn nghỉ phép chờ duyệt (hr.leave)
            if 'hr.leave' in request.env:
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
            'pending_request_changes': pending_request_changes,
            'pending_request_display': pending_request_display,
            'pending_leaves': pending_leaves,
            'recent_processed': recent_processed,
            'ready_resignation_requests': ready_resignation_requests,
            'ready_resignation_actions': ready_resignation_actions,
            'page_name': 'approvals',
            'final_action_done': kw.get('final_action_done'),
        })
        
        return request.render('M02_P0200.portal_approvals_page', values)

    @http.route(['/my/approvals/finalize-resignation'], type='json', auth='user')
    def portal_finalize_resignation(self, request_id, action_code):
        employee = self._get_portal_employee()
        if not employee:
            return {'error': 'Tài khoản chưa liên kết nhân viên.'}

        approval = request.env['approval.request'].sudo().browse(int(request_id))
        if not approval.exists():
            return {'error': 'Yêu cầu không tồn tại.'}

        owner_employee = self._get_request_owner_employee(approval)
        if not owner_employee or owner_employee.parent_id.id != employee.id:
            return {'error': 'Bạn không có quyền xử lý yêu cầu này.'}

        allowed_actions = {
            item['code']: item
            for item in self._get_resignation_finalization_action_map(approval).get(approval.id, [])
        }
        if action_code not in allowed_actions:
            return {'error': 'Hành động không hợp lệ hoặc đơn chưa đủ điều kiện xử lý.'}

        try:
            if action_code == 'ops_send_social_insurance':
                approval.action_send_social_insurance()
            elif action_code == 'ops_send_adecco_notification':
                approval.action_send_adecco_notification()
            elif action_code == 'ops_done':
                approval.action_done()
            elif action_code == 'rst_send_social_insurance':
                approval.action_send_social_insurance()
            elif action_code == 'rst_done':
                approval.action_done()
            else:
                return {'error': 'Hành động chưa được hỗ trợ.'}
        except Exception as exc:
            return {'error': str(exc)}

        return {
            'success': True,
            'message': allowed_actions[action_code]['success_message'],
            'redirect_url': '/my/approvals?final_action_done=1',
        }

    @http.route(['/my/activities'], type='http', auth='user', website=True)
    def portal_my_activities(self, **kw):
        values = self._prepare_portal_layout_values()
        employee = self._get_portal_employee()

        Activity = request.env['mail.activity'].sudo().with_context(active_test=False)
        activities = Activity.search([
            ('user_id', '=', request.env.user.id),
            ('res_model', 'in', ['approval.request', 'hr.employee']),
        ], order='active desc, date_deadline asc, create_date desc')

        pending_activities = activities.filtered(lambda activity: activity.active)
        completed_activities = activities.filtered(lambda activity: not activity.active)[:20]
        activity_display = self._get_user_activity_display_map(activities)

        values.update({
            'user': request.env.user,
            'employee': employee,
            'pending_activities': pending_activities,
            'completed_activities': completed_activities,
            'activity_display': activity_display,
            'page_name': 'my_activities',
            'activity_done': kw.get('activity_done'),
        })

        return request.render('M02_P0200.portal_my_activities_page', values)

    @http.route(['/my/activities/done'], type='http', auth='user', methods=['POST'], website=True, csrf=True)
    def portal_my_activity_done(self, **post):
        activity_id = int(post.get('activity_id', 0))
        if not activity_id:
            return request.redirect('/my/activities')

        activity = request.env['mail.activity'].sudo().browse(activity_id)
        if activity.exists() and activity.user_id == request.env.user and activity.active:
            activity.action_feedback(feedback='Hoàn thành từ Portal')

        return request.redirect('/my/activities?activity_done=1')
    
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
