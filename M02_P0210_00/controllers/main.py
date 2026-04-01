from odoo import http, _
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal, pager as portal_pager

class ManagerSchedulePortal(CustomerPortal):

    def _prepare_home_portal_values(self, counters):
        values = super()._prepare_home_portal_values(counters)
        if not counters or 'schedule_count' in counters:
            # Count schedules user has access to (Record Rules applied)
            values['schedule_count'] = request.env['mcd.manager.schedule'].search_count([])
        return values

    @http.route(['/my/manager/schedules', '/my/manager/schedules/page/<int:page>'], type='http', auth="user", website=True)
    def portal_my_manager_schedules(self, page=1, date_begin=None, date_end=None, sortby=None,filterby=None, **kw):
        values = self._prepare_portal_layout_values()
        Schedule = request.env['mcd.manager.schedule']
        
        domain = []

        searchbar_sortings = {
            'date': {'label': _('Date'), 'order': 'schedule_date desc'},
            'name': {'label': _('Reference'), 'order': 'name desc'},
        }
        if not sortby:
            sortby = 'date'
        order = searchbar_sortings[sortby]['order']

        # Count for pager
        schedule_count = Schedule.search_count(domain)
        
        # Pager
        pager = portal_pager(
            url="/my/manager/schedules",
            url_args={'date_begin': date_begin, 'date_end': date_end, 'sortby': sortby},
            total=schedule_count,
            page=page,
            step=10
        )

        # Content
        schedules = Schedule.search(domain, order=order, limit=10, offset=pager['offset'])
        
        values.update({
            'date': date_begin,
            'schedules': schedules,
            'page_name': 'manager_schedule',
            'pager': pager,
            'default_url': '/my/manager/schedules',
            'searchbar_sortings': searchbar_sortings,
            'sortby': sortby,
            'schedule_count': schedule_count,
        })
        return request.render("M02_P0210_00.portal_my_manager_schedules", values)

    @http.route(['/my/manager/schedule/<int:schedule_id>'], type='http', auth="user", website=True)
    def portal_manager_schedule_detail(self, schedule_id, **kw):
        try:
            # Check access via Record Rules (no sudo)
            schedule = request.env['mcd.manager.schedule'].browse(schedule_id)
            if not schedule.exists():
                return request.redirect('/my/manager/schedules')
                 
        except Exception:
            return request.redirect('/my/manager/schedules')

        values = {
            'schedule': schedule,
            'page_name': 'manager_schedule',
        }
        return request.render("M02_P0210_00.portal_manager_schedule_page", values)

    @http.route(['/my/manager/schedule/feedback'], type='http', auth="user", methods=['POST'], website=True)
    def portal_manager_schedule_feedback(self, **kw):
        schedule_id = kw.get('schedule_id')
        feedback = kw.get('feedback')
        feedback_type = kw.get('feedback_type') # 'employee' or 'lnd'

        if schedule_id and feedback and feedback_type:
            try:
                start_schedule = request.env['mcd.manager.schedule'].browse(int(schedule_id))
                if not start_schedule.exists():
                     return request.redirect('/my/manager/schedules?error=Access Denied')

                schedule = start_schedule.sudo()
                
                if feedback_type == 'employee':
                    if schedule.employee_id.user_id != request.env.user:
                         return request.redirect(f'/my/manager/schedule/{schedule_id}?error=Permission Denied')
                
                schedule.submit_feedback(feedback_type, feedback)
                
                return request.redirect(f'/my/manager/schedule/{schedule_id}?success=Feedback Submitted')
            except Exception as e:
                return request.redirect(f'/my/manager/schedule/{schedule_id}?error={str(e)}')
        
        return request.redirect('/my/manager/schedules')

    @http.route(['/my/manager/schedule/action'], type='http', auth="user", methods=['POST'], website=True)
    def portal_manager_schedule_action(self, **kw):
        schedule_id = kw.get('schedule_id')
        action = kw.get('action') # 'complete_b1', 'complete_b3', 'complete_lff'

        if schedule_id and action:
            try:
                start_schedule = request.env['mcd.manager.schedule'].browse(int(schedule_id))
                if not start_schedule.exists():
                     return request.redirect('/my/manager/schedules?error=Access Denied')

                schedule = start_schedule.sudo()
                
                if schedule.employee_id.user_id != request.env.user:
                     return request.redirect(f'/my/manager/schedule/{schedule_id}?error=Permission Denied')

                if action == 'complete_b1' and schedule.state == 'b1_course':
                    schedule.action_complete_b1()
                elif action == 'complete_b3' and schedule.state == 'b3_course':
                    schedule.action_complete_b3()
                elif action == 'complete_lff' and schedule.state == 'b5_lff':
                    schedule.action_complete_lff()
                
                return request.redirect(f'/my/manager/schedule/{schedule_id}?success=Action Completed')
            except Exception as e:
                return request.redirect(f'/my/manager/schedule/{schedule_id}?error={str(e)}')
        
        return request.redirect('/my/manager/schedules')
