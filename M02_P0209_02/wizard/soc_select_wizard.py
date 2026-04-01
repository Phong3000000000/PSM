from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
import logging

_logger = logging.getLogger(__name__)

class SocSelectWizard(models.TransientModel):
    _name = 'soc.select.wizard'
    _description = 'Select SOC Wizard'

    channel_id = fields.Many2one('slide.channel', string='Course', readonly=True)
    soc_ids = fields.Many2many('slide.slide', string='Select SOCs', 
                               domain="[('is_soc', '=', True)]",
                               required=True)

    @api.model
    def default_get(self, fields_list):
        _logger.info("SOC WIZARD: default_get called")
        res = super().default_get(fields_list)
        if 'channel_id' in fields_list and not res.get('channel_id'):
            channel_id = self.env.context.get('default_channel_id') or self.env.context.get('active_id')
            _logger.info(f"SOC WIZARD: Context Channel ID: {channel_id}")
            if channel_id:
                try:
                    res['channel_id'] = int(channel_id)
                except (ValueError, TypeError):
                     _logger.error(f"SOC WIZARD: Invalid Channel ID: {channel_id}")
        return res

    def action_add_socs(self):
        """Add selected SOCs to the channel"""
        self.ensure_one()
        if not self.channel_id:
             raise UserError(_("No course found. Please access this wizard from a Training Path."))
             
        added_count = 0
        skipped_count = 0
        
        for soc in self.soc_ids:
            # Check if SOC already exists in this channel
            existing = self.env['slide.slide'].search([
                ('channel_id', '=', self.channel_id.id),
                ('is_soc', '=', True),
                ('soc_code', '=', soc.soc_code),
            ], limit=1)
            
            if existing:
                skipped_count += 1
                continue
            
            # Create a copy of the SOC for this channel
            # soc_item_ids has copy=True, so items will be automatically copied
            new_soc = soc.copy({
                'channel_id': self.channel_id.id,
                'is_soc': True,
            })
            
            # Update copied items to clear version_id (they should link to slide, not version)
            if new_soc.soc_item_ids:
                new_soc.soc_item_ids.write({
                    'version_id': False,  # Clear version_id as items should link to slide
                })
            
            added_count += 1
        
        message = _('Added %(added)d SOC(s) to the course.', added=added_count)
        if skipped_count > 0:
            message += _(' %(skipped)d SOC(s) were skipped (already exist).', skipped=skipped_count)
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Success'),
                'message': message,
                'type': 'success',
                'sticky': False,
                'next': {'type': 'ir.actions.act_window_close'},
            }
        }
