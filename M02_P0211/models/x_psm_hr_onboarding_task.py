from odoo import models, fields, api
from odoo.exceptions import UserError

class HrEmployeeOnboardingTask(models.Model):
    _name = 'x_psm.hr.employee.onboarding.task'
    _description = 'Checklist tiến độ Onboarding tổng thể'
    _order = 'x_psm_date_planned, id'

    employee_id = fields.Many2one('hr.employee', string='Nhân viên', required=True, ondelete='cascade')
    name = fields.Char(string='Nhiệm vụ', required=True)
    x_psm_is_done = fields.Boolean(string='Xong', default=False)
    x_psm_date_planned = fields.Date(string='Dự kiến')
    x_psm_activity_id = fields.Many2one('mail.activity', string='Hoạt động liên kết', ondelete='set null')

    def write(self, vals):
        """Đồng bộ khi người dùng gạt cần gạt (x_psm_is_done) trên form."""
        res = super().write(vals)
        if 'x_psm_is_done' in vals and vals['x_psm_is_done']:
             if not self.env.context.get('skip_activity_done'):
                 for rec in self:
                     if rec.x_psm_activity_id:
                          # Use sudo() to ensure HR can close activities assigned to others
                          rec.x_psm_activity_id.sudo().action_done()
        return res

    @api.constrains('x_psm_is_done')
    def x_psm_check_is_done(self):
        for rec in self:
            if not rec.x_psm_is_done and rec._origin.x_psm_is_done:
                raise UserError("Bạn không thể bỏ đánh dấu nhiệm vụ Onboarding sau khi đã hoàn thành.")
