from odoo import models, fields, api

import logging

_logger = logging.getLogger(__name__)

class SocImportWizard(models.TransientModel):
    _name = 'soc.import.wizard'
    _description = 'Import SOC Data Wizard'

    force_update = fields.Boolean(string="Force Update (Overwrite Existing)", default=False)

    def action_import_soc_data(self):
        """
        Load SOCs from static python file.
        """
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Feature Disabled',
                'message': 'Mock data import has been disabled.',
                'type': 'warning',
                'sticky': False,
                'next': {'type': 'ir.actions.act_window_close'},
            }
        }

    def _derive_channel_name(self, soc):
        t = soc['title'].lower()
        if 'rice' in t: return "Rice Station"
        if 'grill' in t: return "Grill Station"
        if 'fried' in t or 'fry' in t: return "Fried Station"
        if 'beverage' in t: return "Beverage Station"
        if 'dessert' in t: return "Dessert Station"
        if soc['sub_area'] == 'mccafe': return "McCafe Station"
        if soc['sub_area'] == 'production': return "Production General"
        return "General SOCs"

    def _get_or_create_section(self, name):
        name = name.strip() or "General"
        sec = self.env['mcd.soc.section'].search([('name', '=', name)], limit=1)
        if not sec:
            sec = self.env['mcd.soc.section'].create({'name': name})
        return sec
