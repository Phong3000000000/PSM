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
    
    # Target Job Position - granted upon completion
    job_id = fields.Many2one('hr.job', string='Target Job Position',
                              help='Job position granted when development is completed')
    
    # Course and Exam Lines
    course_line_ids = fields.One2many('mcd.development.config.line', 'config_id', 
                                       string='List of Courses & Exams')
    
    # Versioning
    version_ids = fields.One2many('mcd.development.config.version', 'config_id',
                                   string='Versions')
    active_version_id = fields.Many2one('mcd.development.config.version',
                                         string='Active Version',
                                         domain="[('config_id', '=', id)]")
    
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

    def action_save_as_version(self):
        """Save current config as a new version"""
        self.ensure_one()
        
        # Calculate next version number
        next_version = "1.0"
        if self.version_ids:
            latest = self.version_ids.sorted('create_date', reverse=True)[0]
            try:
                current_val = float(latest.name)
                next_version = str(round(current_val + 0.1, 1))
            except ValueError:
                next_version = f"{latest.name}.1"
        
        # Create version
        version = self.env['mcd.development.config.version'].create({
            'name': next_version,
            'config_id': self.id,
            'job_id': self.job_id.id,
        })
        
        # Copy course lines to version
        for line in self.course_line_ids:
            self.env['mcd.development.config.version.line'].create({
                'version_id': version.id,
                'sequence': line.sequence,
                'course_name': line.course_name,
                'exam_name': line.exam_name,
                'evaluator_role': line.evaluator_role,
                'slide_channel_id': line.slide_channel_id.id,
                'notes': line.notes,
            })
        
        # Set as active version
        self.active_version_id = version.id
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Version Saved'),
                'message': _('Version %s has been saved and set as active.') % next_version,
                'type': 'success',
                'sticky': False,
            }
        }


class DevelopmentConfigVersion(models.Model):
    _name = 'mcd.development.config.version'
    _description = 'Development Config Version'
    _order = 'create_date desc'
    
    name = fields.Char(string='Version', required=True)
    config_id = fields.Many2one('mcd.development.config', string='Config',
                                 required=True, ondelete='cascade')
    
    job_id = fields.Many2one('hr.job', string='Target Job Position')
    line_ids = fields.One2many('mcd.development.config.version.line', 'version_id',
                                string='Course Lines')
    
    is_active = fields.Boolean(compute='_compute_is_active', string='Is Active')
    
    def _compute_is_active(self):
        for rec in self:
            rec.is_active = (rec.config_id.active_version_id == rec)
    
    def action_apply_version(self):
        """Apply this version to the config"""
        self.ensure_one()
        
        # Delete current lines
        self.config_id.course_line_ids.unlink()
        
        # Copy lines from version
        for line in self.line_ids:
            self.env['mcd.development.config.line'].create({
                'config_id': self.config_id.id,
                'sequence': line.sequence,
                'course_name': line.course_name,
                'exam_name': line.exam_name,
                'evaluator_role': line.evaluator_role,
                'slide_channel_id': line.slide_channel_id.id,
                'notes': line.notes,
            })
        
        # Update job position
        self.config_id.job_id = self.job_id.id
        
        # Set as active
        self.config_id.active_version_id = self.id
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Version Applied'),
                'message': _('Version %s has been applied.') % self.name,
                'type': 'success',
                'sticky': False,
                'next': {'type': 'ir.actions.client', 'tag': 'reload'},
            }
        }


class DevelopmentConfigVersionLine(models.Model):
    _name = 'mcd.development.config.version.line'
    _description = 'Development Config Version Line'
    _order = 'sequence'
    
    version_id = fields.Many2one('mcd.development.config.version', string='Version',
                                  required=True, ondelete='cascade')
    sequence = fields.Integer(string='Sequence', default=10)
    
    course_name = fields.Char(string='Course Name', required=True)
    exam_name = fields.Char(string='Exam Name')
    evaluator_role = fields.Selection([
        ('rgm', 'RGM Evaluation'),
        ('oc', 'OC Evaluation'),
        ('lnd', 'L&D Evaluation'),
    ], string='Evaluator', required=True, default='rgm')
    slide_channel_id = fields.Many2one('slide.channel', string='eLearning Course')
    notes = fields.Text(string='Notes')


class DevelopmentConfigLine(models.Model):
    _name = 'mcd.development.config.line'
    _description = 'Development Config Course Line'
    _order = 'sequence'
    
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

