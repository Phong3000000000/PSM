import datetime
import logging
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError

_logger = logging.getLogger(__name__)

class SlideChannel(models.Model):
    _inherit = 'slide.channel'
    
    # We keep minimal SOC info on Channel to act as a container/filter
    is_soc_course = fields.Boolean(string='Is SOC Course', default=False)
    
    # Method moved to SlideSlide to be accessible from O2M control
    
    soc_station_id = fields.Many2one('mcd.soc.station', string='Linked Station')
    soc_area_id = fields.Many2one('mcd.soc.area', related='soc_station_id.area_id', string='Linked Area', store=True)

    def action_open_soc_select_wizard(self):
        """Open wizard to select existing SOCs to add to this course.
        Called from Form Header.
        """
        self.ensure_one()
        
        if not self.id:
             raise UserError(_("Please save the Training Path (Course) first before adding SOCs."))

        # Explicitly get the view to avoid resolution errors
        view = self.env.ref('M02_P0209_01.view_soc_select_wizard_form', raise_if_not_found=False)
        view_id = view.id if view else False
        
        return {
            'type': 'ir.actions.act_window',
            'name': 'Add SOC to Course',
            'res_model': 'soc.select.wizard',
            'view_mode': 'form',
            'views': [[view_id, 'form']],
            'target': 'new',
            'context': {
                'default_channel_id': self.id,
            }
        }



