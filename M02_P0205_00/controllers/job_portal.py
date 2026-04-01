# -*- coding: utf-8 -*-
import base64
import logging
from odoo import http, _
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal

_logger = logging.getLogger(__name__)


class JobPortalHome(CustomerPortal):
    """Extend portal home to add job counts"""

    def _prepare_home_portal_values(self, counters):
        values = super()._prepare_home_portal_values(counters)
        if 'published_job_count' in counters:
            # Đếm số vị trí đang tuyển
            plan_line_count = request.env['recruitment.plan.line'].sudo().search_count([
                ('plan_id.state', 'in', ['in_progress']),
                ('is_approved', '=', True),
            ])
            unplanned_count = request.env['recruitment.request'].sudo().search_count([
                ('request_type', '=', 'unplanned'),
                ('state', '=', 'in_progress'),
                ('is_published', '=', True),
            ])
            values['published_job_count'] = plan_line_count + unplanned_count
        return values

class JobPortal(http.Controller):

    @http.route('/my/jobs', type='http', auth='user', website=True)
    def portal_published_jobs(self, **kw):
        """Show published job listings grouped by batch"""
        # Lấy tất cả plan.line đang active
        lines = request.env['recruitment.plan.line'].sudo().search([
            ('plan_id.state', 'in', ['in_progress']),
            ('is_approved', '=', True),
        ], order='plan_id asc')

        # Nhóm theo batch (plan_id.batch_id), không cộng dồn
        batches_dict = {}
        no_batch_lines = []

        for line in lines:
            batch = line.plan_id.batch_id
            if batch:
                key = batch.id
                if key not in batches_dict:
                    batches_dict[key] = {
                        'batch': batch,
                        'lines': [],
                    }
                batches_dict[key]['lines'].append(line)
            else:
                # Kế hoạch không có đợt tuyển dụng → nhóm riêng
                no_batch_lines.append(line)

        # Danh sách đợt theo thứ tự
        batches = list(batches_dict.values())

        # Lấy các yêu cầu tuyển dụng đột xuất đang tuyển
        unplanned_requests = request.env['recruitment.request'].sudo().search([
            ('request_type', '=', 'unplanned'),
            ('state', '=', 'in_progress'),
            ('is_published', '=', True),
        ], order='create_date desc')

        return request.render('M02_P0205_00.portal_my_published_jobs', {
            'batches': batches,
            'no_batch_lines': no_batch_lines,
            'unplanned_requests': unplanned_requests,
            'page_name': 'published_jobs',
        })

    @http.route('/jobs/detail/<int:line_id>', type='http', auth='public', website=True)
    def job_detail_and_apply(self, line_id, **kw):
        """Show job detail for a plan.line and application form"""
        line = request.env['recruitment.plan.line'].sudo().browse(line_id)
        if not line.exists() or line.plan_id.state != 'in_progress':
            return request.redirect('/404')

        job = line.job_id
        return request.render('M02_P0205_00.job_apply_template', {
            'job': job,
            'line': line,
            'batch': line.plan_id.batch_id,
            'error': kw.get('error'),
            'msg': kw.get('msg', '').replace('+', ' ') if kw.get('msg') else None
        })

    @http.route('/jobs/request/detail/<int:request_id>', type='http', auth='public', website=True)
    def job_request_detail_and_apply(self, request_id, **kw):
        """Show job detail for a recruitment.request and application form"""
        req = request.env['recruitment.request'].sudo().browse(request_id)
        if not req.exists() or req.state != 'in_progress':
            return request.redirect('/404')

        job = req.job_id
        return request.render('M02_P0205_00.job_apply_template', {
            'job': job,
            'request_rec': req,
            'error': kw.get('error'),
            'msg': kw.get('msg', '').replace('+', ' ') if kw.get('msg') else None
        })

    @http.route('/jobs/submit', type='http', auth='public', methods=['POST'], website=True, csrf=True)
    def job_apply_submit(self, **post):
        """Redirect to the unified apply route in M02_P0204_00."""
        line_id = post.get('line_id')
        request_id = post.get('request_id')
        
        if not line_id and not request_id:
            return request.redirect('/404')

        job = False
        if line_id:
            line = request.env['recruitment.plan.line'].sudo().browse(int(line_id))
            if line.exists():
                job = line.job_id
        elif request_id:
            req = request.env['recruitment.request'].sudo().browse(int(request_id))
            if req.exists():
                job = req.job_id

        if not job:
            return request.redirect('/404')

        # Redirect to the unified 0204 apply route
        return request.redirect(f'/jobs/apply/{job.id}')

    @http.route('/jobs/thankyou', type='http', auth='public', website=True)
    def job_thankyou(self, **kw):
        """Thank you page after application"""
        return request.render('M02_P0205_00.job_thankyou_template', {})
