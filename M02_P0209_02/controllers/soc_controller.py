# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request

class SocController(http.Controller):
    
    @http.route(['/slides/soc/take/<model("slide.slide"):slide>'], type='http', auth="user", website=True)
    def soc_take_view(self, slide, **kwargs):
        """
        Render the SOC Fullscreen Evaluation View.
        """
        if not slide.is_soc:
            return request.redirect(f"/slides/slide/{slide.id}")
            
        values = {
            'slide': slide,
            'user': request.env.user,
            'is_public_user': request.env.user._is_public(),
        }

        # Phase B2: Check Prerequisites
        allowed, missing = slide.check_soc_access_rights(request.env.user)
        if not allowed:
             values['unmet_prereqs'] = missing
             return request.render("M02_P0209_01.soc_fullscreen_view", values)

        return request.render("M02_P0209_01.soc_fullscreen_view", values)

    @http.route(['/slides/soc/submit'], type='json', auth="user", website=True)
    def soc_submit(self, slide_id, results, **kwargs):
        """
        Handle SOC submission.
        results: {item_id: 'pass'|'fail'|'na'}
        """
        slide = request.env['slide.slide'].browse(slide_id)
        if not slide.exists():
            return {'error': 'Slide not found'}
            
        # 1. Scoring Logic
        items = slide.soc_item_ids
        pass_count = 0
        fail_count = 0
        na_count = 0
        critical_fail = False
        
        for item in items:
            str_id = str(item.id)
            val = results.get(str_id) or results.get(item.id) # Handle potential int/str key mismatch
            
            if val == 'fail':
                fail_count += 1
                if item.is_critical:
                    critical_fail = True
            elif val == 'pass':
                pass_count += 1
            elif val == 'na':
                na_count += 1
            else:
                # Missing result -> treat as NA or Fail? Let's treat as NA for now or ignore
                na_count += 1

        effective_total = len(items) - na_count
        score = 0
        if effective_total > 0:
            score = round((pass_count / effective_total) * 100)
        else:
            score = 100 # All NA
            
        if critical_fail:
            score = 0 # Immediate fail
            
        passed = score >= slide.pass_score

        # 2. Record Progress
        slide.action_mark_completed() # Standard Odoo method to mark slide viewed/done

        # 3. Grant Skill if Passed
        skill_msg = None
        if passed and slide.soc_skill_id:
            res = slide._grant_soc_skill(request.env.user)
            if res == 'granted':
                skill_msg = f"Congratulations! You have been granted the skill: {slide.soc_skill_id.name}"
            elif res == 'upgraded':
                skill_msg = f"Congratulations! Your skill {slide.soc_skill_id.name} has been upgraded!"
        
        return {
            'success': True, 
            'message': 'SOC Submitted Successfully',
            'score': score,
            'passed': passed,
            'skill_message': skill_msg
        }
