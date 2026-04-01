# -*- coding: utf-8 -*-
from odoo import http, fields
from odoo.http import request
from odoo.addons.portal_custom.controllers.portal import CustomPortal


class ReferralPortalController(CustomPortal):
    """Override portal home to inject active referral programs into
    the SỰ KIỆN SẮP TỚI sidebar widget."""

    @http.route(['/my', '/my/home'], type='http', auth='user', website=True)
    def home(self, **kw):
        response = super().home(**kw)

        # Bài tuyển dụng đang mở và còn trong thời hạn
        programs = request.env['employee.referral.program'].sudo().search([
            ('state', '=', 'active'),
            '|',
            ('end_date', '=', False),
            ('end_date', '>=', fields.Date.today()),
        ], order='end_date asc', limit=3)

        if hasattr(response, 'qcontext'):
            response.qcontext['upcoming_referral_programs'] = programs

        return response
