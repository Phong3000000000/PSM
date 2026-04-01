# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal

class CustomerPortal(CustomerPortal):

    def _prepare_soc_hierarchy(self, employee):
        # 1. Get all published SOCs
        socs = request.env['slide.slide'].sudo().search([
            ('is_soc', '=', True),
            ('is_published', '=', True),
            ('channel_id.is_published', '=', True)
        ], order='soc_area, soc_sub_area, sequence')
        
        # 2b. Get Passed Evaluations (Secure Fallback)
        passed_evals = request.env['mcd.soc.evaluation'].sudo().search([
            ('employee_id', '=', employee.id),
            ('state', '=', 'done'),
            ('result', '=', 'pass'),
            ('score_achieved', '>=', 100)
        ])
        passed_slide_ids = {e.soc_id.id: True for e in passed_evals}
        
        # 3. Build Hierarchy
        hierarchy = {}
        Slide = request.env['slide.slide']
        area_labels = dict(Slide._fields['soc_area'].selection or [])
        station_labels = dict(Slide._fields['soc_sub_area'].selection or [])
        
        temp_data = {}

        for soc in socs:
            area_key = soc.soc_area or 'other'
            station_key = soc.soc_sub_area or 'other'
            
            # SOC is passed ONLY if Employee has a passed evaluation 100%
            is_done = passed_slide_ids.get(soc.id, False)
            
            if area_key not in temp_data: temp_data[area_key] = {}
            if station_key not in temp_data[area_key]: temp_data[area_key][station_key] = []
            
            temp_data[area_key][station_key].append({'slide': soc, 'status': is_done})

        # Process Status aggregation
        for area_key, stations_dict in temp_data.items():
            area_label = area_labels.get(area_key, area_key)
            
            area_node = {
                'name': area_label,
                'key': area_key,
                'status': True,
                'stations': []
            }
            
            for station_key, soc_list in stations_dict.items():
                station_label = station_labels.get(station_key, station_key)
                
                station_status = all(s['status'] for s in soc_list) and len(soc_list) > 0
                
                if not station_status:
                    area_node['status'] = False
                    
                station_node = {
                    'name': station_label,
                    'key': station_key,
                    'status': station_status,
                    'socs': soc_list
                }
                area_node['stations'].append(station_node)
            
            if not area_node['stations']:
                area_node['status'] = False

            if area_label not in hierarchy:
                hierarchy[area_label] = area_node

        # Progress Stats
        total_socs = len(socs)
        completed_socs = sum(1 for s in socs if passed_slide_ids.get(s.id))
        
        return hierarchy, total_socs, completed_socs

    @http.route(['/my/skills'], type='http', auth='user', website=True)
    def portal_my_skills(self, **kw):
        """ Display SOC Dashboard (My Skills) using Trainer Dashboard Logic """
        employee = request.env.user.employee_id
        if not employee:
            return request.render('M02_P0209_00.portal_no_employee_skills')
            
        hierarchy, total_socs, completed_socs = self._prepare_soc_hierarchy(employee)
        
        return request.render("M02_P0209_00.soc_trainer_evaluation_select", {
            'employee': employee,
            'hierarchy': hierarchy,
            'user': request.env.user,
            'total_socs': total_socs,
            'completed_socs': completed_socs,
            'is_self_view': True,
            'page_name': 'my_skills',
        })
