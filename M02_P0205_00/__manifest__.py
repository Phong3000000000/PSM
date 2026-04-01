# -*- coding: utf-8 -*-
{
    "name": "Quy Trình Tuyển Dụng Khối Văn Phòng",
    "version": "1.0",
    "category": "Human Resources/Recruitment",
    "summary": "Quản lý quy trình tuyển dụng 35 bước cho Khối Văn Phòng",
    "description": """
        Quy Trình Tuyển Dụng Khối Văn Phòng (M02_P0205_00)
        ==================================================
        Triển khai quy trình 35 bước:
        1. Yêu cầu tuyển dụng (Approval: Manager -> HR -> CEO)
        2. Quy trình phỏng vấn nhiều vòng (HR -> CEO -> BOD -> ABU)
        3. Tích hợp Onboarding & Offboarding
    """,
    "author": "PSM",
    "depends": [
        "calendar",
        "hr_recruitment",
        "hr",
        "mail",
        "survey",
        "approvals",
        "portal",
        "website_blog",
        "M02_P0200_00",
        "M02_P0204_00",  # Base recruitment module (store + shared logic)
        "M02_P0211_00",  # Onboarding
        "M02_P0213_00",  # Offboarding
        "portal_custom",
        "hr_recruitment_survey",  # For survey integration in recruitment
    ],
    "data": [
        "security/hr_validator_group.xml",
        "security/approval_groups.xml",
        "security/recruitment_security.xml",
        "security/ir.model.access.csv",
        "data/ir_sequence_data.xml",
        "data/force_sequence.xml",
        "data/office_stages.xml",
        "data/view_cleanup.xml",
        "data/mail_template_data.xml",
        "data/mail_template_override.xml",
        "data/survey_digital_marketing.xml",
        "data/ir_cron_data.xml",
        "data/survey_barista.xml",
        "data/survey_odoo_dev.xml",
        "data/survey_refuse_data.xml",
        "data/hr_employee_sample_data.xml",
        "data/survey_marketing_specialist.xml",
        "data/survey_marketing_consultant.xml",
        "data/survey_digital_marketing_executive.xml",
        "data/survey_accountant.xml",
        "views/recruitment_plan_views.xml",
        "views/recruitment_request_views.xml",
        "views/recruitment_request_approver_views.xml",
        "views/hr_applicant_views.xml",
        "views/calendar_event_views.xml",
        "views/hr_job_views.xml",
        "views/survey_views.xml",
        "views/res_company_views.xml",
        "views/menus.xml",
        "views/portal_templates.xml",
        "views/job_portal_templates.xml",
        "views/website_hr_recruitment_templates.xml",
    ],
    "post_init_hook": "post_init_hook",
    "installable": True,
    "application": True,
    "license": "LGPL-3",
}