class SlideSlide(models.Model):
    _inherit = 'slide.slide'

    @api.model_create_multi
    def create(self, vals_list):
        _logger.info("SOC CREATE: vals_list=%s", vals_list)
        for vals in vals_list:
            is_soc = vals.get('is_soc') or self.env.context.get('default_is_soc')
            if is_soc:
                # Auto-generate code if empty or not provided
                soc_code = vals.get('soc_code', '').strip() if vals.get('soc_code') else ''
                if not soc_code:
                    code = self.env['ir.sequence'].next_by_code('mcd.soc.code')
                    if not code:
                        _logger.warning("SOC Sequence 'mcd.soc.code' NOT FOUND. Make sure to update the module.")
                        code = 'SOC-NEW'
                    _logger.info("SOC CREATE: Generated code=%s", code)
                    vals['soc_code'] = code
                if not vals.get('soc_version'):
                    version = datetime.datetime.now().strftime('%m%Y')
                    _logger.info("SOC CREATE: Generated version=%s", version)
                    vals['soc_version'] = version
        return super().create(vals_list)

    def write(self, vals):
        _logger.info("SOC WRITE: vals=%s", vals)
        for record in self:
            is_soc = vals.get('is_soc', record.is_soc)
            if is_soc:
                # Auto-generate code if empty or cleared
                if 'soc_code' in vals:
                    soc_code = vals.get('soc_code', '').strip() if vals.get('soc_code') else ''
                    if not soc_code:
                        code = self.env['ir.sequence'].next_by_code('mcd.soc.code')
                        if not code:
                            _logger.warning("SOC Sequence 'mcd.soc.code' NOT FOUND. Make sure to update the module.")
                            code = 'SOC-UPD'
                        _logger.info("SOC WRITE: Generated code=%s", code)
                        vals['soc_code'] = code
                # If record has no code and not being set in vals, generate it
                elif not record.soc_code or (record.soc_code and not record.soc_code.strip()):
                    code = self.env['ir.sequence'].next_by_code('mcd.soc.code')
                    if not code:
                        _logger.warning("SOC Sequence 'mcd.soc.code' NOT FOUND. Make sure to update the module.")
                        code = 'SOC-FIX'
                    _logger.info("SOC WRITE: Generated code=%s for existing record", code)
                    vals['soc_code'] = code

                if 'soc_version' in vals and not vals.get('soc_version'):
                    vals['soc_version'] = datetime.datetime.now().strftime('%m%Y')
                elif not record.soc_version and not vals.get('soc_version'):
                    vals['soc_version'] = datetime.datetime.now().strftime('%m%Y')
                    
        return super().write(vals)

    def _compute_display_name(self):
        for record in self:
            if record.soc_code and record.is_soc:
                record.display_name = f"[{record.soc_code}] {record.name}"
            else:
                record.display_name = record.name

    is_soc = fields.Boolean(string='Is SOC content', default=False)

    # ── Lock/Unlock Control ──────────────────────────────────────────────────
    # False  = New record (editable by default)
    # True   = Locked after import/finalized  (readonly for normal users)
    is_locked = fields.Boolean(
        string='Locked',
        default=False,
        tracking=True,
        help='Khoá lại không cho sửa trực tiếp. Dùng nút "🔓 Chỉnh sửa" để mở khoá.'
    )

    def action_lock(self):
        """🔒 Khoá lại – set is_locked=True"""
        for rec in self:
            rec.is_locked = True
            rec.message_post(body="🔒 SOC đã được khoá lại (readonly).")

    def action_unlock(self):
        """🔓 Mở khoá – set is_locked=False"""
        for rec in self:
            rec.is_locked = False
            rec.message_post(body="🔓 SOC đã được mở khoá để chỉnh sửa.")

    # 1. Header Info
    soc_code = fields.Char(string='Code')
    
    @api.onchange('is_soc', 'soc_code')
    def _onchange_soc_code_auto_generate(self):
        """Auto-generate SOC code when is_soc is True and code is empty"""
        if self.is_soc:
            # If code is empty or only whitespace, generate it
            if not self.soc_code or not self.soc_code.strip():
                code = self.env['ir.sequence'].next_by_code('mcd.soc.code')
                if not code:
                    code = 'SOC-NEW'
                self.soc_code = code
    soc_version = fields.Char(string='Version')
    soc_type_id = fields.Many2one('mcd.soc.type', string='SOC Type')
    
    # 2. Classification
    soc_area_id = fields.Many2one('mcd.soc.area', string='Area')
    
    soc_station_id = fields.Many2one('mcd.soc.station', string='Station', domain="[('area_id', '=', soc_area_id), ('soc_type_ids', 'in', soc_type_id)]")

    document_type = fields.Selection([
        ('permanent', 'Permanent'),
        ('temporary', 'Temporary')
    ], string='Document Type', default='permanent')

    # 4. Scoring & Logic
    # 4. Scoring & Logic (Stored on Slide for Editing)
    pass_score = fields.Float(string='Pass Score (%)', default=100.0)
    time_allowed = fields.Float(string='Time Allowed (Minutes)', default=15.0)
    soc_prerequisite_ids = fields.Many2many('slide.slide', 'soc_slide_prereq_rel', 'source_id', 'prereq_id', string='Prerequisites')

    # 3. Content (Stored on Slide for Editing)
    soc_item_ids = fields.One2many('mcd.soc.item', 'slide_id', string='Checklist Items', copy=True)
    
    # Versioning
    version_ids = fields.One2many('mcd.soc.version', 'slide_id', string='Versions')
    active_version_id = fields.Many2one('mcd.soc.version', string='Active Version', domain="[('slide_id', '=', id)]")

    # Linked Skill
    soc_skill_type_id = fields.Many2one('hr.skill.type', string='Skill Type')
    soc_skill_id = fields.Many2one('hr.skill', string='Granted Skill', domain="[('skill_type_id', '=', soc_skill_type_id)]")
    soc_skill_level_id = fields.Many2one('hr.skill.level', string='Skill Level to Grant', domain="[('skill_type_id', '=', soc_skill_type_id)]")
    
    @api.onchange('soc_skill_type_id')
    def _onchange_soc_skill_type_id(self):
        self.soc_skill_id = False
        self.soc_skill_level_id = False
    
    # Override defaults - REMOVED to avoid DB creation error
    # user_id = fields.Many2one('res.users', default=lambda self: self.env.user, readonly=True)

    @api.onchange('soc_area_id')
    def _onchange_soc_area_id(self):
        if self.soc_area_id:
            return {'domain': {'soc_station_id': [('area_id', '=', self.soc_area_id.id)]}}
        return {'domain': {'soc_station_id': []}}

    @api.onchange('soc_station_id')
    def _onchange_soc_station_id(self):
        """Auto-link Course (Channel) when Station is selected"""
        if self.soc_station_id and self.soc_station_id.channel_id:
            self.channel_id = self.soc_station_id.channel_id

    @api.onchange('channel_id')
    def _onchange_channel_id_soc(self):
        if self.channel_id and self.channel_id.soc_station_id:
             self.soc_station_id = self.channel_id.soc_station_id
             if self.soc_station_id.area_id:
                 self.soc_area_id = self.soc_station_id.area_id

    # Make channel_id optional to allow creation via SOC form without initial channel
    channel_id = fields.Many2one('slide.channel', string='Course', required=False)

    @api.constrains('is_soc', 'soc_code', 'soc_version', 'soc_type_id', 'document_type', 
                   'soc_area_id', 'soc_station_id', 'soc_skill_id', 'soc_skill_level_id')
    def _check_soc_required_fields(self):
        for record in self:
            if record.is_soc and record.is_published: # Only check strictly on publish
                missing = []
                if not record.soc_type_id: missing.append('SOC Type')
                if not record.document_type: missing.append('Document Type')
                if not record.soc_area_id: missing.append('Area')
                if not record.soc_station_id: missing.append('Station')
                if not record.soc_skill_type_id: missing.append('Skill Type')
                if not record.soc_skill_id: missing.append('Granted Skill')
                if not record.soc_skill_level_id: missing.append('Skill Level to Grant')
                if not record.soc_item_ids: missing.append('Checklist Items')

                if missing:
                    raise ValidationError(_("For SOC Content, the following fields are mandatory:\n- %s") % '\n- '.join(missing))

    def _sync_to_active_version(self):
        """
        Sync current Slide data to the Active Version (Snapshot).
        This ensures the version record matches the main editor.
        """
        self.ensure_one()
        if not self.active_version_id:
            return

        # 1. Update Header fields
        self.active_version_id.with_context(from_sync=True).write({
            'pass_score': self.pass_score,
            'time_allowed': self.time_allowed,
            'description': self.description,
            'html_content': self.html_content,
            'datas': self.binary_content,
            'slide_category_code': self.slide_category,
            'soc_code': self.soc_code,
            'soc_type_id': self.soc_type_id.id,
            'soc_area_id': self.soc_area_id.id,
            'soc_station_id': self.soc_station_id.id,
            'document_type': self.document_type,
            'datas_filename': self.name,
            'soc_title': self.name,
            'soc_tag_ids': [(6, 0, self.tag_ids.ids)],
            'soc_image': self.image_1920,
        })
        
        # 2. Sync Items (Full Replacement for simplicity and accuracy)
        # Remove old items in version
        self.active_version_id.item_ids.unlink()
        
        # Create new items in version based on Slide items
        new_items = []
        for item in self.soc_item_ids:
            new_items.append({
                'version_id': self.active_version_id.id,
                'section_id': item.section_id.id,
                'sequence': item.sequence,
                'name': item.name,
            })
        _logger.info("SOC SYNC ITEMS: Found %s items to sync", len(new_items))
        if new_items:
            # Context from_sync=True prevents Version Items from triggering reverse sync back to Slide
            self.env['mcd.soc.item'].with_context(from_sync=True).create(new_items)

    @api.model_create_multi
    def create(self, vals_list):
        slides = super(SlideSlide, self).create(vals_list)
        for slide in slides:
            if slide.is_soc and not slide.active_version_id and not slide.version_ids:
                # 1. Auto-create v1.0
                version = self.env['mcd.soc.version'].create({
                    'name': '1.0',
                    'slide_id': slide.id,
                    'user_id': slide.user_id.id,
                })
                # 2. Link as active
                # Use skip_sync=True to prevent the "Version Switch logic" in write() from triggering
                # and wiping the newly created items with empty version data.
                slide.with_context(skip_sync=True).write({'active_version_id': version.id})
                # 3. Sync initial data (if any was provided in vals)
                slide._sync_to_active_version()
        return slides

    def write(self, vals):
        # 1. Standard Write
        res = super(SlideSlide, self).write(vals)
        
        # 2. Post-Write Sync
        if not self._context.get('skip_sync') and any(f in vals for f in ['pass_score', 'time_allowed', 'soc_item_ids', 'description', 
                                  'html_content', 'binary_content', 'slide_category', 'soc_code', 'soc_type_id', 'soc_area_id', 
                                  'soc_station_id', 'document_type']):
            for slide in self:
                if slide.is_soc and slide.active_version_id:
                     slide._sync_to_active_version()
        
        # 3. Handle Active Version Switch (Load Data)
        if 'active_version_id' in vals and not self._context.get('skip_sync'):
             for slide in self:
                 if slide.is_soc and slide.active_version_id:
                     # Load data FROM version TO slide (Reverse Sync)
                     # Important: Use write to update self, but don't trigger sync loop!
                     # We can use context to avoid loop if needed, but here simple assignment usually triggers write.
                     # But we are INSIDE write.
                     # We just need to update columns.
                     v = slide.active_version_id
                     
                     # Update fields (Prevent loop by context check or check equality)
                     # actually, if we just switched version, we W WANT to overwrite slide content.
                     
                     # Copy Items
                     # Delete current slide items
                     slide.soc_item_ids.unlink()
                     
                     items_copy = []
                     for item in v.item_ids:
                         items_copy.append({
                             'slide_id': slide.id, 
                             'sequence': item.sequence,
                             'sequence': item.sequence,
                             'name': item.name,
                             'description': item.description,
                         })
                     
                     # We must use SQL or new write to update within write?
                     # Ideally avoiding recursion. 
                     # Let's perform a separate write with context to skip sync
                     slide.with_context(skip_sync=True).write({
                         'pass_score': v.pass_score,
                         'time_allowed': v.time_allowed,
                     })
                     if items_copy:
                         self.env['mcd.soc.item'].with_context(skip_sync=True).create(items_copy)

        return res

    def action_prepare_new_version(self):
        """
        Open the SOC Version creation form with data pre-filled from the current Slide.
        This allows the user to 'Edit' the SOC by creating a new version.
        """
        self.ensure_one()
        
        # Prepare Checklist Items
        # We need to pass them as (0, 0, vals) tuples to create copies in the new version
        default_items = []
        for item in self.soc_item_ids:
            default_items.append((0, 0, {
                'section_id': item.section_id.id,
                'sequence': item.sequence,
                'name': item.name,
            }))

        # Auto-calculate next version name
        # Default start
        next_version = "1.0"
        
        # Find latest version
        latest_version = self.env['mcd.soc.version'].search([
            ('slide_id', '=', self.id)
        ], order='create_date desc, id desc', limit=1)
        
        if latest_version and latest_version.name:
            try:
                # Try to parse as float (1.0 -> 1.1)
                current_val = float(latest_version.name)
                next_val = round(current_val + 0.1, 1) # simple increment
                next_version = str(next_val)
            except ValueError:
                # Fallback if non-numeric
                next_version = f"{latest_version.name}.1"

        return {
            'type': 'ir.actions.act_window',
            'name': 'Save as New Version',
            'res_model': 'mcd.soc.version',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_name': next_version,
                'default_slide_id': self.id,
                # Header Defaults from Slide
                'default_soc_code': self.soc_code,
                'default_soc_type_id': self.soc_type_id.id,
                'default_soc_area_id': self.soc_area_id.id,
                'default_soc_station_id': self.soc_station_id.id,
                'default_document_type': self.document_type,
                'default_pass_score': self.pass_score,
                'default_time_allowed': self.time_allowed,
                
                # Snapshot Defaults
                'default_soc_title': self.name,
                'default_soc_tag_ids': [(6, 0, self.tag_ids.ids)],
                'default_soc_image': self.image_1920,
                
                # Content Defaults
                'default_description': self.description,
                'default_html_content': self.html_content,
                'default_datas': self.binary_content,
                'default_datas_filename': self.name, # Or calculate filename if stored
                'default_slide_category_code': self.slide_category,
                
                # Checklist Items
                'default_item_ids': default_items,
            }
        }

    def action_open_soc_view(self):
        self.ensure_one()
        url = f"/slides/soc/take/{self.id}"
        return {
            'type': 'ir.actions.act_url',
            'url': url,
            'target': 'new',
        }

    def action_open_soc_select_wizard(self):
        """Open wizard to select existing SOCs to add to this course."""
        # Retrieve context safely
        ctx = dict(self.env.context or {})
        channel_id = ctx.get('default_channel_id') or ctx.get('active_id')
        
        # When called from button in o2m, self might be non-empty if record is saved
        if not channel_id and self:
            channel_id = self.channel_id.id or ctx.get('active_id')

        # Robust casting
        if hasattr(channel_id, 'id'):
            channel_id = channel_id.id
            
        try:
             # Ensure integer
             channel_id = int(channel_id) if channel_id else False
        except (ValueError, TypeError):
             channel_id = False

        if not channel_id:
             raise UserError(_("Please save the Training Path (Course) first before adding SOCs."))

        # Simplified return - let Odoo resolve the view
        return {
            'type': 'ir.actions.act_window',
            'name': 'Add SOC to Course',
            'res_model': 'soc.select.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_channel_id': channel_id,
            }
        }

    def _grant_soc_skill(self, user):
        """
        Grant the skill defined in this SOC to the user's employee record.
        Wrapper for new method grant_soc_skill_to_employee.
        """
        self.ensure_one()
        employee = self.env['hr.employee'].search([('user_id', '=', user.id)], limit=1)
        if not employee:
            return False
            
        return self.grant_soc_skill_to_employee(employee)

    def grant_soc_skill_to_employee(self, employee):
        """
        Grant the skill defined in this SOC to the specific hr.employee record.
        """
        self.ensure_one()
        if not self.soc_skill_id or not self.soc_skill_level_id:
            return False

        EmployeeSkill = self.env['hr.employee.skill']
        
        # Check if employee already has this skill
        existing_skill = EmployeeSkill.search([
            ('employee_id', '=', employee.id),
            ('skill_id', '=', self.soc_skill_id.id)
        ], limit=1)

        if existing_skill:
            # Upgrade level if new level is higher
            if self.soc_skill_level_id.level_progress > existing_skill.skill_level_id.level_progress:
                existing_skill.write({'skill_level_id': self.soc_skill_level_id.id})
                return "upgraded"
            return "existing"
        else:
            # Create new skill
            EmployeeSkill.create({
                'employee_id': employee.id,
                'skill_id': self.soc_skill_id.id,
                'skill_level_id': self.soc_skill_level_id.id,
                'skill_type_id': self.soc_skill_id.skill_type_id.id,
            })
            return "granted"

    def check_soc_access_rights(self, user):
        """
        Check if user meets prerequisites.
        Returns: (Boolean, List of missing prerequisite names)
        """
        self.ensure_one()
        if not self.soc_prerequisite_ids:
            return True, []

        employee = self.env['hr.employee'].search([('user_id', '=', user.id)], limit=1)
        missing_prereqs = []

        for prereq in self.soc_prerequisite_ids:
            is_met = False
            
            # Strategy A: Check by Skill (Preferred)
            if prereq.soc_skill_id and employee:
                has_skill = self.env['hr.employee.skill'].search_count([
                    ('employee_id', '=', employee.id),
                    ('skill_id', '=', prereq.soc_skill_id.id)
                ])
                if has_skill:
                    is_met = True
            
            # Strategy B: Check by Slide Completion (Fallback)
            if not is_met and not prereq.soc_skill_id:
                 has_completed = self.env['slide.slide.partner'].search_count([
                    ('slide_id', '=', prereq.id),
                    ('partner_id', '=', user.partner_id.id),
                    ('completed', '=', True)
                ])
                 if has_completed:
                     is_met = True

            if not is_met:
                missing_prereqs.append(prereq.name)
        
        return len(missing_prereqs) == 0, missing_prereqs

