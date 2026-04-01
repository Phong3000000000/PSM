from odoo import models, fields, api

class McdSocType(models.Model):
    _name = 'mcd.soc.type'
    _description = 'SOC Document Type'
    
    name = fields.Char(string='Name', required=True)
    code = fields.Char(string='Code')

class McdSocArea(models.Model):
    _name = 'mcd.soc.area'
    _description = 'SOC Area'
    
    name = fields.Char(string='Name', required=True)
    code = fields.Char(string='Code')

class McdSocStation(models.Model):
    _name = 'mcd.soc.station'
    _description = 'SOC Station'
    _order = 'name'
    
    name = fields.Char(string='Station Name', required=True)
    code = fields.Char(string='Code')

    area_id = fields.Many2one('mcd.soc.area', string='Area', required=True)
    soc_type_ids = fields.Many2many('mcd.soc.type', string='Allowed Document Types')

    # Service type configuration
    service_type = fields.Selection([
        ('permanent', 'Permanent Service'),
        ('lto', 'LTO'),
        ('na', 'N/A'),
    ], string='Service Type', default='permanent')

    # Check type availability
    has_initial = fields.Boolean(string='Initial Check', default=True)
    has_unannounced = fields.Boolean(string='Unannounced Check', default=False)

    # Link to Training Path (Course)
    channel_id = fields.Many2one('slide.channel', string='Training Path', readonly=True, help="Auto-created Course for this Station")

    @api.model_create_multi
    def create(self, vals_list):
        records = super(McdSocStation, self).create(vals_list)
        for record in records:
            if not record.channel_id:
                channel = self.env['slide.channel'].create({
                    'name': record.name,
                    'is_published': True,
                    'soc_station_id': record.id,
                    'description': f"Training Path for Station: {record.name}",
                    'enroll': 'public', 
                    'channel_type': 'training',
                    'promote_strategy': 'most_voted',
                })
                record.channel_id = channel.id
        return records

    def write(self, vals):
        res = super(McdSocStation, self).write(vals)
        if 'name' in vals:
            for record in self:
                if record.channel_id:
                    record.channel_id.name = vals['name']
        return res
