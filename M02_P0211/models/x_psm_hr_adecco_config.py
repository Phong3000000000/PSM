from odoo import models, fields, api

class HrAdeccoConfig(models.Model):
    _name = 'x_psm.hr.adecco.config'
    _description = 'Cấu hình đối tác Onboarding'

    name = fields.Char(string='Tên đối tác', required=True, default='Cấu hình mặc định')
    x_psm_email = fields.Char(string='Email nhận thông báo', required=True)
    active = fields.Boolean(string='Đang sử dụng', default=True)
    x_psm_cooperate_with_3p = fields.Boolean(string='Hợp tác với đối tác', default=True)
    
    x_psm_agency_type = fields.Selection([
        ('adecco', 'Khối Cửa hàng (OPS/Adecco)'),
        ('good_day', 'Khối Văn phòng (RST/Good Day)')
    ], string='Phân khối áp dụng', default='adecco', required=True)

    @api.model
    def get_x_psm_agency_email(self, x_psm_0211_staff_type='ops'):
        """Lấy email dựa trên loại nhân viên (ops -> Adecco, office -> Good Day)"""
        x_psm_agency_type = 'adecco' if x_psm_0211_staff_type == 'ops' else 'good_day'
        
        # Kiểm tra bảng đã tồn tại chưa để tránh lỗi lúc cài đặt module
        try:
            self.env.cr.execute("SELECT 1 FROM information_schema.tables WHERE table_name = 'x_psm_hr_adecco_config'")
            if not self.env.cr.fetchone():
                 return False
                 
            config = self.sudo().search([('x_psm_agency_type', '=', x_psm_agency_type), ('active', '=', True)], limit=1)
            return config.x_psm_email if config else False
        except Exception:
            return False

    @api.model
    def get_x_psm_adecco_email(self):
        """Helper cũ để giữ tương thích."""
        return self.get_x_psm_agency_email(x_psm_0211_staff_type='ops')
