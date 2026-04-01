# -*- coding: utf-8 -*-
from odoo import http, _
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal, pager as portal_pager

class RecruitmentPortal(CustomerPortal):

    def _prepare_home_portal_values(self, counters):
        values = super()._prepare_home_portal_values(counters)
        if 'recruitment_request_count' in counters:
            count = request.env['recruitment.request'].search_count([
                ('user_id', '=', request.env.user.id)
            ])
            values['recruitment_request_count'] = count
        if 'published_job_count' in counters:
            count = request.env['hr.job'].search_count([
                ('website_published', '=', True),
                ('active', '=', True)
            ])
            values['published_job_count'] = count
        return values

    @http.route(['/my/jobs', '/my/jobs/page/<int:page>'], type='http', auth="user", website=True)
    def portal_my_published_jobs(self, page=1, date_begin=None, date_end=None, sortby=None, **kw):
        values = self._prepare_portal_layout_values()
        HrJob = request.env['hr.job']
        domain = [('website_published', '=', True), ('active', '=', True)]

        # count for pager
        job_count = HrJob.search_count(domain)
        # pager
        pager = portal_pager(
            url="/my/jobs",
            total=job_count,
            page=page,
            step=self._items_per_page
        )
        # content
        jobs = HrJob.search(domain, limit=self._items_per_page, offset=pager['offset'])

        values.update({
            'jobs': jobs,
            'page_name': 'published_job',
            'pager': pager,
            'default_url': '/my/jobs',
        })
        return request.render("M02_P0205_00.portal_my_published_jobs", values)

    @http.route(['/my/recruitment_requests', '/my/recruitment_requests/page/<int:page>'], type='http', auth="user", website=True)
    def portal_my_recruitment_requests(self, page=1, date_begin=None, date_end=None, sortby=None, **kw):
        values = self._prepare_portal_layout_values()
        RecruitmentRequest = request.env['recruitment.request']
        domain = [('user_id', '=', request.env.user.id)]

        if date_begin and date_end:
            domain += [('create_date', '>', date_begin), ('create_date', '<=', date_end)]

        # count for pager
        request_count = RecruitmentRequest.search_count(domain)
        # pager
        pager = portal_pager(
            url="/my/recruitment_requests",
            url_args={'date_begin': date_begin, 'date_end': date_end, 'sortby': sortby},
            total=request_count,
            page=page,
            step=self._items_per_page
        )
        # content according to pager and archive selected
        requests = RecruitmentRequest.search(domain, limit=self._items_per_page, offset=pager['offset'])
        request.session['my_recruitment_requests_history'] = requests.ids[:100]

        values.update({
            'date': date_begin,
            'recruitment_requests': requests,
            'page_name': 'recruitment_request',
            'pager': pager,
            'default_url': '/my/recruitment_requests',
        })
        return request.render("M02_P0205_00.portal_my_recruitment_requests", values)