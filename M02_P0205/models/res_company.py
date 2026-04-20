# -*- coding: utf-8 -*-
import re

from odoo import api, fields, models


GROUP_XMLID_MAPPINGS = {
    "M02_P0205.group_hr_validator": "M02_P0205.group_gdh_rst_office_recruitment_mgr",
    "M02_P0205.group_ceo_recruitment": "M02_P0205.group_gdh_rst_office_recruitment_mgr_ceo",
    "M02_P0205.group_bod_recruitment": "M02_P0205.group_gdh_rst_office_recruitment_mgr_bod",
    "M02_P0205.group_abu_recruitment": "M02_P0205.group_gdh_rst_office_recruitment_mgr_abu",
    "M02_P0205.group_gdh_rst_hr_recruitment_m": "M02_P0205.group_gdh_rst_office_recruitment_mgr",
    "M02_P0205.group_gdh_rst_all_ceo_recruitment_m": "M02_P0205.group_gdh_rst_office_recruitment_mgr_ceo",
    "M02_P0205.group_gdh_rst_all_bod_recruitment_m": "M02_P0205.group_gdh_rst_office_recruitment_mgr_bod",
    "M02_P0205.group_gdh_rst_all_abu_recruitment_m": "M02_P0205.group_gdh_rst_office_recruitment_mgr_abu",
}


