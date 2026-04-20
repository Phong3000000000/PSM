# -*- coding: utf-8 -*-

from odoo import models


class ResUsers(models.Model):
    _inherit = 'res.users'

    def _x_psm_0204_get_portal_employee(self):
        """Return linked employee for portal-role resolution."""
        self.ensure_one()

        user_sudo = self.sudo()
        employee = user_sudo.employee_id
        if employee:
            return employee.sudo()

        return self.env['hr.employee'].sudo().search([
            ('user_id', '=', user_sudo.id),
        ], limit=1)

    def _x_psm_0204_get_store_portal_pseudo_role(self):
        """Resolve pseudo-role for store portal flows from employee.job_id.name."""
        self.ensure_one()

        if self._is_public() or not self.has_group('base.group_portal'):
            return False

        employee = self._x_psm_0204_get_portal_employee()
        if not employee or not employee.job_id:
            return False

        normalized_job_name = ' '.join((employee.job_id.name or '').strip().lower().split())
        if normalized_job_name == 'department manager 1':
            return 'dm1'
        if normalized_job_name == 'department manager 2':
            return 'dm2'

        return False

    def _x_psm_0204_is_store_portal_dm1(self):
        """Store portal flow in 0204 is currently enabled only for DM1."""
        self.ensure_one()
        return self._x_psm_0204_get_store_portal_pseudo_role() == 'dm1'
