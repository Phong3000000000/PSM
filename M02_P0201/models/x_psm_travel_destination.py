from odoo import models, fields, api


class TravelDestination(models.Model):
    _name = 'x_psm_travel_destination'
    _description = 'Travel Destination'
    _rec_name = 'x_psm_name'

    x_psm_name = fields.Char(string='Name', required=True)
    x_psm_state_id = fields.Many2one(
        'res.country.state',
        string='City / Province (Odoo)',
        help='Chọn tỉnh/thành phố từ dữ liệu có sẵn của Odoo (sau sáp nhập). '
             'Tên điểm đến sẽ được tự động điền và cho phép sửa lại.',
    )
    x_psm_country_id = fields.Many2one(
        'res.country',
        string='Country',
        compute='_compute_country_id',
        store=True,
        readonly=True,
    )
    x_psm_is_international = fields.Boolean(
        string='Is International',
        compute='_compute_is_international',
        store=True,
        readonly=True,
    )
    x_psm_zone_id = fields.Many2one('x_psm_travel_zone', string='Zone')
    x_psm_is_adjacent_hcm = fields.Boolean(string='Adjacent to HCM', help='BD, LA, TG, TN, DN, BRVT')


    @api.depends('x_psm_state_id')
    def _compute_country_id(self):
        for rec in self:
            rec.x_psm_country_id = rec.x_psm_state_id.country_id if rec.x_psm_state_id else False

    @api.depends('x_psm_country_id')
    def _compute_is_international(self):
        vietnam = self.env.ref('base.vn', raise_if_not_found=False)
        for rec in self:
            if rec.x_psm_country_id and vietnam:
                rec.x_psm_is_international = rec.x_psm_country_id.id != vietnam.id
            else:
                rec.x_psm_is_international = False

    @api.onchange('x_psm_state_id')
    def _onchange_state_id(self):
        if self.x_psm_state_id:
            self.x_psm_name = self.x_psm_state_id.name
