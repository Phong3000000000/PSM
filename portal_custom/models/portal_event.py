from odoo import models, fields

class PortalEvent(models.Model):
    _name = 'portal.event'
    _description = 'Portal Upcoming Events'
    _order = 'date asc'

    name = fields.Char(string='Tên sự kiện', required=True)
    date = fields.Datetime(string='Thời gian', required=True)
    location = fields.Char(string='Địa điểm')
    color = fields.Selection([
        ('primary', 'Blue'),
        ('danger', 'Red'),
        ('warning', 'Yellow'),
        ('success', 'Green'),
        ('info', 'Cyan')
    ], string='Màu sắc', default='primary')
    image = fields.Image(string="Hình ảnh minh họa")
