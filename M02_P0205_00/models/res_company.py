# -*- coding: utf-8 -*-
from odoo import api, fields, models


GROUP_XMLID_MAPPINGS = {
    "M02_P0205_00.group_hr_validator": "M02_P0205_00.group_gdh_rst_office_recruitment_mgr",
    "M02_P0205_00.group_ceo_recruitment": "M02_P0205_00.group_gdh_rst_office_recruitment_mgr_ceo",
    "M02_P0205_00.group_bod_recruitment": "M02_P0205_00.group_gdh_rst_office_recruitment_mgr_bod",
    "M02_P0205_00.group_abu_recruitment": "M02_P0205_00.group_gdh_rst_office_recruitment_mgr_abu",
    "M02_P0205_00.group_gdh_rst_hr_recruitment_m": "M02_P0205_00.group_gdh_rst_office_recruitment_mgr",
    "M02_P0205_00.group_gdh_rst_all_ceo_recruitment_m": "M02_P0205_00.group_gdh_rst_office_recruitment_mgr_ceo",
    "M02_P0205_00.group_gdh_rst_all_bod_recruitment_m": "M02_P0205_00.group_gdh_rst_office_recruitment_mgr_bod",
    "M02_P0205_00.group_gdh_rst_all_abu_recruitment_m": "M02_P0205_00.group_gdh_rst_office_recruitment_mgr_abu",
}


class ResCompany(models.Model):
    _inherit = "res.company"

    x_psm_0205_ceo_id = fields.Many2one(
        "hr.employee",
        string="CEO",
        help="Giam doc dieu hanh chiu trach nhiem cua cong ty.",
    )

    @api.model
    def _migrate_0205_standard_groups(self):
        """Map users from legacy 0205 groups into standardized security groups."""
        for legacy_xmlid, standardized_xmlid in GROUP_XMLID_MAPPINGS.items():
            legacy_group = self.env.ref(legacy_xmlid, raise_if_not_found=False)
            standardized_group = self.env.ref(standardized_xmlid, raise_if_not_found=False)
            if not legacy_group or not standardized_group:
                continue
            missing_users = legacy_group.users - standardized_group.users
            if missing_users:
                standardized_group.write({"users": [(4, user.id) for user in missing_users]})