class ResCompany(models.Model):
    _inherit = "res.company"

    x_psm_0205_ceo_id = fields.Many2one(
        "hr.employee",
        string="CEO",
        help="Giam doc dieu hanh chiu trach nhiem cua cong ty.",
    )
    x_psm_0205_office_block_codes = fields.Char(
        string="Ma block van phong",
        default="RST",
        help="Danh sach ma block duoc xem la khoi van phong. Co the nhap cach nhau boi dau phay, dau cham phay hoac xuong dong.",
    )
    x_psm_0205_office_block_names = fields.Char(
        string="Ten block van phong",
        default="HEAD OFFICE",
        help="Danh sach ten block duoc xem la khoi van phong. Co the nhap cach nhau boi dau phay, dau cham phay hoac xuong dong.",
    )
    x_psm_0205_default_recruitment_email_from = fields.Char(
        string="Email gui recruitment mac dinh",
        help="Email nguoi gui mac dinh cho cac thu moi va email nghiep vu cua tuyen dung khoi van phong.",
    )
    x_psm_0205_default_recruitment_noreply_email = fields.Char(
        string="Email no-reply recruitment mac dinh",
        help="Email fallback khi khong co email nguoi tao lich hoac email tu user phu trach.",
    )
    x_psm_0205_default_interview_location = fields.Char(
        string="Dia diem phong van mac dinh",
        default="Van phong cong ty",
        help="Dia diem duoc su dung khi lich phong van chua co location cu the.",
    )
    x_psm_0205_default_recruitment_blog_id = fields.Many2one(
        "blog.blog",
        string="Blog tuyen dung mac dinh",
        help="Blog duoc uu tien dung khi dang Job Position len portal.",
    )
    x_psm_0205_include_department_manager_interviewer = fields.Boolean(
        string="Them truong bo phan vao interviewer mac dinh",
        default=True,
        help="Neu bat, manager cua phong ban se duoc them vao danh sach interviewer mac dinh cua office job.",
    )
    x_psm_0205_include_ceo_interviewer = fields.Boolean(
        string="Them CEO vao interviewer mac dinh",
        default=True,
        help="Neu bat, CEO cong ty se duoc them vao danh sach interviewer mac dinh cua office job.",
    )
    x_psm_0205_default_bod_interviewer_group_id = fields.Many2one(
        "res.groups",
        string="Group BOD interviewer mac dinh",
        default=lambda self: self.env.ref(
            "M02_P0205.group_gdh_rst_office_recruitment_mgr_bod",
            raise_if_not_found=False,
        ),
        help="Group duoc dung de lay interviewer mac dinh cho vai tro BOD.",
    )
    x_psm_0205_default_abu_interviewer_group_id = fields.Many2one(
        "res.groups",
        string="Group ABU interviewer mac dinh",
        default=lambda self: self.env.ref(
            "M02_P0205.group_gdh_rst_office_recruitment_mgr_abu",
            raise_if_not_found=False,
        ),
        help="Group duoc dung de lay interviewer mac dinh cho vai tro ABU.",
    )
    x_psm_0205_hr_approval_group_id = fields.Many2one(
        "res.groups",
        string="Group duyet HR mac dinh",
        default=lambda self: self.env.ref(
            "M02_P0200.GDH_RST_HR_RECRUITMENT_M",
            raise_if_not_found=False,
        ),
        help="Group fallback de tim user HR approver khi khong co user phu trach cu the.",
    )
    x_psm_0205_ceo_approval_group_id = fields.Many2one(
        "res.groups",
        string="Group duyet CEO mac dinh",
        default=lambda self: self.env.ref(
            "M02_P0205.group_gdh_rst_office_recruitment_mgr_ceo",
            raise_if_not_found=False,
        ),
        help="Group fallback de tim user CEO approver khi khong co CEO cong ty hoac user cu the.",
    )
    x_psm_0205_enable_ceo_approval = fields.Boolean(
        string="Bat buoc buoc duyet CEO",
        default=True,
        help="Neu tat, luong approval office se bo qua buoc CEO va ket thuc sau khi HR duyet.",
    )
    x_psm_0205_hr_approval_sequence = fields.Integer(
        string="Sequence duyet HR",
        default=10,
        help="Thu tu sequence cua approver HR trong approval flow office.",
    )
    x_psm_0205_ceo_approval_sequence = fields.Integer(
        string="Sequence duyet CEO",
        default=20,
        help="Thu tu sequence cua approver CEO trong approval flow office.",
    )

    def _x_psm_0205_split_config_values(self, raw_value, uppercase=False):
        self.ensure_one()
        if not raw_value:
            return set()
        values = set()
        for item in re.split(r"[,;\r\n]+", raw_value):
            cleaned = (item or "").strip()
            if not cleaned:
                continue
            values.add(cleaned.upper() if uppercase else cleaned)
        return values

    def _x_psm_0205_get_office_block_codes(self):
        self.ensure_one()
        return self._x_psm_0205_split_config_values(
            self.x_psm_0205_office_block_codes,
            uppercase=True,
        )

    def _x_psm_0205_get_office_block_names(self):
        self.ensure_one()
        return self._x_psm_0205_split_config_values(
            self.x_psm_0205_office_block_names,
            uppercase=True,
        )

    def _x_psm_0205_get_bod_interviewer_group(self):
        self.ensure_one()
        return (
            self.x_psm_0205_default_bod_interviewer_group_id
            or self.env.ref(
                "M02_P0205.group_gdh_rst_office_recruitment_mgr_bod",
                raise_if_not_found=False,
            )
        )

    def _x_psm_0205_get_abu_interviewer_group(self):
        self.ensure_one()
        return (
            self.x_psm_0205_default_abu_interviewer_group_id
            or self.env.ref(
                "M02_P0205.group_gdh_rst_office_recruitment_mgr_abu",
                raise_if_not_found=False,
            )
        )

    def _x_psm_0205_get_hr_approval_group(self):
        self.ensure_one()
        return (
            self.x_psm_0205_hr_approval_group_id
            or self.env.ref(
                "M02_P0200.GDH_RST_HR_RECRUITMENT_M",
                raise_if_not_found=False,
            )
        )

    def _x_psm_0205_get_ceo_approval_group(self):
        self.ensure_one()
        return (
            self.x_psm_0205_ceo_approval_group_id
            or self.env.ref(
                "M02_P0205.group_gdh_rst_office_recruitment_mgr_ceo",
                raise_if_not_found=False,
            )
        )

    def _x_psm_0205_get_hr_approval_sequence(self):
        self.ensure_one()
        return self.x_psm_0205_hr_approval_sequence or 10

    def _x_psm_0205_get_ceo_approval_sequence(self):
        self.ensure_one()
        return self.x_psm_0205_ceo_approval_sequence or 20

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
