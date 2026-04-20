# -*- coding: utf-8 -*-
from odoo import models, fields, api

class ResUsers(models.Model):
    _inherit = 'res.users'

    x_is_portal_manager = fields.Boolean(
        string="Is Portal Manager",
        help="Check this box if this portal user manages other users (e.g. DM, SM)."
    )

    @api.model
    def _fix_portal_groups(self):
        """
        Cleanup groups for portal users before update to avoid
        'The user cannot have more than one user types' error.
        """
        # List of user logins to reset
        logins = ['dm@master.com', 'sm@master.com', 'crew@master.com']
        users = self.search([('login', 'in', logins)])
        if users:
            # Remove all groups to avoid conflicts
            # We will re-assign them in the XML data
            users.write({'group_ids': [(5, 0, 0)]})
