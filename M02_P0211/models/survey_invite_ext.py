from odoo import models, api

class SurveyInvite(models.TransientModel):
    _inherit = 'survey.invite'

    def _send_mail(self, answer):
        """ Ghi đè hàm gửi mail gốc của Odoo Survey để GỬI NGAY LẬP TỨC thay vì cho vào hàng đợi """
        mail = super()._send_mail(answer)
        # Bắt Odoo phải gửi mail đi ngay tức khắc
        if mail and mail.state == 'outgoing':
            mail.sudo().send(auto_commit=False)
        return mail
