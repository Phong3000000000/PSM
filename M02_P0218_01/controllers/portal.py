# -*- coding: utf-8 -*-

from odoo import http
from odoo.http import request


class PortalGoalsController(http.Controller):
    
    @http.route(['/my/goals'], type='http', auth='user', website=True)
    def portal_goals(self, **kw):
        """Display employee goals list in portal"""
        # user = request.env.user
        # employee = user.employee_id
        partner = request.env.user.partner_id
        employee = request.env['hr.employee'].sudo().search([('work_contact_id', '=', partner.id)], limit=1)
        
        # Debug info
        # debug_user_name = user.name if user else 'No User'
        # debug_user_id = user.id if user else 0
        # debug_employee_name = employee.name if employee else 'No Employee'
        # debug_employee_id = employee.id if employee else 0
        
        goals = []
        if employee:
            goals = request.env['hr.appraisal.goal'].sudo().search([
                ('employee_ids', 'in', employee.ids)
            ], order='create_date desc')
        
        debug_goals_count = len(goals)
        debug_goals_names = ', '.join(goals.mapped('name')) if goals else 'No Goals'
        
        # Map progression to percentage for display
        progression_map = {
            '000': 0,
            '025': 25,
            '050': 50,
            '075': 75,
            '100': 100,
        }
        
        return request.render('M02_P0218_01.portal_goals_page', {
            'goals': goals,
            'employee': employee,
            'progression_map': progression_map,
            # Debug variables
            # 'debug_user_name': debug_user_name,
            # 'debug_user_id': debug_user_id,
            # 'debug_employee_name': debug_employee_name,
            # 'debug_employee_id': debug_employee_id,
            # 'debug_goals_count': debug_goals_count,
            # 'debug_goals_names': debug_goals_names,
        })

    @http.route(['/my/goals/create'], type='http', auth='user', website=True)
    def portal_goals_create(self, **kw):
        """Render goal creation form"""
        return request.render('M02_P0218_01.portal_goals_create_page', {})

    @http.route(['/my/goals/submit'], type='http', auth='user', methods=['POST'], website=True)
    def portal_goals_submit(self, **kw):
        """Handle goal creation submission"""
        partner = request.env.user.partner_id
        employee = request.env['hr.employee'].sudo().search([('work_contact_id', '=', partner.id)], limit=1)
        
        if not employee:
            return request.redirect('/my/goals?error=no_employee')
            
        vals = {
            'name': kw.get('name'),
            'goal_type': kw.get('goal_type'),
            'deadline': kw.get('deadline') or False,
            'description': kw.get('description'),
            'progression': kw.get('progression'),
            'employee_ids': [(4, employee.id)],
        }
        
        try:
            request.env['hr.appraisal.goal'].sudo().create(vals)
        except Exception as e:
             return request.redirect('/my/goals?error=create_failed')
             
        return request.redirect('/my/goals?success=goal_created')

    @http.route(['/my/goals/<int:goal_id>'], type='http', auth='user', website=True)
    def portal_goals_edit(self, goal_id, **kw):
        """Render goal edit form"""
        try:
            # Check access: goal must belong to logged in employee
            partner = request.env.user.partner_id
            employee = request.env['hr.employee'].sudo().search([('work_contact_id', '=', partner.id)], limit=1)
            
            if not employee:
                return request.redirect('/my/goals?error=no_access')
                
            goal = request.env['hr.appraisal.goal'].sudo().search([
                ('id', '=', goal_id),
                ('employee_ids', 'in', employee.ids)
            ], limit=1)
            
            if not goal:
                 return request.redirect('/my/goals?error=goal_not_found')
                 
            return request.render('M02_P0218_01.portal_goals_edit_page', {
                'goal': goal,
            })
        except Exception as e:
            import traceback
            return request.make_response(f"Error: {str(e)}<br><pre>{traceback.format_exc()}</pre>")

    @http.route(['/my/goals/<int:goal_id>/submit'], type='http', auth='user', methods=['POST'], website=True)
    def portal_goals_submit_changes(self, goal_id, **kw):
        """Handle goal update submission"""
        partner = request.env.user.partner_id
        employee = request.env['hr.employee'].sudo().search([('work_contact_id', '=', partner.id)], limit=1)
        
        goal = request.env['hr.appraisal.goal'].sudo().search([
            ('id', '=', goal_id),
            ('employee_ids', 'in', employee.ids if employee else [])
        ], limit=1)
        
        if not goal:
            return request.redirect('/my/goals?error=goal_not_found')
            
        vals = {
            'name': kw.get('name'),
            'goal_type': kw.get('goal_type'),
            'deadline': kw.get('deadline') or False,
            'description': kw.get('description'),
            'progression': kw.get('progression'),
        }
        
        try:
            goal.write(vals)
        except Exception as e:
             return request.redirect('/my/goals/%s?error=update_failed' % goal_id)
             
        return request.redirect('/my/goals?success=goal_updated')
