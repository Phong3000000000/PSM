# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError

class HrProbationWizard(models.TransientModel):
    _name = 'hr.probation.wizard'
    _description = 'Wizard đánh giá thử việc'

    employee_id = fields.Many2one('hr.employee', string='Nhân viên', required=True)
    evaluation_result = fields.Selection([
        ('pass', 'Đạt (Pass) — Thông báo cho ứng viên và chuyển sang trạng thái tiếp theo'),
        ('fail', 'Không đạt (Fail) — Gửi thư từ chối và lý do cho ứng viên')
    ], string='Kết quả đánh giá', required=True, default='pass')
    
    refusal_reason = fields.Text(string='Lý do không đạt/Nhận xét')

    def action_confirm(self):
        self.ensure_one()
        # Dùng sudo() để vượt qua các rào cản phân quyền trên các field đặc biệt (như version_id) 
        # khi cập nhật trạng thái hồ sơ nhân viên.
        employee = self.employee_id.sudo()
        
        if self.evaluation_result == 'fail' and not self.refusal_reason:
            raise UserError("Vui lòng nhập lý do không đạt thử việc.")

        if self.evaluation_result == 'pass':
            # Logic đậu thử việc (đã có sẵn method notify)
            employee.action_psm_notify_probation_passed()
            from markupsafe import Markup as markup
            employee.message_post(body=markup("<b>Kết quả: Đạt thử việc (Pass)</b>. Hồ sơ đã được chuyển sang trạng thái Hoàn thành thử việc."))
        else:
            # Logic không đạt thử việc
            employee.write({'x_psm_0211_onboarding_state': 'refused'})
            employee._send_psm_0211_probation_fail_email(self.refusal_reason)
            from markupsafe import Markup as markup
            employee.message_post(body=markup(f"<b>Kết quả: Không đạt (Fail)</b>. Lý do: {self.refusal_reason}"))

        return {'type': 'ir.actions.act_window_close'}
