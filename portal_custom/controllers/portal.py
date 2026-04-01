# -*- coding: utf-8 -*-
import json
from odoo import http, fields
from odoo.addons.portal.controllers.portal import CustomerPortal
from odoo.http import request


from odoo.tools.image import image_data_uri


def get_cover_image_url(post):
    """Extract cover image URL from blog post's cover_properties JSON"""
    if not post.cover_properties:
        return None
    try:
        props = json.loads(post.cover_properties)
        bg_image = props.get('background-image', '')
        # Extract URL from "url('/path/to/image')" format
        if bg_image.startswith("url("):
            url = bg_image[4:-1].strip("'").strip('"')
            return url
    except (json.JSONDecodeError, ValueError):
        pass
    return None


class CustomPortal(CustomerPortal):

    @http.route(['/my', '/my/home'], type='http', auth="user", website=True)
    def home(self, **kw):
        """ Override home to add blog posts for news feed and manager approval data """
        response = super(CustomPortal, self).home(**kw)
        
        # 1. Check if current user is an employee
        employee = request.env['hr.employee'].sudo().search([
            ('user_id', '=', request.env.user.id)
        ], limit=1)
        
        # If not an employee, return standard portal response
        if not employee:
            return response

        # 2. Fetch published blog posts for news feed
        BlogPost = request.env['blog.post'].sudo()
        blog_posts = BlogPost.search([
            ('is_published', '=', True),
        ], order='post_date desc', limit=20)
        
        # 3. Fetch upcoming events
        PortalEvent = request.env['portal.event'].sudo()
        upcoming_events = PortalEvent.search([
            ('date', '>=', fields.Date.today()),
        ], order='date asc', limit=5)
        
        # 4. Check if current user is a line manager
        is_manager = False
        approval_count = 0
        
        # Check if user has any subordinates
        subordinates = request.env['hr.employee'].sudo().search([
            ('parent_id', '=', employee.id)
        ])
        if subordinates:
            is_manager = True
            # Count pending approval requests from subordinates
            # 1. Count pending shift approvals (planning.slot)
            sub_resource_ids = subordinates.mapped('resource_id').ids
            PlanningSlot = request.env['planning.slot'].sudo()
            if 'approval_state' in PlanningSlot._fields:
                shift_count = PlanningSlot.search_count([
                    ('resource_id', 'in', sub_resource_ids),
                    ('approval_state', '=', 'to_approve'),
                ])
            else:
                shift_count = 0
            
            # 2. Count pending approval.request from subordinates
            ApprovalRequest = request.env['approval.request'].sudo()
            sub_user_ids = subordinates.mapped('user_id').ids
            approval_request_count = ApprovalRequest.search_count([
                ('request_owner_id', 'in', sub_user_ids),
                ('request_status', '=', 'pending'),
            ])
            
            approval_count = shift_count + approval_request_count
        
        # 5. Check permissions for posting news (HR Officers or Admin)
        can_post_news = request.env.user.has_group('hr.group_hr_user') or request.env.user.has_group('base.group_system')

        # 6. Add context variables to response
        if hasattr(response, 'qcontext'):
            response.qcontext['is_employee'] = True
            response.qcontext['blog_posts'] = blog_posts
            response.qcontext['upcoming_events'] = upcoming_events
            response.qcontext['slug'] = request.env['ir.http']._slug
            response.qcontext['image_data_uri'] = image_data_uri
            response.qcontext['user'] = request.env.user
            response.qcontext['get_cover_image_url'] = get_cover_image_url
            response.qcontext['is_manager'] = is_manager
            response.qcontext['approval_count'] = approval_count
            response.qcontext['can_post_news'] = can_post_news
        
        return response

    @http.route(['/my/news/post'], type='http', auth='user', methods=['POST'], website=True)
    def post_news(self, **kw):
        """ Handle news posting from portal (HR or Admin only) """
        if not (request.env.user.has_group('hr.group_hr_user') or request.env.user.has_group('base.group_system')):
            return request.redirect('/my')

        content = kw.get('content')
        if not content:
            return request.redirect('/my')

        # Find a default blog (e.g., 'News' or first available)
        Blog = request.env['blog.blog'].sudo()
        blog = Blog.search([('name', 'ilike', 'News')], limit=1)
        if not blog:
            blog = Blog.search([], limit=1)
        
        if not blog:
            return request.redirect('/my?error=no_blog_found')

        # Create the post
        BlogPost = request.env['blog.post'].sudo()
        
        # Use first few words as title
        title = content[:50] + '...' if len(content) > 50 else content
        
        post = BlogPost.create({
            'blog_id': blog.id,
            'name': title,
            'subtitle': content, # Using subtitle as main content for simple posts
            'author_id': request.env.user.partner_id.id,
            'is_published': True, # Publish immediately
        })
        
        return request.redirect('/my?success=post_created')

    @http.route(['/my/news/post/delete/<int:post_id>'], type='http', auth='user', website=True)
    def delete_news(self, post_id, **kw):
        """ Handle post deletion """
        BlogPost = request.env['blog.post'].sudo()
        post = BlogPost.browse(post_id)
        
        if not post.exists():
            return request.redirect('/my?error=post_not_found')
            
        # Check permissions: HR or Admin only
        is_hr_or_admin = request.env.user.has_group('hr.group_hr_user') or request.env.user.has_group('base.group_system')
        
        if is_hr_or_admin:
            post.unlink()
            return request.redirect('/my?success=post_deleted')
            
        return request.redirect('/my?error=access_denied')

    # =====================
    # PORTAL APPS
    # =====================

    @http.route(['/my/leaves'], type='http', auth='user', website=True)
    def portal_leaves(self, **kw):
        return request.render('portal_custom.portal_app_leaves', {
            'user': request.env.user,
            'app_name': 'Leaves',
        })

    @http.route(['/my/personal-information'], type='http', auth='user', website=True)
    def portal_personal_information(self, **kw):
        return request.render('portal_custom.portal_app_personal_information', {
            'user': request.env.user,
            'app_name': 'Personal Information',
        })

    @http.route(['/my/rocks'], type='http', auth='user', website=True)
    def portal_rocks(self, **kw):
        return request.render('portal_custom.portal_app_rocks', {
            'user': request.env.user,
            'app_name': 'Rocks',
        })

    @http.route(['/my/performance'], type='http', auth='user', website=True)
    def portal_performance(self, **kw):
        return request.render('portal_custom.portal_app_performance', {
            'user': request.env.user,
            'app_name': 'Performance',
        })

    @http.route(['/my/team-accountabilities'], type='http', auth='user', website=True)
    def portal_team_accountabilities(self, **kw):
        employee = request.env['hr.employee'].sudo().search([
            ('user_id', '=', request.env.user.id)
        ], limit=1)
        
        is_manager = False
        subordinates = request.env['hr.employee'].sudo()
        shift_data = [] # For Shift Management View
        attendance_by_employee = {} # For Timesheet (Bảng chấm công)
        days_in_month = list(range(1, 32)) # 1-31 days
        
        if employee:
            subordinates = request.env['hr.employee'].sudo().search([
                ('parent_id', '=', employee.id)
            ])
            if subordinates:
                is_manager = True
                
                # Fetch Upcoming Shifts for Shift Management (e.g. today or next 7 days)
                PlanningSlot = request.env['planning.slot'].sudo()
                shifts = PlanningSlot.search([
                    ('resource_id', 'in', subordinates.mapped('resource_id').ids),
                    ('start_datetime', '>=', fields.Datetime.today())
                ], order='start_datetime asc')
                shift_data = shifts
                
                # Fetch Attendances for Timesheet (Bảng chấm công) - current month
                from dateutil.relativedelta import relativedelta
                today = fields.Date.today()
                first_day = today.replace(day=1)
                last_day = today + relativedelta(day=31)
                
                Attendance = request.env['hr.attendance'].sudo()
                attendances = Attendance.search([
                    ('employee_id', 'in', subordinates.ids),
                    ('check_in', '>=', first_day),
                    ('check_in', '<=', last_day)
                ])
                
                # Build dict: {employee_id: {day: worked_hours}}
                for sub in subordinates:
                    attendance_by_employee[sub] = {day: 0.0 for day in days_in_month}
                    
                for att in attendances:
                    if att.check_in and att.worked_hours > 0:
                        day = att.check_in.day
                        attendance_by_employee[att.employee_id][day] += att.worked_hours

        return request.render('portal_custom.portal_app_team_accountabilities', {
            'user': request.env.user,
            'app_name': 'Team Accountabilities',
            'is_manager': is_manager,
            'subordinates': subordinates,
            'shift_data': shift_data,
            'attendance_by_employee': attendance_by_employee,
            'days_in_month': days_in_month,
        })

    @http.route(['/my/team-accountabilities/approve_day'], type='http', auth='user', methods=['POST'], website=True)
    def approve_day_timesheet(self, **kw):
        """Approve all attendances for a specific day for subordinates"""
        day = int(kw.get('day', 0))
        if not day:
            return request.redirect('/my/team-accountabilities')
            
        employee = request.env['hr.employee'].sudo().search([
            ('user_id', '=', request.env.user.id)
        ], limit=1)
        
        if employee:
            subordinates = request.env['hr.employee'].sudo().search([
                ('parent_id', '=', employee.id)
            ])
            if subordinates:
                today = fields.Date.today()
                target_date = today.replace(day=day)
                
                Attendance = request.env['hr.attendance'].sudo()
                attendances = Attendance.search([
                    ('employee_id', 'in', subordinates.ids),
                    ('check_in', '>=', fields.Datetime.to_string(fields.Datetime.start_of(target_date, 'day'))),
                    ('check_in', '<=', fields.Datetime.to_string(fields.Datetime.end_of(target_date, 'day'))),
                    ('is_manager_validated', '=', False)
                ])
                
                # Check if field exists before writing to prevent errors if module not updated yet
                if 'is_manager_validated' in Attendance._fields:
                    attendances.write({'is_manager_validated': True})
                
        return request.redirect('/my/team-accountabilities#timesheet')

    @http.route(['/my/appraisals'], type='http', auth='user', website=True)
    def portal_appraisals(self, **kw):
        return request.render('portal_custom.portal_app_appraisals', {
            'user': request.env.user,
            'app_name': 'Appraisals',
        })

    @http.route(['/my/employee-engagement'], type='http', auth='user', website=True)
    def portal_employee_engagement(self, **kw):
        return request.render('portal_custom.portal_app_employee_engagement', {
            'user': request.env.user,
            'app_name': 'Employee Engagement',
        })

    @http.route(['/my/expenses'], type='http', auth='user', website=True)
    def portal_expenses(self, **kw):
        return request.render('portal_custom.portal_app_expenses', {
            'user': request.env.user,
            'app_name': 'Expenses',
        })

    @http.route(['/my/cond'], type='http', auth='user', website=True)
    def portal_cond(self, **kw):
        return request.render('portal_custom.portal_app_cond', {
            'user': request.env.user,
            'app_name': 'COND',
        })

    @http.route(['/my/payslips'], type='http', auth='user', website=True)
    def portal_payslips(self, **kw):
        return request.render('portal_custom.portal_app_payslips', {
            'user': request.env.user,
            'app_name': 'Payslips',
        })

    @http.route(['/my/knowledge-hub'], type='http', auth='user', website=True)
    def portal_knowledge_hub(self, **kw):
        return request.render('portal_custom.portal_app_knowledge_hub', {
            'user': request.env.user,
            'app_name': 'Knowledge Hub',
        })

    @http.route(['/my/settings'], type='http', auth='user', website=True)
    def portal_settings(self, **kw):
        values = self._prepare_portal_layout_values()
        values.update({
            'user': request.env.user,
        })
        return request.render('portal_custom.portal_settings_page', values)

    # =========================================================
    # APPROVALS MOVED TO M02_P0200_00
    # =========================================================