class McdSocVersion(models.Model):
    _name = 'mcd.soc.version'
    _description = 'SOC Version'
    _order = 'create_date desc, id desc'
    
    name = fields.Char(string='Version', required=True)
    slide_id = fields.Many2one('slide.slide', string='SOC Template', required=True, ondelete='cascade')
    user_id = fields.Many2one('res.users', string='Created By', default=lambda self: self.env.user, readonly=True)
    
    pass_score = fields.Float(string='Pass Score (%)', default=100.0)
    time_allowed = fields.Float(string='Time Allowed (Minutes)', default=15.0)
    
    item_ids = fields.One2many('mcd.soc.item', 'version_id', string='Checklist Items')
    
    # Snapshot Fields
    description = fields.Html(string='Description', sanitize_attributes=False, sanitize_overridable=True)
    html_content = fields.Html(string='Content')
    datas = fields.Binary(string='Content (File)')
    datas_filename = fields.Char(string='Filename')
    slide_category = fields.Selection(related='slide_id.slide_category', store=True) # Store creation time category? Better to store independently?
    # Actually related store=True won't snapshot updates correctly if we want strictly snapshot. 
    # Let's make it a normal field and sync it.
    slide_category_code = fields.Selection([
        ('infographic', 'Infographic'),
        ('article', 'Article'),
        ('document', 'Document'),
        ('video', 'Video'),
        ('quiz', 'Quiz')
    ], string='Category')

    soc_code = fields.Char(string='Code')
    soc_type_id = fields.Many2one('mcd.soc.type', string='SOC Type')
    
    soc_area_id = fields.Many2one('mcd.soc.area', string='Area')
    
    soc_station_id = fields.Many2one('mcd.soc.station', string='Station')

    document_type = fields.Selection([
        ('permanent', 'Permanent'),
        ('temporary', 'Temporary')
    ], string='Document Type')
    
    # Snapshot Metadata
    soc_title = fields.Char(string='SOC Title')
    soc_tag_ids = fields.Many2many('slide.tag', string='Tags')
    soc_image = fields.Binary(string='Image')

    is_active_version = fields.Boolean(compute='_compute_is_active_version', string='Is Active Version')

    def _compute_is_active_version(self):
        for record in self:
            record.is_active_version = (record.slide_id.active_version_id == record)
            
    def write(self, vals):
        """
        If this is the Active Version, sync changes back to the Slide immediately.
        This prevents data loss if the user edits the Active Version directly.
        """
        res = super(McdSocVersion, self).write(vals)
        for record in self:
            if record.is_active_version and not self.env.context.get('from_sync'):
                 # Check if any content fields or metadata fields were changed
                 content_fields = ['pass_score', 'time_allowed', 'description', 'soc_code', 
                                   'soc_type_id', 'soc_area_id', 'soc_station_id', 'document_type',
                                   'soc_title', 'soc_tag_ids', 'soc_image']
                 if any(f in vals for f in content_fields):
                     record.action_restore_version()
        return res
            
    def action_restore_version(self):
        """Set this version as the active version for the slide"""
        self.ensure_one()
        # Restore Snapshot Data to Slide
        vals = {
            'active_version_id': self.id,
            'description': self.description,
            'soc_code': self.soc_code,
            'soc_type_id': self.soc_type_id.id,
            'soc_area_id': self.soc_area_id.id,
            'soc_station_id': self.soc_station_id.id,
            'document_type': self.document_type,
            'pass_score': self.pass_score,
            'time_allowed': self.time_allowed,
            'name': self.soc_title,
            'tag_ids': [(6, 0, self.soc_tag_ids.ids)],
            'image_1920': self.soc_image,
        }
        
        # Restore Content based on category
        if self.slide_category_code == 'article':
            vals['html_content'] = self.html_content
            # Clear datas if switching to article? Odoo standard might handle this but let's be safe
            vals['binary_content'] = False 
        elif self.slide_category_code in ['document', 'infographic']:
            vals['binary_content'] = self.datas
            # We don't have a filename field on slide.slide to write back to? 
            # slide.slide usually derives it or doesn't store it explicitly if uploaded via widget?
            # actually checking standard odoo, binary_content often goes with a filename field in context or similar?
            # but slide.slide uses 'name' often.
            vals['html_content'] = False
            
        # We generally don't change slide_category on restore? Or should we?
        # If user changed from Article to Document, and restoring an Article version...
        # It's safer to restore category too.
        if self.slide_category_code:
            vals['slide_category'] = self.slide_category_code

        # Restore Checklist Items
        # We replace all existing items on the slide with the items from this version
        item_commands = [(5, 0, 0)] # Command to delete all existing records
        for item in self.item_ids:
            item_commands.append((0, 0, {
                'section_id': item.section_id.id,
                'sequence': item.sequence,
                'name': item.name,
            }))
        vals['soc_item_ids'] = item_commands

        # Use skip_sync=True to prevent Slide from triggering _sync_to_active_version again
        self.slide_id.with_context(skip_sync=True).write(vals)
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Version Restored',
                'message': f'Version {self.name} has been restored as the active template.',
                'type': 'success',
                'sticky': False,
                'next': {'type': 'ir.actions.client', 'tag': 'reload'},
            }
        }

    _sql_constraints = [
        ('name_slide_uniq', 'unique (name, slide_id)', 'Version name must be unique per SOC Template!')
    ]

