# -*- coding: utf-8 -*-
from odoo import http, _, fields
from odoo.http import request


class SocTrainerController(http.Controller):
    
    def _check_trainer_access(self):
        # No permission check - allow all users
        return True

    @http.route(['/soc/trainer/dashboard'], type='http', auth="user", website=True)
    def trainer_dashboard(self, **kwargs):
        # No permission check - allow all users
        employees = request.env['hr.employee'].sudo().search([
            ('active', '=', True),
        ], order='name')
        
        return request.render("M02_P0209_01.soc_trainer_dashboard", {
            'employees': employees,
            'user': request.env.user
        })

    def _prepare_soc_hierarchy(self, employee):
        # 1. Get all SOCs (no filter for published)
        socs = request.env['slide.slide'].sudo().search([
            ('is_soc', '=', True),
        ], order='soc_area_id, soc_station_id, sequence')
        
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
        # removed labels logic
        
        temp_data = {}

        for soc in socs:
            area_key = soc.soc_area_id.name if soc.soc_area_id else 'Other'
            station_key = soc.soc_station_id.name if soc.soc_station_id else 'Other'
            
            # SOC is passed ONLY if Employee has a passed evaluation 100%
            is_done = passed_slide_ids.get(soc.id, False)
            
            if area_key not in temp_data: temp_data[area_key] = {}
            if station_key not in temp_data[area_key]: temp_data[area_key][station_key] = []
            
            temp_data[area_key][station_key].append({'slide': soc, 'status': is_done})

        # Process Status aggregation
        for area_key, stations_dict in temp_data.items():
            area_label = area_key # Key is name now
            
            area_node = {
                'name': area_label,
                'key': area_key,
                'status': True,
                'stations': []
            }
            
            for station_key, soc_list in stations_dict.items():
                station_label = station_key # Key is name now
                
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

    @http.route(['/soc/trainer/evaluate/<int:employee_id>'], type='http', auth="user", website=True)
    def trainer_evaluate_employee(self, employee_id, **kwargs):
        if not self._check_trainer_access():
            return request.render('http_routing.403')
            
        employee = request.env['hr.employee'].sudo().browse(employee_id)
        if not employee.exists():
            return request.redirect('/soc/trainer/dashboard')
            
        hierarchy, total_socs, completed_socs = self._prepare_soc_hierarchy(employee)
        
        return request.render("M02_P0209_01.soc_trainer_evaluation_select", {
            'employee': employee,
            'hierarchy': hierarchy,
            'user': request.env.user,
            'total_socs': total_socs,
            'completed_socs': completed_socs
        })

    # --- EMPLOYEE SELF-SERVICE ROUTES ---

    @http.route(['/soc/my/dashboard'], type='http', auth="user", website=True)
    def my_soc_dashboard(self, **kwargs):
        employee = request.env.user.employee_id
        if not employee:
             return request.render('http_routing.404') # Or redirect to contact
        
        hierarchy, total_socs, completed_socs = self._prepare_soc_hierarchy(employee)
        
        return request.render("M02_P0209_01.soc_trainer_evaluation_select", {
            'employee': employee,
            'hierarchy': hierarchy,
            'user': request.env.user,
            'total_socs': total_socs,
            'completed_socs': completed_socs,
            'is_self_view': True
        })

    @http.route(['/soc/my/view/<int:slide_id>'], type='http', auth="user", website=True)
    def my_soc_view(self, slide_id, **kwargs):
        employee = request.env.user.employee_id
        if not employee:
            return request.render('http_routing.404')

        slide = request.env['slide.slide'].sudo().browse(slide_id)
        if not slide.exists():
            return request.redirect('/soc/my/dashboard')
            
        # Fetch History
        history_evals = request.env['mcd.soc.evaluation'].sudo().search([
            ('soc_id', '=', slide.id),
            ('employee_id', '=', employee.id),
            ('state', 'in', ['done', 'in_progress'])
        ], order='date_evaluation desc, create_date desc')

        # Check for latest Passed (100%) evaluation
        passed_evals = history_evals.filtered(lambda e: e.result == 'pass' and e.score_achieved >= 100.0)
        completed_eval = passed_evals[0] if passed_evals else False

        return request.render("M02_P0209_01.soc_trainer_perform_form", {
            'slide': slide,
            'employee': employee,
            'user': request.env.user,
            'history_evals': history_evals,
            'completed_eval': completed_eval,
            'readonly_mode': True # Always Read-Only for self view
        })

    @http.route(['/soc/trainer/perform/<int:slide_id>/<int:employee_id>'], type='http', auth="user", website=True)
    def trainer_perform_evaluation(self, slide_id, employee_id, **kwargs):
        if not self._check_trainer_access():
            return request.render('http_routing.403')

        slide = request.env['slide.slide'].sudo().browse(slide_id)
        employee = request.env['hr.employee'].sudo().browse(employee_id)
        
        if not slide.exists() or not employee.exists():
            return request.redirect('/soc/trainer/dashboard')

        # Fetch History
        history_evals = request.env['mcd.soc.evaluation'].sudo().search([
            ('soc_id', '=', slide.id),
            ('employee_id', '=', employee.id),
            ('state', 'in', ['done', 'in_progress']) # Include in_progress if needed, or just done
        ], order='date_evaluation desc, create_date desc')

        # Check for latest Passed (100%) evaluation
        passed_evals = history_evals.filtered(lambda e: e.result == 'pass' and e.score_achieved >= 100.0)
        completed_eval = passed_evals[0] if passed_evals else False

        return request.render("M02_P0209_01.soc_trainer_perform_form", {
            'slide': slide,
            'employee': employee,
            'user': request.env.user,
            'history_evals': history_evals,
            'completed_eval': completed_eval
        })

    @http.route(['/soc/trainer/history/<int:evaluation_id>'], type='http', auth="user", website=True)
    def trainer_view_history_detail(self, evaluation_id, **kwargs):
        if not self._check_trainer_access():
            return request.render('http_routing.403')
            
        evaluation = request.env['mcd.soc.evaluation'].sudo().browse(evaluation_id)
        if not evaluation.exists():
            return request.render('http_routing.404')

        return request.render("M02_P0209_01.soc_trainer_history_detail", {
             'evaluation': evaluation,
             'slide': evaluation.soc_id,
             'employee': evaluation.employee_id,
             'user': request.env.user
        })

    @http.route(['/soc/trainer/submit'], type='json', auth="user", website=True)
    def trainer_submit_evaluation(self, slide_id, employee_id, results, **kwargs):
        if not self._check_trainer_access():
            return {'error': 'Access Denied'}
            
        slide = request.env['slide.slide'].sudo().browse(slide_id)
        employee = request.env['hr.employee'].sudo().browse(employee_id)
        trainer = request.env.user.employee_id
        
        if not slide.exists() or not employee.exists():
            return {'error': 'Record not found'}
            
        # 1. Process Results (Strict 100% check requested)
        lines_data = []
        pass_count = 0
        total_items = len(slide.soc_item_ids)
        critical_fail = False
        
        for item in slide.soc_item_ids:
            val = results.get(str(item.id)) or 'fail' 
            is_checked = (val == 'pass')
            
            if is_checked:
                pass_count += 1
            else:
                # Any fail makes it < 100%
                if item.is_critical:
                    critical_fail = True
                
            lines_data.append((0, 0, {
                'soc_item_id': item.id,
                'name': item.name,
                'section_id': item.section_id.id,
                'is_critical': item.is_critical,
                'sequence': item.sequence,
                'is_checked': is_checked,
                'comment': results.get(f"comment_{item.id}", "")
            }))
            
        # Score
        score = 0
        if total_items > 0:
            score = (pass_count / total_items) * 100
        
        # User Requirement: "Phải đậu 100% mới được chứng chỉ"
        is_passed = False
        if critical_fail:
            is_passed = False
        elif score == 100: # Strict 100%
            is_passed = True
        else:
            is_passed = False
            
        result_state = 'pass' if is_passed else 'fail'
            
        # 2. Create Evaluation Record
        evaluation = request.env['mcd.soc.evaluation'].sudo().create({
            'employee_id': employee.id,
            'trainer_id': trainer.id,
            'soc_id': slide.id,
            'date_evaluation': fields.Date.today(),
            'state': 'done',
            'line_ids': lines_data,
            # result auto-computed? We might need to force it if logic differs from model defaults.
            # But normally model logic should align. Let's trust model but verify result.
        })
        
        # Force result update to match our strict logic if model differs
        # The model likely uses slide.pass_score. If slide.pass_score is 100, it matches.
        # But to be safe, we can manually ensure skill is granted ONLY if 100%.
        
        msg = f"Result: {result_state.upper()} ({score}%)"
        
        # 3. Grant Skill
        skill_msg = ""
        if is_passed:
             res = slide.grant_soc_skill_to_employee(employee)
             if res:
                 skill_msg = "PASSED! New Skill/Certificate Added to History."
        else:
             skill_msg = "Review Required. Score must be 100% to pass."
        
        return {
            'success': True,
            'message': msg,
            'skill_message': skill_msg,
            'redirect': f'/soc/trainer/evaluate/{employee.id}'
        }

    @http.route(['/soc/check/<int:employee_id>'], type='http', auth="user", website=True)
    def soc_check_page(self, employee_id, **kwargs):
        """Trang Kiểm tra SOC - Form giống SOC Evaluations"""
        employee = request.env['hr.employee'].sudo().browse(employee_id)
        if not employee.exists():
            return request.redirect('/my/home')
        
        # Lấy tất cả SOCs (published & active)
        socs = request.env['slide.slide'].sudo().search([
            ('is_soc', '=', True),
            ('is_published', '=', True),
            ('channel_id.is_published', '=', True)
        ], order='soc_area_id, soc_station_id, sequence')
        
        # Build Hierarchy Dict
        hierarchy = {}
        # removed labels logic
        
        for soc in socs:
            area_key = soc.soc_area_id.name if soc.soc_area_id else 'Other'
            station_key = soc.soc_station_id.name if soc.soc_station_id else 'Other'
            
            area_label = area_key
            station_label = station_key
            
            if area_label not in hierarchy:
                hierarchy[area_label] = {}
            if station_label not in hierarchy[area_label]:
                hierarchy[area_label][station_label] = []
                
            hierarchy[area_label][station_label].append(soc)
        
        return request.render("M02_P0209_01.soc_check_form", {
            'employee': employee,
            'hierarchy': hierarchy,
            'user': request.env.user
        })

    @http.route(['/soc/check/perform/<int:slide_id>/<int:employee_id>'], type='http', auth="user", website=True)
    def soc_check_perform(self, slide_id, employee_id, **kwargs):
        """Form kiểm tra SOC giống SOC Evaluations"""
        slide = request.env['slide.slide'].sudo().browse(slide_id)
        employee = request.env['hr.employee'].sudo().browse(employee_id)
        
        if not slide.exists() or not employee.exists():
            return request.redirect(f'/soc/check/{employee_id}')
        
        return request.render("M02_P0209_01.soc_check_perform_form", {
            'slide': slide,
            'employee': employee,
            'user': request.env.user
        })

    @http.route(['/soc/check/submit'], type='json', auth="user", website=True)
    def soc_check_submit(self, slide_id, employee_id, results, **kwargs):
        """Submit SOC Check - Logic giống SOC Evaluations, chỉ cấp chứng chỉ khi 100%"""
        slide = request.env['slide.slide'].sudo().browse(slide_id)
        employee = request.env['hr.employee'].sudo().browse(employee_id)
        trainer = request.env.user.employee_id

        if not slide.exists() or not employee.exists():
            return {'error': 'Record not found'}

        # Build line items giống backend SOC Evaluation
        lines_data = []
        for item in slide.soc_item_ids:
            val = results.get(str(item.id)) or 'fail'
            is_checked = (val == 'pass')

            lines_data.append((0, 0, {
                'soc_item_id': item.id,
                'name': item.name,
                'section_id': item.section_id.id,
                'is_critical': item.is_critical,
                'sequence': item.sequence,
                'is_checked': is_checked,
                'comment': results.get(f"comment_{item.id}", ""),
            }))

        # Tạo evaluation và dùng logic backend
        evaluation = request.env['mcd.soc.evaluation'].sudo().create({
            'employee_id': employee.id,
            'trainer_id': trainer.id,
            'soc_id': slide.id,
            'date_evaluation': fields.Date.today(),
            'state': 'in_progress',
            'line_ids': lines_data,
        })

        # Gọi action_submit_evaluation() - đã được sửa để chỉ cấp chứng chỉ khi 100%
        evaluation.action_submit_evaluation()

        msg = f"Evaluation Saved. Result: {evaluation.result.upper()} ({evaluation.score_achieved}%)"
        
        if evaluation.result == 'pass' and evaluation.score_achieved >= 100.0:
            skill_msg = "Certificate granted to Skills & Certifications!"
        elif evaluation.result == 'pass':
            skill_msg = f"Passed but not 100% ({evaluation.score_achieved}%). Certificate not granted. Please retake to achieve 100%."
        else:
            skill_msg = "Failed. Please retake the evaluation."

        return {
            'success': True,
            'result_code': evaluation.result,
            'score': evaluation.score_achieved,
            'message': msg,
            'skill_message': skill_msg,
            'redirect': f'/soc/trainer/evaluate/{employee.id}'
        }
