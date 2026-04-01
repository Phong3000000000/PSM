# -*- coding: utf-8 -*-
import pytz
from datetime import datetime, time, timedelta
from odoo import http, fields, _
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal


class WorkforcePortal(CustomerPortal):
    """
    Controller Portal cho nhân viên đăng ký ca làm việc
    Tích hợp với M02_P0206_00 và portal_custom
    """

    def _prepare_home_portal_values(self, counters):
        """
        Hiển thị số lượng ca trống, ca chờ duyệt và xác nhận công trên menu Portal Home
        (Đã gộp logic từ 2 hàm bị trùng tên trong code cũ)
        """
        values = super()._prepare_home_portal_values(counters)
        employee = request.env.user.employee_id
        
        # 1. Counter cho Ca làm việc (Shift)
        if 'shift_count' in counters:
            if employee:
                # Chỉ đếm ca trong kỳ đang mở
                domain = [
                    ('resource_id', '=', False),
                    ('start_datetime', '>=', fields.Datetime.now()),
                    ('state', '=', 'published'),
                    ('period_id.state', '=', 'open'),
                ]
                values['shift_count'] = request.env['planning.slot'].sudo().search_count(domain)
            else:
                values['shift_count'] = 0
        
        # 2. Counter cho menu "Duyệt ca nhân viên" (Manager)
        if 'approval_count' in counters:
            if employee:
                subordinates = request.env['hr.employee'].sudo().search([
                    ('parent_id', '=', employee.id)
                ])
                if subordinates:
                    sub_resource_ids = subordinates.mapped('resource_id').ids
                    values['approval_count'] = request.env['planning.slot'].sudo().search_count([
                        ('resource_id', 'in', sub_resource_ids),
                        ('approval_state', '=', 'to_approve'),
                        ('start_datetime', '>=', fields.Datetime.now()),
                    ])
                else:
                    values['approval_count'] = 0
            else:
                values['approval_count'] = 0

        # 3. Counter cho menu "Xác nhận công cuối tháng" (Timesheet Closing)
        if 'closing_count' in counters:
            if employee:
                MonthClosing = request.env['workforce.month.closing'].sudo()
                values['closing_count'] = MonthClosing.search_count([
                    ('employee_id', '=', employee.id),
                    ('state', '=', 'draft'),
                ])
            else:
                values['closing_count'] = 0
        
        return values

    def _get_shift_domain(self, employee, role_id=None, store_id=None):
        """Helper to get domain for planning slots"""
        domain = [
            ('start_datetime', '!=', False),
            ('end_datetime', '!=', False),
            ('employee_id', '=', employee.id),
        ]
        return domain

    @http.route(['/my/shifts', '/my/shifts/page/<int:page>'], type='http', auth="user", website=True)
    def portal_my_shifts(self, page=1, date=None, role_id=None, store_id=None, sortby=None, **kw):
        """ Hiển thị lịch đăng ký ca làm việc theo Role và Store """
        values = self._prepare_portal_layout_values()
        employee = request.env.user.employee_id
        if not employee:
            return request.redirect('/my')

        # 1. Fetch Stores
        stores = request.env['hr.department'].sudo().search([])
        if not store_id and stores:
            store_id = stores[0].id
        selected_store = request.env['hr.department'].sudo().browse(int(store_id)) if store_id else None

        PlanningSlot = request.env['planning.slot'].sudo()
        PlanningRole = request.env['planning.role'].sudo()

        # 1. Lấy danh sách Roles
        if hasattr(employee, 'skill_role_ids') and employee.skill_role_ids:
            available_roles = employee.skill_role_ids
        else:
            available_roles = PlanningRole.search([])
        
        # 2. Xác định role đang chọn
        selected_role = None
        if role_id:
            try:
                selected_role = PlanningRole.browse(int(role_id))
                if not selected_role.exists():
                    selected_role = available_roles[:1] if available_roles else None
            except:
                selected_role = available_roles[:1] if available_roles else None
        else:
            selected_role = available_roles[:1] if available_roles else None

        # 3. Xác định tuần hiển thị
        today = fields.Date.today()
        if date:
            try:
                current_date = fields.Date.from_string(date)
            except:
                current_date = today
        else:
            current_date = today

        start_of_week = current_date - timedelta(days=current_date.weekday())
        end_of_week = start_of_week + timedelta(days=6)
        
        prev_week = (start_of_week - timedelta(days=7)).strftime('%Y-%m-%d')
        next_week = (start_of_week + timedelta(days=7)).strftime('%Y-%m-%d')
        
        current_week_start = today - timedelta(days=today.weekday())
        next_week_start = current_week_start + timedelta(days=7)
        is_current_week_locked = start_of_week < next_week_start

        # Check Period
        period = request.env['planning.period'].sudo().search([
            ('date_from', '<=', start_of_week),
            ('date_to', '>=', end_of_week)
        ], limit=1)
        
        is_period_closed = False
        if period and period.state != 'open':
            is_period_closed = True

        # 4. Week days structure
        week_days = []
        day_names = ['Thứ 2', 'Thứ 3', 'Thứ 4', 'Thứ 5', 'Thứ 6', 'Thứ 7', 'Chủ nhật']
        for i in range(7):
            d = start_of_week + timedelta(days=i)
            week_days.append({
                'day_name': day_names[i],
                'day_str': d.strftime('%d/%m'),
                'date': d,
                'is_today': d == today,
            })

        # Fetch Shift Templates
        ShiftTemplate = request.env['workforce.shift.template'].sudo()
        template_domain = [('is_active', '=', True)]
        if selected_store:
            template_domain += ['|', ('store_id', '=', False), ('store_id', '=', selected_store.id)]
            
        templates = ShiftTemplate.search(template_domain, order='sequence, id')
        
        shift_frames = []
        for t in templates:
            def format_time(float_hour):
                h = int(float_hour)
                m = int((float_hour - h) * 60)
                return f"{h:02d}:{m:02d}"
                
            label = f"{t.name} ({format_time(t.start_hour)} - {format_time(t.end_hour)})"
            shift_frames.append({
                'id': t.id,
                'name': t.name,
                'start': t.start_hour,
                'end': t.end_hour,
                'label': label,
                'duration': t.duration,
            })

        # 6. Existing slots
        existing_slots = {}
        user_tz = pytz.timezone(request.env.user.tz or 'UTC')
        
        if selected_role:
            domain = [
                ('role_id', '=', selected_role.id),
                ('start_datetime', '>=', fields.Datetime.to_datetime(start_of_week)),
                ('start_datetime', '<', fields.Datetime.to_datetime(end_of_week) + timedelta(days=2)),
            ]
            if selected_store:
                domain.append(('store_id', '=', selected_store.id))
                
            slots = PlanningSlot.search(domain)
            
            for slot in slots:
                start_dt_utc = slot.start_datetime
                if not start_dt_utc: 
                    continue
                    
                start_dt_user = pytz.utc.localize(start_dt_utc).astimezone(user_tz)
                date_key = start_dt_user.strftime('%Y-%m-%d')
                slot_hour = start_dt_user.hour + start_dt_user.minute / 60.0
                
                matched_template_id = None
                min_diff = 1.0 
                for t in templates:
                    diff = abs(slot_hour - t.start_hour)
                    if diff < min_diff:
                        min_diff = diff
                        matched_template_id = t.id
                
                if matched_template_id:
                    key = f"{date_key}_{matched_template_id}"
                    existing_slots[key] = slot

        # 7. Schedule Grid
        schedule = {t.id: {} for t in templates}

        for i in range(7):
            d = start_of_week + timedelta(days=i)
            date_key = d.strftime('%Y-%m-%d')
            is_date_locked = (d < next_week_start) or is_period_closed
            
            for frame in shift_frames:
                t_id = frame['id']
                key = f"{date_key}_{t_id}"
                slot = existing_slots.get(key)
                
                shift_info = {
                    'date': d,
                    'date_key': date_key,
                    'template_id': t_id,
                    'role_id': selected_role.id if selected_role else None,
                    'start_hour': frame['start'],
                    'end_hour': frame['end'],
                }
                
                if slot:
                    if slot.resource_id:
                        if slot.resource_id.id == employee.resource_id.id:
                            # Ca của tôi
                            schedule[t_id][date_key] = {
                                'status': 'mine',
                                'slot': slot,
                                'shift_info': shift_info,
                                'is_locked': is_date_locked,
                            }
                        else:
                            # Đã có người khác
                            schedule[t_id][date_key] = {
                                'status': 'taken',
                                'slot': slot,
                                'shift_info': shift_info,
                                'is_locked': is_date_locked,
                            }
                            # [FIX] Removed extra '}' here
                else:
                    # Chưa có slot
                    status = 'unavailable'
                    schedule[t_id][date_key] = {
                        'status': status,
                        'slot': None,
                        'shift_info': shift_info,
                        'is_locked': is_date_locked,
                    }

        is_fulltime = getattr(employee, 'employment_type', None) == 'full_time'
        
        values.update({
            'employee': employee,
            'is_fulltime': is_fulltime,
            'page_name': 'shifts',
            'week_days': week_days,
            'prev_week': prev_week,
            'next_week': next_week,
            'schedule': schedule,
            'shift_frames': shift_frames,
            'available_roles': available_roles,
            'selected_role': selected_role,
            'stores': stores,
            'selected_store': selected_store,
            'is_current_week_locked': is_current_week_locked,
            'is_period_closed': is_period_closed,
            'next_week_start': next_week_start,
        })
        
        return request.render("M02_P0206_00.portal_my_shifts_calendar", values)

    @http.route(['/my/shifts/register-new'], type='json', auth="user")
    def register_new_shift(self, role_id, date_str, template_id, store_id=None):
        """ API đăng ký ca MỚI """
        employee = request.env.user.employee_id
        if not employee:
            return {'error': 'Tài khoản chưa liên kết với hồ sơ nhân viên.'}

        PlanningSlot = request.env['planning.slot'].sudo()
        PlanningRole = request.env['planning.role'].sudo()
        
        role = PlanningRole.browse(int(role_id))
        if not role.exists():
            return {'error': 'Vị trí công việc không hợp lệ.'}
        
        try:
            slot_date = fields.Date.from_string(date_str)
        except:
            return {'error': 'Ngày không hợp lệ.'}
        
        today = fields.Date.today()
        current_week_start = today - timedelta(days=today.weekday())
        next_week_start = current_week_start + timedelta(days=7)
        
        if slot_date < next_week_start:
            return {'error': 'Chỉ được đăng ký ca từ tuần tới trở đi.'}

        period = request.env['planning.period'].sudo().search([
            ('date_from', '<=', slot_date),
            ('date_to', '>=', slot_date)
        ], limit=1)
        
        if period and period.state != 'open':
            return {'error': 'Kỳ đăng ký (%s) chưa mở hoặc đã đóng.' % period.name}
        
        template = request.env['workforce.shift.template'].sudo().browse(int(template_id))
        if not template.exists():
            return {'error': 'Mẫu ca làm việc không tồn tại.'}
            
        start_hour = template.start_hour
        end_hour = template.end_hour
        
        def float_to_time(f):
            h = int(f)
            m = int((f - h) * 60)
            return h, m

        sh, sm = float_to_time(start_hour)
        eh, em = float_to_time(end_hour)
        
        user_tz = pytz.timezone(request.env.user.tz or 'UTC')
        
        local_dt_start = datetime.combine(slot_date, time(hour=sh, minute=sm))
        start_dt_aware = user_tz.localize(local_dt_start)
        start_dt = start_dt_aware.astimezone(pytz.utc).replace(tzinfo=None)
        
        if end_hour < start_hour:
            local_dt_end = datetime.combine(slot_date + timedelta(days=1), time(hour=eh, minute=em))
        else:
            local_dt_end = datetime.combine(slot_date, time(hour=eh, minute=em))
            
        end_dt_aware = user_tz.localize(local_dt_end)
        end_dt = end_dt_aware.astimezone(pytz.utc).replace(tzinfo=None)
        
        existing = PlanningSlot.search([
            ('role_id', '=', role.id),
            ('start_datetime', '=', start_dt),
            ('end_datetime', '=', end_dt),
        ], limit=1)
        
        if existing:
            if existing.resource_id:
                if existing.resource_id.id == employee.resource_id.id:
                    return {'error': 'Bạn đã đăng ký ca này rồi.'}
                else:
                    return {'error': 'Ca này đã có người khác đăng ký.'}
            else:
                return self._do_register(existing, employee)
        
        # Validations
        if hasattr(employee, 'skill_role_ids') and employee.skill_role_ids:
            if role not in employee.skill_role_ids:
                return {'error': 'Bạn chưa được đào tạo vị trí "%s".' % role.name}
        
        overlap_domain = [
            ('resource_id', '=', employee.resource_id.id),
            ('start_datetime', '<', end_dt),
            ('end_datetime', '>', start_dt),
            ('approval_state', 'in', ['to_approve', 'approved']),
        ]
        if PlanningSlot.search_count(overlap_domain) > 0:
            return {'error': 'Bạn đã có ca làm trùng khung giờ này.'}
        
        if hasattr(employee, 'max_hours_week') and hasattr(employee, 'get_week_worked_hours'):
            week_start = slot_date - timedelta(days=slot_date.weekday())
            week_end = week_start + timedelta(days=6)
            current_hours = employee.get_week_worked_hours(week_start, week_end)
            slot_hours = (end_dt - start_dt).total_seconds() / 3600
            if current_hours + slot_hours > employee.max_hours_week:
                return {'error': 'Vượt quá giới hạn giờ làm việc.'}
        
        # [FIX] Added try block for creation
        try:
            vals = {
                'resource_id': employee.resource_id.id,
                'role_id': int(role_id),
                'start_datetime': start_dt,
                'end_datetime': end_dt,
                'period_id': period.id,
                'registered_by': request.env.user.id,
                'registered_date': fields.Datetime.now(),
                'approval_state': 'to_approve',
                'state': 'published',
            }
            
            if store_id:
                vals['store_id'] = int(store_id)
                
            slot = PlanningSlot.create(vals)
            
            # Notify manager
            self._notify_manager(employee, slot)
            
            return {
                'success': True,
                'message': 'Đăng ký thành công! Chờ RGM duyệt.',
                'slot_id': slot.id,
            }
        except Exception as e:
            return {'error': 'Lỗi hệ thống: %s' % str(e)}

    def _do_register(self, slot, employee):
        """Helper: Đăng ký vào slot có sẵn"""
        try:
            slot.write({
                'resource_id': employee.resource_id.id,
                'approval_state': 'to_approve',
                'registered_by': request.env.uid,
                'registered_date': fields.Datetime.now(),
            })
            self._notify_manager(employee, slot)
            return {
                'success': True,
                'message': 'Đăng ký thành công! Chờ RGM duyệt.',
                'slot_id': slot.id,
            }
        except Exception as e:
            return {'error': 'Lỗi hệ thống: %s' % str(e)}

    @http.route(['/my/shifts/register'], type='json', auth="user")
    def register_shift(self, slot_id):
        """ API đăng ký ca """
        employee = request.env.user.employee_id
        if not employee:
            return {'error': 'Tài khoản chưa liên kết với hồ sơ nhân viên.'}

        PlanningSlot = request.env['planning.slot'].sudo()
        slot = PlanningSlot.browse(int(slot_id))
        
        if not slot.exists():
            return {'error': 'Ca làm việc không tồn tại.'}
        if slot.resource_id:
            return {'error': 'Ca này đã có người đăng ký!'}
        if slot.state != 'published':
            return {'error': 'Ca này chưa được mở đăng ký.'}
        
        if slot.period_id and slot.period_id.state != 'open':
            return {'error': 'Kỳ đăng ký chưa mở hoặc đã đóng.'}
        
        if slot.role_id:
            employee_skills = employee.skill_role_ids if hasattr(employee, 'skill_role_ids') else []
            if employee_skills and slot.role_id not in employee_skills:
                return {'error': 'Bạn chưa được đào tạo vị trí này.'}
        
        overlap_domain = [
            ('resource_id', '=', employee.resource_id.id), 
            ('start_datetime', '<', slot.end_datetime), 
            ('end_datetime', '>', slot.start_datetime),
            ('approval_state', 'in', ['to_approve', 'approved']),
        ]
        if PlanningSlot.search_count(overlap_domain) > 0:
            return {'error': 'Bạn đã có ca làm trùng khung giờ này.'}
        
        if hasattr(employee, 'max_hours_week') and hasattr(employee, 'get_week_worked_hours'):
            slot_date = slot.start_datetime.date()
            week_start = slot_date - timedelta(days=slot_date.weekday())
            week_end = week_start + timedelta(days=6)
            current_hours = employee.get_week_worked_hours(week_start, week_end)
            slot_hours = slot.allocated_hours or 0
            if current_hours + slot_hours > employee.max_hours_week:
                return {'error': 'Vượt quá giới hạn giờ làm việc.'}
        
        if hasattr(slot, 'max_capacity') and slot.max_capacity > 0:
            current_count = PlanningSlot.search_count([
                ('start_datetime', '=', slot.start_datetime),
                ('end_datetime', '=', slot.end_datetime),
                ('role_id', '=', slot.role_id.id if slot.role_id else False),
                ('resource_id', '!=', False),
            ])
            if current_count >= slot.max_capacity:
                return {'error': 'Ca này đã đủ người.'}
        
        try:
            slot.write({
                'resource_id': employee.resource_id.id,
                'approval_state': 'to_approve',
                'registered_by': request.env.uid,
                'registered_date': fields.Datetime.now(),
            })
            self._notify_manager(employee, slot)
            return {
                'success': True, 
                'message': 'Đăng ký thành công! Chờ RGM duyệt.'
            }
        except Exception as e:
            return {'error': 'Lỗi hệ thống: %s' % str(e)}

    def _notify_manager(self, employee, slot):
        """Gửi Activity notification cho Manager"""
        manager = employee.parent_id.user_id if employee.parent_id else None
        if not manager:
            manager = request.env.ref('base.user_admin', raise_if_not_found=False)
        
        if manager:
            activity_type = request.env.ref('mail.mail_activity_data_todo', raise_if_not_found=False)
            model_ref = request.env['ir.model'].sudo().search([('model', '=', 'planning.slot')], limit=1)
            
            if activity_type and model_ref:
                request.env['mail.activity'].sudo().create({
                    'activity_type_id': activity_type.id,
                    'summary': 'Duyệt ca: %s đăng ký' % employee.name,
                    'note': 'Nhân viên %s đăng ký ca %s - %s. Vui lòng duyệt.' % (
                        employee.name,
                        slot.start_datetime.strftime('%d/%m %H:%M'),
                        slot.end_datetime.strftime('%H:%M')
                    ),
                    'res_id': slot.id,
                    'res_model_id': model_ref.id,
                    'user_id': manager.id,
                })

    @http.route(['/my/shifts/unregister'], type='json', auth="user")
    def unregister_shift(self, slot_id):
        """Hủy đăng ký ca"""
        employee = request.env.user.employee_id
        if not employee:
            return {'error': 'Tài khoản chưa liên kết với hồ sơ nhân viên.'}

        slot = request.env['planning.slot'].sudo().browse(int(slot_id))
        
        if not slot.exists():
            return {'error': 'Ca làm việc không tồn tại.'}
        if slot.resource_id.id != employee.resource_id.id:
            return {'error': 'Bạn không thể hủy ca của người khác.'}
        
        if hasattr(slot, 'approval_state') and slot.approval_state == 'approved':
            if slot.start_datetime <= fields.Datetime.now():
                return {'error': 'Không thể hủy ca đã được duyệt và bắt đầu.'}
        
        try:
            slot.write({
                'resource_id': False,
                'approval_state': 'open',
                'registered_by': False,
                'registered_date': False,
            })
            return {'success': True, 'message': 'Đã hủy đăng ký thành công.'}
        except Exception as e:
            return {'error': str(e)}

    @http.route(['/my/shifts/cancel'], type='json', auth="user")
    def cancel_shift(self, slot_id):
        return self.unregister_shift(slot_id)

    # =========================================================
    # PORTAL APPROVAL
    # =========================================================
    @http.route(['/my/team/approvals'], type='http', auth="user", website=True)
    def portal_team_approvals(self, **kw):
        """ Trang duyệt ca cho Line Manager """
        values = self._prepare_portal_layout_values()
        
        employee = request.env.user.employee_id
        if not employee:
            return request.render('M02_P0206_00.portal_no_employee', {
                'message': 'Tài khoản chưa liên kết với hồ sơ nhân viên.'
            })
        
        PlanningSlot = request.env['planning.slot'].sudo()
        subordinates = request.env['hr.employee'].sudo().search([
            ('parent_id', '=', employee.id)
        ])
        
        if not subordinates:
            pending_shifts = PlanningSlot.browse()
        else:
            sub_resource_ids = subordinates.mapped('resource_id').ids
            pending_shifts = PlanningSlot.search([
                ('resource_id', 'in', sub_resource_ids),
                ('approval_state', '=', 'to_approve'),
                ('start_datetime', '>=', fields.Datetime.now()),
            ], order='start_datetime asc')
        
        week_ago = datetime.now() - timedelta(days=7)
        if subordinates:
            sub_resource_ids = subordinates.mapped('resource_id').ids
            recent_approved = PlanningSlot.search([
                ('resource_id', 'in', sub_resource_ids),
                ('approval_state', 'in', ['approved', 'rejected']),
                ('write_date', '>=', week_ago),
            ], order='write_date desc', limit=20)
        else:
            recent_approved = PlanningSlot.browse()
        
        values.update({
            'employee': employee,
            'subordinates': subordinates,
            'pending_shifts': pending_shifts,
            'recent_approved': recent_approved,
            'page_name': 'team_approvals',
        })
        
        return request.render("M02_P0206_00.portal_team_approvals", values)

    @http.route(['/my/team/approve'], type='json', auth="user")
    def portal_approve_shift(self, slot_id):
        """API duyệt ca"""
        employee = request.env.user.employee_id
        if not employee:
            return {'error': 'Tài khoản chưa liên kết nhân viên.'}
        
        PlanningSlot = request.env['planning.slot'].sudo()
        slot = PlanningSlot.browse(int(slot_id))
        
        if not slot.exists():
            return {'error': 'Ca làm việc không tồn tại.'}
        
        if slot.approval_state != 'to_approve':
            return {'error': 'Ca này không ở trạng thái chờ duyệt.'}
        
        slot_employee = request.env['hr.employee'].sudo().search([
            ('resource_id', '=', slot.resource_id.id)
        ], limit=1)
        
        if not slot_employee or slot_employee.parent_id.id != employee.id:
            return {'error': 'Bạn không có quyền duyệt ca này.'}
        
        try:
            slot.write({'approval_state': 'approved'})
            if slot.registered_by and slot.registered_by.partner_id:
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

    @http.route(['/my/team/reject'], type='json', auth="user")
    def portal_reject_shift(self, slot_id, reason=None):
        """API từ chối ca"""
        employee = request.env.user.employee_id
        if not employee:
            return {'error': 'Tài khoản chưa liên kết nhân viên.'}
        
        PlanningSlot = request.env['planning.slot'].sudo()
        slot = PlanningSlot.browse(int(slot_id))
        
        if not slot.exists():
            return {'error': 'Ca làm việc không tồn tại.'}
        
        if slot.approval_state != 'to_approve':
            return {'error': 'Ca này không ở trạng thái chờ duyệt.'}
        
        slot_employee = request.env['hr.employee'].sudo().search([
            ('resource_id', '=', slot.resource_id.id)
        ], limit=1)
        
        if not slot_employee or slot_employee.parent_id.id != employee.id:
            return {'error': 'Bạn không có quyền từ chối ca này.'}
        
        try:
            rejected_user = slot.registered_by
            slot.write({
                'approval_state': 'open',
                'resource_id': False,
                'registered_by': False,
                'registered_date': False,
                'reject_reason': reason or 'Không phù hợp với lịch làm việc',
            })
            if rejected_user and rejected_user.partner_id:
                slot.message_post(
                    body='Ca làm việc ngày %s đã bị từ chối. Lý do: %s' % (
                        slot.start_datetime.strftime('%d/%m/%Y'),
                        reason or 'Không phù hợp'
                    ),
                    partner_ids=[rejected_user.partner_id.id],
                    message_type='notification'
                )
            return {'success': True, 'message': 'Đã từ chối ca.'}
        except Exception as e:
            return {'error': 'Lỗi: %s' % str(e)}

    # =========================================================
    # TIMESHEET PORTAL
    # =========================================================
    @http.route(['/my/timesheets'], type='http', auth="user", website=True)
    def portal_my_timesheets(self, **kw):
        """Hiển thị bảng công tháng"""
        values = self._prepare_portal_layout_values()
        employee = request.env.user.employee_id
        if not employee:
            return request.render('M02_P0206_00.portal_no_employee', {
                'message': 'Tài khoản chưa liên kết với hồ sơ nhân viên.'
            })
        
        today = fields.Date.today()
        first_day = today.replace(day=1)
        
        Attendance = request.env['hr.attendance'].sudo()
        attendances = Attendance.search([
            ('employee_id', '=', employee.id),
            ('check_in', '>=', first_day),
        ], order='check_in desc')
        
        total_hours = sum(att.worked_hours for att in attendances)
        Correction = request.env['attendance.correction'].sudo()
        correction_count = Correction.search_count([
            ('employee_id', '=', employee.id),
            ('create_date', '>=', first_day),
        ])
        
        values.update({
            'employee': employee,
            'attendances': attendances,
            'total_hours': total_hours,
            'correction_count': correction_count,
            'correction_remaining': max(0, 3 - correction_count),
            'page_name': 'timesheets',
        })
        
        return request.render("M02_P0206_00.portal_my_timesheets", values)

    @http.route(['/my/timesheets/correction'], type='http', auth="user", website=True, methods=['GET', 'POST'])
    def portal_correction_form(self, **kw):
        """Form yêu cầu sửa công"""
        employee = request.env.user.employee_id
        if not employee:
            return request.redirect('/my')
        
        today = fields.Date.today()
        first_day = today.replace(day=1)
        Correction = request.env['attendance.correction'].sudo()
        correction_count = Correction.search_count([
            ('employee_id', '=', employee.id),
            ('create_date', '>=', first_day),
        ])
        
        if correction_count >= 3:
            return request.render('M02_P0206_00.portal_correction_limit', {
                'message': 'Bạn đã hết lượt sửa công trong tháng này.'
            })
        
        if request.httprequest.method == 'POST':
            vals = {
                'employee_id': employee.id,
                'date': kw.get('date'),
                'requested_check_in': kw.get('check_in'),
                'requested_check_out': kw.get('check_out'),
                'reason': kw.get('reason'),
            }
            Correction.create(vals)
            return request.redirect('/my/timesheets?success=1')
        
        values = self._prepare_portal_layout_values()
        values.update({
            'employee': employee,
            'correction_remaining': 3 - correction_count,
            'page_name': 'correction',
        })
        return request.render("M02_P0206_00.portal_correction_form", values)

    # =========================================================
    # WORK SCHEDULE API
    # =========================================================
    @http.route(['/my/work-schedule'], type='http', auth='user', website=True)
    def portal_work_schedule(self, **kw):
        return request.redirect('/my/shifts')

    @http.route(['/my/work-schedule/events'], type='json', auth='user')
    def work_schedule_events(self, start=None, end=None, **kw):
        employee = request.env.user.employee_id
        if not employee:
            return []
        
        PlanningSlot = request.env['planning.slot'].sudo()
        domain = [('resource_id', '=', employee.resource_id.id)]
        if start:
            domain.append(('start_datetime', '>=', start))
        if end:
            domain.append(('end_datetime', '<=', end))
        
        slots = PlanningSlot.search(domain, order='start_datetime asc')
        events = []
        for slot in slots:
            color = '#17a2b8'
            if slot.approval_state == 'approved':
                color = '#28a745'
            elif slot.approval_state == 'to_approve':
                color = '#ffc107'
            elif slot.approval_state == 'rejected':
                color = '#dc3545'
            
            events.append({
                'id': slot.id,
                'title': slot.role_id.name if slot.role_id else 'Ca làm việc',
                'start': slot.start_datetime.isoformat(),
                'end': slot.end_datetime.isoformat(),
                'color': color,
                'extendedProps': {
                    'role': slot.role_id.name if slot.role_id else '',
                    'hours': slot.allocated_hours,
                    'state': slot.approval_state,
                }
            })
        return events

    @http.route(['/my/work-schedule/create'], type='json', auth='user')
    def work_schedule_create(self, title=None, start=None, end=None, **kw):
        employee = request.env.user.employee_id
        if not employee:
            return {'error': 'Tài khoản chưa liên kết nhân viên.'}
        
        if not start or not end:
            return {'error': 'Vui lòng chọn thời gian.'}
        
        PlanningSlot = request.env['planning.slot'].sudo()
        slot = PlanningSlot.search([
            ('resource_id', '=', False),
            ('start_datetime', '<=', start),
            ('end_datetime', '>=', end),
            ('state', '=', 'published'),
        ], limit=1)
        
        if slot:
            return self.register_shift(slot.id)
        else:
            return {
                'success': True,
                'message': 'Không có ca trống phù hợp. Vui lòng liên hệ RGM.'
            }

    # =========================================================
    # TIMESHEET CONFIRMATION PORTAL
    # =========================================================
    @http.route(['/my/timesheet/confirm'], type='http', auth="user", website=True)
    def portal_timesheet_confirm(self, **kw):
        """Trang xác nhận công cuối tháng"""
        values = self._prepare_portal_layout_values()
        employee = request.env.user.employee_id
        if not employee:
            return request.render('rgm_workforce.portal_no_employee', {
                'message': 'Tài khoản chưa liên kết với hồ sơ nhân viên.'
            })
        
        MonthClosing = request.env['workforce.month.closing'].sudo()
        today = fields.Date.today()
        month = '%02d' % today.month
        year = today.year
        
        month_closing = MonthClosing.get_or_create_for_employee(employee.id, month, year)
        
        values.update({
            'employee': employee,
            'month_closing': month_closing,
            'page_name': 'timesheet_confirm',
        })
        return request.render("rgm_workforce.portal_timesheet_confirm", values)

    @http.route(['/my/timesheet/confirm/submit'], type='http', auth="user", website=True, methods=['POST'])
    def portal_timesheet_confirm_submit(self, **kw):
        employee = request.env.user.employee_id
        if not employee:
            return request.redirect('/my')
        
        closing_id = kw.get('closing_id')
        action = kw.get('action')
        
        if not closing_id:
            return request.redirect('/my/timesheet/confirm')
        
        MonthClosing = request.env['workforce.month.closing'].sudo()
        closing = MonthClosing.browse(int(closing_id))
        
        if not closing.exists() or closing.employee_id.id != employee.id:
            return request.redirect('/my/timesheet/confirm')
        
        if action == 'confirm':
            closing.action_employee_confirm()
        elif action == 'dispute':
            dispute_reason = kw.get('dispute_reason', '')
            if dispute_reason:
                closing.write({
                    'state': 'disputed',
                    'dispute_reason': dispute_reason,
                    'dispute_date': fields.Datetime.now(),
                    'dispute_resolved': False,
                })
                closing.message_post(
                    body='Nhân viên khiếu nại: %s' % dispute_reason,
                    message_type='comment',
                )
        return request.redirect('/my/timesheet/confirm')

    @http.route(['/my/timesheet/dispute'], type='http', auth="user", website=True)
    def portal_timesheet_dispute(self, **kw):
        values = self._prepare_portal_layout_values()
        employee = request.env.user.employee_id
        if not employee:
            return request.render('rgm_workforce.portal_no_employee', {
                'message': 'Tài khoản chưa liên kết với hồ sơ nhân viên.'
            })
        
        closing_id = kw.get('closing_id')
        if not closing_id:
            return request.redirect('/my/timesheet/confirm')
        
        MonthClosing = request.env['workforce.month.closing'].sudo()
        closing = MonthClosing.browse(int(closing_id))
        
        if not closing.exists() or closing.employee_id.id != employee.id:
            return request.redirect('/my/timesheet/confirm')
        
        values.update({
            'employee': employee,
            'month_closing': closing,
            'page_name': 'timesheet_dispute',
        })
        return request.render("rgm_workforce.portal_timesheet_dispute", values)