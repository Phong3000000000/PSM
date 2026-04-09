# -*- coding: utf-8 -*-
{
    "name": "M02_P0205 - Quy Trinh Tuyen Dung Khoi Van Phong",
    "version": "19.0.20250918",
    "category": "Human Resources/Recruitment",
    "summary": "Quy trình tuyển dụng cho khối văn phòng",
    "description": """
        M02_P0205_00 - Quy trình tuyển dụng khối văn phòng
        ================================================

        Module mở rộng quy trình tuyển dụng cho khối văn phòng.

        Chức năng chính:
        - Quản lý recruitment request và recruitment plan
        - Vận hành pipeline ứng viên theo nhiều vòng phỏng vấn
        - Hỗ trợ interview scheduling, evaluation và survey
        - Tự động hóa email, activity và thông báo nghiệp vụ
        - Tích hợp với onboarding và offboarding liên quan

        Phạm vi quy trình:
        1. Luồng duyệt yêu cầu tuyển dụng: Manager -> HR -> CEO
        2. Luồng phỏng vấn nhiều vòng với nhiều vai trò tham gia
        3. Offer, hired và các bước chuyển tiếp sau tuyển dụng
    """,
    "author": "PSM",
    "depends": [
        "calendar",
        "hr_recruitment",
        "hr_skills",
        "hr_recruitment_skills",
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
        "security/recruitment_group_bridge.xml",
        "data/group_migration_data.xml",
        "security/recruitment_security.xml",
        "security/ir.model.access.csv",
        "data/ir_sequence_data.xml",
        "data/force_sequence.xml",
        "data/office_stages.xml",
        "data/approval_category_data.xml",
        "data/job_level_interview_round_data.xml",
        "data/job_level_fix_data.xml",
        "data/view_cleanup.xml",
        "data/mail_template_data.xml",
        "data/mail_template_override.xml",
        "data/survey_digital_marketing.xml",
        "data/ir_cron_data.xml",
        "data/survey_barista.xml",
        # "data/survey_odoo_dev.xml",
        "data/survey_refuse_data.xml",
        "data/hr_employee_sample_data.xml",
        "data/survey_marketing_specialist.xml",
        "data/survey_marketing_consultant.xml",
        "data/survey_digital_marketing_executive.xml",
        "data/survey_accountant.xml",
        "views/recruitment_plan_views.xml",
        "views/recruitment_request_views.xml",
        "views/recruitment_request_approver_views.xml",
        "views/approval_request_views.xml",
        "views/hr_applicant_views.xml",
        "views/calendar_event_views.xml",
        "views/hr_job_level_views.xml",
        "views/hr_job_views.xml",
        "views/survey_views.xml",
        "views/res_company_views.xml",
        "views/menus.xml",
        "views/portal_templates.xml",
        "views/job_portal_templates.xml",
        "views/website_hr_recruitment_templates.xml",
    ],
    "assets": {
        "web.assets_frontend": [
            "M02_P0205_00/static/src/scss/office_apply_responsive.scss",
        ],
    },
    "post_init_hook": "post_init_hook",
    "installable": True,
    "application": False,
    "license": "LGPL-3",
}
