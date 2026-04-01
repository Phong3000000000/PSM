# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request


class PortalEOTQ(http.Controller):

    @http.route(['/my/eotq'], type='http', auth='public', website=True)
    def portal_eotq_list(self, **kw):
        """Display a list of confirmed EOTQ winners"""
        rewards = request.env['shift.reward'].sudo().search([
            ('reward_type', '=', 'eotq'),
            ('state', '=', 'confirmed'),
        ], order='date desc')
        
        values = {
            'rewards': rewards,
            'page_name': 'eotq_blog',
        }
        return request.render('M02_P0216_00.portal_eotq_list', values)

class VoucherPortal(http.Controller):

    @http.route(['/my/vouchers'], type='http', auth='user', website=True)
    def portal_voucher_list(self, **kw):
        # Get filter and sort parameters
        partner_id = kw.get('partner_id')
        sort_by = kw.get('sort', 'name')
        
        # Build domain
        domain = [
            ('state', '=', 'active'),
            ('quantity', '>', 0)
        ]
        if partner_id:
            domain.append(('partner_id', '=', int(partner_id)))
        
        # Sort mapping
        sort_mapping = {
            'name': 'name asc',
            'price_asc': 'value asc',
            'price_desc': 'value desc',
            'points_asc': 'point_required asc',
            'points_desc': 'point_required desc',
        }
        order = sort_mapping.get(sort_by, 'name asc')
        
        # Get vouchers and partners
        vouchers = request.env['voucher.voucher'].sudo().search(domain, order=order)
        partners = request.env['urbox.partner'].sudo().search([('active', '=', True)])
        
        # Get employee points
        user = request.env.user
        employee = request.env['hr.employee'].sudo().search([
            ('user_id', '=', user.id)
        ], limit=1)
        if not employee and user.email:
            employee = request.env['hr.employee'].sudo().search([
                ('work_email', '=', user.email)
            ], limit=1)
        
        return request.render(
            'M02_P0216_00.portal_voucher_list',
            {
                'vouchers': vouchers,
                'partners': partners,
                'selected_partner': int(partner_id) if partner_id else None,
                'sort_by': sort_by,
                'employee': employee,
            }
        )

    @http.route(['/my/voucher/redeem/<int:voucher_id>'], type='http', auth='user', website=True, methods=['POST'])
    def redeem_voucher_portal(self, voucher_id, **kw):
        user = request.env.user
        employee = request.env['hr.employee'].sudo().search([
            ('user_id', '=', user.id)
        ], limit=1)

        if not employee and user.email:
            employee = request.env['hr.employee'].sudo().search([
                ('work_email', '=', user.email)
            ], limit=1)

        if not employee:
            return request.redirect('/my/vouchers?error=no_employee')

        voucher = request.env['voucher.voucher'].sudo().browse(voucher_id)

        if not voucher.exists() or voucher.quantity <= 0:
             return request.redirect('/my/vouchers?error=invalid_voucher')

        if employee.total_points < voucher.point_required:
             return request.redirect('/my/vouchers?error=not_enough_points')

        # Perform redemption
        employee.sudo().write({
            'total_points': employee.total_points - voucher.point_required
        })
        voucher.sudo().write({
            'quantity': voucher.quantity - 1
        })
        request.env['voucher.redeem'].sudo().create({
            'employee_id': employee.id,
            'voucher_id': voucher.id,
            'point_used': voucher.point_required
        })

        return request.redirect('/my/vouchers?success=True')

    @http.route(['/my/vouchers/history'], type='http', auth='user', website=True)
    def portal_voucher_history(self):
        user = request.env.user
        employee = request.env['hr.employee'].sudo().search([
            ('user_id', '=', user.id)
        ], limit=1)

        if not employee and user.email:
            employee = request.env['hr.employee'].sudo().search([
                ('work_email', '=', user.email)
            ], limit=1)

        history = []
        if employee:
            history = request.env['voucher.redeem'].sudo().search([
                ('employee_id', '=', employee.id)
            ], order='redeem_date desc')
        
        return request.render(
            'M02_P0216_00.portal_voucher_history',
            {'history': history}
        )

class ShiftEvaluationPortal(http.Controller):

    def _get_employee(self):
        user = request.env.user
        employee = request.env['hr.employee'].sudo().search([
            ('user_id', '=', user.id)
        ], limit=1)
        if not employee and user.email:
            employee = request.env['hr.employee'].sudo().search([
                ('work_email', '=', user.email)
            ], limit=1)
        return employee

    @http.route(['/my/shift_evaluations'], type='http', auth='user', website=True)
    def portal_shift_evaluation_list(self, **kw):
        employee = self._get_employee()
        if not employee:
            return request.redirect('/my')
        
        evaluations = request.env['shift.evaluation'].sudo().search([
            ('mic_id', '=', employee.id)
        ], order='date desc')
        
        return request.render('M02_P0216_00.portal_shift_evaluation_list', {
            'evaluations': evaluations,
        })

    @http.route(['/my/shift_evaluation/<int:evaluation_id>'], type='http', auth='user', website=True)
    def portal_shift_evaluation_detail(self, evaluation_id, **kw):
        employee = self._get_employee()
        if not employee:
            return request.redirect('/my')

        evaluation = request.env['shift.evaluation'].sudo().browse(evaluation_id)
        if not evaluation.exists() or evaluation.mic_id.id != employee.id:
             return request.redirect('/my/shift_evaluations')

        return request.render('M02_P0216_00.portal_shift_evaluation_detail', {
            'evaluation': evaluation,
            'success': kw.get('success'),
            'error': kw.get('error'),
        })

    @http.route(['/my/shift_evaluation/grade/<int:evaluation_id>'], type='http', auth='user', website=True, methods=['POST'])
    def portal_shift_evaluation_grade(self, evaluation_id, **kw):
        employee = self._get_employee()
        if not employee:
            return request.redirect('/my')

        evaluation = request.env['shift.evaluation'].sudo().browse(evaluation_id)
        if not evaluation.exists() or evaluation.mic_id.id != employee.id:
             return request.redirect('/my/shift_evaluations')

        # Process scores
        # Expecting inputs like score_<post_shift_id> and desc_<post_shift_id>
        PostShift = request.env['post.shift'].sudo()
        
        for key, value in kw.items():
            if key.startswith('score_'):
                try:
                    ps_id = int(key.split('_')[1])
                    score = float(value)
                    
                    ps = PostShift.browse(ps_id)
                    if ps.exists() and ps.shift_evaluation_id.id == evaluation.id:
                        ps.write({'score': score})
                        
                        # Also update description if present
                        desc_key = f'desc_{ps_id}'
                        if desc_key in kw:
                            ps.write({'description': kw.get(desc_key)})
                            
                except (ValueError, IndexError):
                    continue
        
        # Auto-complete the evaluation
        evaluation.sudo().write({'state': 'done'})

        return request.redirect(f'/my/shift_evaluation/{evaluation.id}?success=True')