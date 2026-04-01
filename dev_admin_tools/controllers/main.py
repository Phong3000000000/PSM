from odoo import http
from odoo.http import request


class DevSessionInfo(http.Controller):
    
    @http.route('/web/session/get_session_info', type='json', auth='user')
    def get_session_info(self):
        session_info = request.env['ir.http'].session_info()
        session_info['expiration_date'] = '2099-12-31 23:59:59'
        session_info['expiration_reason'] = 'manual'
        session_info['warning'] = False
        session_info['dev_mode'] = 'assets,qweb'
        return session_info
