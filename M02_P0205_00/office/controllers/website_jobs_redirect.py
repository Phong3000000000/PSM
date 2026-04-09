# -*- coding: utf-8 -*-
from odoo import http
from odoo.addons.website_hr_recruitment.controllers.main import WebsiteHrRecruitment
from odoo.http import request


class WebsiteHrRecruitmentRedirect(WebsiteHrRecruitment):

    @http.route([
        '/jobs',
        '/jobs/page/<int:page>',
    ], type='http', auth='public', website=True, sitemap=WebsiteHrRecruitment.sitemap_jobs,
       list_as_website_content="Jobs")
    def jobs(self, country_id=None, all_countries=False, department_id=None, office_id=None, contract_type_id=None,
             is_remote=False, is_other_department=False, is_untyped=None, industry_id=None,
             is_industry_untyped=False, noFuzzy=False, page=1, search=None, **kwargs):
        if request.env.user._is_public():
            return request.redirect('/office-jobs')

        return super().jobs(
            country_id=country_id,
            all_countries=all_countries,
            department_id=department_id,
            office_id=office_id,
            contract_type_id=contract_type_id,
            is_remote=is_remote,
            is_other_department=is_other_department,
            is_untyped=is_untyped,
            industry_id=industry_id,
            is_industry_untyped=is_industry_untyped,
            noFuzzy=noFuzzy,
            page=page,
            search=search,
            **kwargs,
        )
