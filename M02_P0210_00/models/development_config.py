from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class DevelopmentConfig(models.Model):
    _name = 'mcd.development.config'
    _description = 'Manager Development Configuration'
    _order = 'development_type'
    _rec_name = 'display_name'

    development_type = fields.Selection([
        ('shift_manager', 'Develop to Shift Manager'),
        ('dm1', 'Develop to DM1'),
        ('dm2', 'Develop to DM2'),
        ('rgm', 'Develop to RGM'),
    ], string='Development Type', required=True)
    
    display_name = fields.Char(compute='_compute_display_name', store=True)
    
    # Course and Exam Lines
    course_line_ids = fields.One2many('mcd.development.config.line', 'config_id', 
                                       string='List of Courses & Exams')
    
    active = fields.Boolean(default=True)
    company_id = fields.Many2one('res.company', string='Company', 
                                  default=lambda self: self.env.company)
    
    @api.constrains('development_type', 'company_id')
    def _check_unique_development_type(self):
        """Check that only one config per development type exists (including inactive)"""
        for record in self:
            # Search for existing config with same type (include inactive)
            existing = self.with_context(active_test=False).search([
                ('development_type', '=', record.development_type),
                ('company_id', '=', record.company_id.id),
                ('id', '!=', record.id)
            ], limit=1)
            if existing:
                type_labels = {
                    'shift_manager': 'Shift Manager',
                    'dm1': 'DM1',
                    'dm2': 'DM2',
                    'rgm': 'RGM',
                }
                type_name = type_labels.get(record.development_type, record.development_type)
                raise ValidationError(
                    _('Configuration for "%s" already exists! Please reactivate the old configuration instead of creating a new one.') % type_name
                )
    
    def unlink(self):
        """Prevent deletion - archive instead"""
        raise ValidationError(_('Cannot delete configuration! Please archive it instead of deleting.'))
    
    @api.depends('development_type')
    def _compute_display_name(self):
        type_labels = {
            'shift_manager': 'Shift Manager',
            'dm1': 'DM1',
            'dm2': 'DM2',
            'rgm': 'RGM',
        }
        for rec in self:
            rec.display_name = f"Configuration {type_labels.get(rec.development_type, '')}"


class DevelopmentConfigLine(models.Model):
    _name = 'mcd.development.config.line'
    _description = 'Development Config Course Line'
    _order = 'sequence'
    _rec_name = 'course_name'
    
    config_id = fields.Many2one('mcd.development.config', string='Config', 
                                 required=True, ondelete='cascade')
    sequence = fields.Integer(string='Sequence', default=10)
    
    course_name = fields.Char(string='Course Name', required=True)
    exam_name = fields.Char(string='Exam Name')
    
    evaluator_role = fields.Selection([
        ('rgm', 'RGM Evaluation'),
        ('oc', 'OC Evaluation'),
        ('lnd', 'L&D Evaluation'),
    ], string='Evaluator', required=True, default='rgm')
    
    slide_channel_id = fields.Many2one('slide.channel', string='eLearning Course',
                                        help='Link to eLearning Course (if any)')
    
    notes = fields.Text(string='Notes')
