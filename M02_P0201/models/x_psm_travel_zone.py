from odoo import models, fields

class TravelZone(models.Model):
    _name = 'x_psm_travel_zone'
    _description = 'Travel Zone (Policy Area)'
    _rec_name = 'x_psm_name'

    x_psm_name = fields.Char(string='Zone Name', required=True, help="Ví dụ: Vùng 1, Khu vực Châu Á...")
    x_psm_active = fields.Boolean(string='Active', default=True)
    x_psm_is_allowance = fields.Boolean(string='Apply Allowance', default=True)
    
    x_psm_allowance_line_ids = fields.One2many('x_psm_travel_zone_allowance', 'x_psm_zone_id', string='Allowance & Hotel Rates')
    x_psm_destination_ids = fields.One2many('x_psm_travel_destination', 'x_psm_zone_id', string='Destinations')
    x_psm_laundry_limit = fields.Float(string='Laundry Limit', default=500000.0, help="Hạn mức giặt ủi tối đa cho mỗi nhân viên mỗi chuyến đi (> 7 ngày)")


class TravelZoneAllowance(models.Model):
    _name = 'x_psm_travel_zone_allowance'
    _description = 'Travel Zone Allowance & Hotel Rates'

    x_psm_zone_id = fields.Many2one('x_psm_travel_zone', string='Zone', ondelete='cascade')
    x_psm_job_ids = fields.Many2many('hr.job', string='Job Positions', help="Để trống để áp dụng cho tất cả chức danh")
    
    x_psm_allowance_rate = fields.Float(string='Allowance Rate', required=True, help="Định mức phụ cấp (Per Diem)")
    x_psm_hotel_rate = fields.Float(string='Hotel Max Rate', required=True, help="Định mức khách sạn tối đa mỗi đêm")
    x_psm_currency_id = fields.Many2one('res.currency', string='Currency', required=True, default=lambda self: self.env.company.currency_id)