class McdSocSection(models.Model):
    _name = 'mcd.soc.section'
    _description = 'SOC Section'
    _order = 'sequence, id'
    
    name = fields.Char(required=True)
    sequence = fields.Integer(default=10)

class McdSocItem(models.Model):
    _name = 'mcd.soc.item'
    _description = 'SOC Checklist Item'
    _order = 'sequence, id'

    # Hybrid Model: Item can belong to a Version (Snapshot) OR a Slide (Draft/Active)
    version_id = fields.Many2one('mcd.soc.version', string='SOC Version', ondelete='cascade')
    slide_id = fields.Many2one('slide.slide', string='SOC Template (Draft)', ondelete='cascade')
    
    section_id = fields.Many2one('mcd.soc.section', string='Section')
    
    sequence = fields.Integer(default=10)
    name = fields.Text(string='Description', required=True)
    is_critical = fields.Boolean(string='Critical (K.O)', default=False)

    def create(self, vals_list):
        items = super(McdSocItem, self).create(vals_list)
        # If created on an Active Version, sync to Slide
        # Check context to avoid recursion if we are creating items FROM sync
        if not self.env.context.get('from_sync'):
            for item in items:
                if item.version_id and item.version_id.is_active_version:
                    item.version_id.action_restore_version()
        return items

    def write(self, vals):
        res = super(McdSocItem, self).write(vals)
        # If updated on an Active Version, sync to Slide
        if not self.env.context.get('from_sync'):
            for item in self:
                if item.version_id and item.version_id.is_active_version:
                    item.version_id.action_restore_version()
        return res

    def unlink(self):
        # Check before deletion if we need to sync
        versions_to_sync = self.mapped('version_id').filtered('is_active_version')
        res = super(McdSocItem, self).unlink()
        if not self.env.context.get('from_sync'):
            for version in versions_to_sync:
                 version.action_restore_version()
        return res
    
    def action_open_soc_view(self):
        self.ensure_one()
        url = f"/slides/soc/take/{self.id}"
        return {
            'type': 'ir.actions.act_url',
            'url': url,
            'target': 'new',
        }

    def _grant_soc_skill(self, user):
        """
        Grant the skill defined in this SOC to the user's employee record.
        Wrapper for new method grant_soc_skill_to_employee.
        """
        self.ensure_one()
        employee = self.env['hr.employee'].search([('user_id', '=', user.id)], limit=1)
        if not employee:
            return False
            
        return self.grant_soc_skill_to_employee(employee)

    def grant_soc_skill_to_employee(self, employee):
        """
        Grant the skill defined in this SOC to the specific hr.employee record.
        """
        self.ensure_one()
        if not self.soc_skill_id or not self.soc_skill_level_id:
            return False

        EmployeeSkill = self.env['hr.employee.skill']
        
        # Check if employee already has this skill
        existing_skill = EmployeeSkill.search([
            ('employee_id', '=', employee.id),
            ('skill_id', '=', self.soc_skill_id.id)
        ], limit=1)

        if existing_skill:
            # Upgrade level if new level is higher
            if self.soc_skill_level_id.level_progress > existing_skill.skill_level_id.level_progress:
                existing_skill.write({'skill_level_id': self.soc_skill_level_id.id})
                return "upgraded"
            return "existing"
        else:
            # Create new skill
            EmployeeSkill.create({
                'employee_id': employee.id,
                'skill_id': self.soc_skill_id.id,
                'skill_level_id': self.soc_skill_level_id.id,
                'skill_type_id': self.soc_skill_id.skill_type_id.id,
            })
            return "granted"

    def check_soc_access_rights(self, user):
        """
        Check if user meets prerequisites.
        Returns: (Boolean, List of missing prerequisite names)
        """
        self.ensure_one()
        if not self.soc_prerequisite_ids:
            return True, []

        employee = self.env['hr.employee'].search([('user_id', '=', user.id)], limit=1)
        missing_prereqs = []

        for prereq in self.soc_prerequisite_ids:
            is_met = False
            
            # Strategy A: Check by Skill (Preferred)
            if prereq.soc_skill_id and employee:
                has_skill = self.env['hr.employee.skill'].search_count([
                    ('employee_id', '=', employee.id),
                    ('skill_id', '=', prereq.soc_skill_id.id)
                ])
                if has_skill:
                    is_met = True
            
            # Strategy B: Check by Slide Completion (Fallback)
            if not is_met and not prereq.soc_skill_id:
                 has_completed = self.env['slide.slide.partner'].search_count([
                    ('slide_id', '=', prereq.id),
                    ('partner_id', '=', user.partner_id.id),
                    ('completed', '=', True)
                ])
                 if has_completed:
                     is_met = True

            if not is_met:
                missing_prereqs.append(prereq.name)
        
        return len(missing_prereqs) == 0, missing_prereqs

