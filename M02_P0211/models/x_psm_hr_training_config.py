from odoo import models, fields, api
from odoo.exceptions import UserError

class HrTrainingConfig(models.Model):
    _name = 'x_psm.hr.training.config'
    _description = 'Cấu hình lộ trình đào tạo Onboarding'
    _order = 'x_psm_staff_type, sequence, x_psm_days_after_start'

    name = fields.Char(string='Tên nhắc nhở đào tạo', required=True)
    x_psm_code = fields.Char(string='Document Code')
    x_psm_description = fields.Text(string='Mô tả / Hướng dẫn')
    x_psm_days_after_start = fields.Integer(string='Sau (ngày)', default=1, help='Số ngày sau khi bắt đầu lộ trình đào tạo sẽ diễn ra buổi này.')
    sequence = fields.Integer(string='Thứ tự', default=10)
    active = fields.Boolean(string="Hiển thị", default=True)
    
    x_psm_staff_type = fields.Selection([
        ('ops', 'OPS'),
        ('office', 'RST')
    ], string='Khối áp dụng', default='ops', required=True)

class HrEmployeeTrainingTask(models.Model):
    _name = 'x_psm.hr.employee.training.task'
    _description = 'Checklist tiến độ đào tạo nhân viên'
    _order = 'sequence'

    employee_id = fields.Many2one('hr.employee', required=True, ondelete='cascade')
    x_psm_origin_config_id = fields.Many2one('x_psm.hr.training.config', string='Cấu hình gốc')
    name = fields.Char(string='Tên công việc', required=True)
    x_psm_doc_code = fields.Char(string='Mã tài liệu')
    x_psm_description = fields.Text(string='Mô tả / Hướng dẫn')
    sequence = fields.Integer(string='Thứ tự', default=10)
    x_psm_date_planned = fields.Date(string='Ngày dự kiến')
    x_psm_is_done = fields.Boolean(string='Đã hoàn thành', default=False)

    x_psm_activity_id = fields.Many2one('mail.activity', string='Hoạt động liên kết', ondelete='set null')

    def write(self, vals):
        res = super().write(vals)
        if 'x_psm_is_done' in vals:
             for rec in self:
                 # 1. Tự động đóng activity cũ
                 if rec.x_psm_is_done and rec.x_psm_activity_id and not self.env.context.get('skip_activity_done'):
                      rec.x_psm_activity_id.sudo().action_done()
                 
                 # 2. Kiểm tra nếu đã đủ % để báo cho Line Manager (Tối ưu: Chỉ chạy khi có tích chọn hoàn thành)
                 if 'x_psm_is_done' in vals and rec.x_psm_is_done:
                      rec.employee_id.sudo()._compute_x_psm_0211_onboarding_ops_rst_training_process()
                      threshold = rec.employee_id.x_psm_0211_get_evaluation_threshold()
                      if rec.employee_id.x_psm_0211_onboarding_ops_rst_training_process >= threshold:
                           rec.employee_id.x_psm_0211_notify_evaluation_ready()
        return res

    @api.constrains('x_psm_is_done')
    def x_psm_check_is_done(self):
        for rec in self:
            if not rec.x_psm_is_done and rec._origin.x_psm_is_done:
                raise UserError("Bạn không thể bỏ đánh dấu nhiệm vụ đào tạo sau khi đã hoàn thành.")
