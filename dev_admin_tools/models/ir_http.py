# -*- coding: utf-8 -*-
from odoo import models


class IrHttp(models.AbstractModel):
    _inherit = 'ir.http'

    def session_info(self):
        """Override session_info to always return fake expiration data."""
        result = super().session_info()
        # Always override expiration data regardless of user type
        result['expiration_date'] = '2099-12-31 23:59:59'
        result['expiration_reason'] = 'manual'
        result['warning'] = False
        return result
