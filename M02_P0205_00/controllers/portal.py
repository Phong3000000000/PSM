# -*- coding: utf-8 -*-
from odoo import http, _
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal, pager as portal_pager


class RecruitmentPortal(CustomerPortal):

    def _prepare_home_portal_values(self, counters):
        values = super()._prepare_home_portal_values(counters)
        if 'recruitment_request_count' in counters:
            count = request.env['x_psm_recruitment_request'].search_count([
                ('user_id', '=', request.env.user.id)
            ])
            values['recruitment_request_count'] = count
        if 'published_job_count' in counters:
            count = request.env['x_psm_recruitment_plan_line'].search_count([
                ('plan_id.state', '=', 'in_progress'),
                ('plan_id.is_sub_plan', '=', True),
                ('is_approved', '=', True),
                ('job_id.x_psm_0205_is_office_job', '=', True),
                ('job_id.website_published', '=', True),
                ('job_id.active', '=', True),
            ]) + request.env['x_psm_recruitment_request'].search_count([
                ('request_type', '=', 'unplanned'),
                ('state', '=', 'in_progress'),
                ('is_published', '=', True),
                ('job_id.x_psm_0205_is_office_job', '=', True),
                ('job_id.website_published', '=', True),
                ('job_id.active', '=', True),
            ])
            values['published_job_count'] = count
        return values

    @http.route(['/my/jobs', '/my/jobs/page/<int:page>'], type='http', auth="user", website=True)
    def portal_my_published_jobs(self, page=1, date_begin=None, date_end=None, sortby=None, **kw):
        values = self._prepare_portal_layout_values()
        lines_domain = [
            ('plan_id.state', '=', 'in_progress'),
            ('plan_id.is_sub_plan', '=', True),
            ('is_approved', '=', True),
            ('job_id', '!=', False),
            ('job_id.x_psm_0205_is_office_job', '=', True),
            ('job_id.website_published', '=', True),
            ('job_id.active', '=', True),
        ]
        lines = request.env['x_psm_recruitment_plan_line'].sudo().search(lines_domain, order='plan_id asc, planned_date asc, id desc')

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
                no_batch_lines.append(line)
        batches = list(batches_dict.values())

        unplanned_requests_domain = [
            ('request_type', '=', 'unplanned'),
            ('state', '=', 'in_progress'),
            ('is_published', '=', True),
            ('job_id', '!=', False),
            ('job_id.x_psm_0205_is_office_job', '=', True),
            ('job_id.website_published', '=', True),
            ('job_id.active', '=', True),
        ]
        unplanned_requests = request.env['x_psm_recruitment_request'].sudo().search(unplanned_requests_domain, order='create_date desc')

        values.update({
            'batches': batches,
            'no_batch_lines': no_batch_lines,
            'unplanned_requests': unplanned_requests,
            'page_name': 'published_jobs',
            'default_url': '/my/jobs',
        })
        return request.render("M02_P0205_00.psm_portal_my_published_jobs", values)

    @http.route(['/my/recruitment_requests', '/my/recruitment_requests/page/<int:page>'], type='http', auth="user", website=True)
    def portal_my_recruitment_requests(self, page=1, date_begin=None, date_end=None, sortby=None, **kw):
        values = self._prepare_portal_layout_values()
        RecruitmentRequest = request.env['x_psm_recruitment_request']
        domain = [('user_id', '=', request.env.user.id)]

        if date_begin and date_end:
            domain += [('create_date', '>', date_begin), ('create_date', '<=', date_end)]

        request_count = RecruitmentRequest.search_count(domain)
        pager = portal_pager(
            url="/my/recruitment_requests",
            url_args={'date_begin': date_begin, 'date_end': date_end, 'sortby': sortby},
            total=request_count,
            page=page,
            step=self._items_per_page
        )
        requests = RecruitmentRequest.search(domain, limit=self._items_per_page, offset=pager['offset'])
        request.session['my_recruitment_requests_history'] = requests.ids[:100]

        values.update({
            'date': date_begin,
            'recruitment_requests': requests,
            'page_name': 'recruitment_request',
            'pager': pager,
            'default_url': '/my/recruitment_requests',
        })
        return request.render("M02_P0205_00.psm_portal_my_recruitment_requests", values)
