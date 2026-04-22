# -*- coding: utf-8 -*-
{
    "name": "M02_P0204 - Quy Trinh Tuyen Dung Khoi Cua Hang",
    "version": "1.1",
    "category": "Human Resources/Recruitment",
    "summary": "Quản lý lịch phỏng vấn cửa hàng, gửi email mời PV kèm khảo sát",
    "description": """
        Quy Trình Tuyển Dụng Khối Cửa Hàng
        ===================================
        
        Tính năng:
        - Store Manager đặt lịch phỏng vấn (3 ngày/tuần) cho từng cửa hàng
        - HR gửi email mời ứng viên kèm 3 ngày có thể phỏng vấn
        - Tích hợp Survey để ứng viên điền thông tin trước khi phỏng vấn
        - Kanban view hiển thị lịch các cửa hàng dạng card
        
        Menu mới: Recruitment > Lịch phỏng vấn dự kiến
    """,
    "author": "PSM",
    "depends": [
        "hr_recruitment",  # Module tuyển dụng
        "calendar",  # Đồng bộ lịch phỏng vấn
        "survey",  # Module khảo sát
        "bus",  # Realtime update slot availability
        "hr",  # HR cơ bản
        "mail",  # Email
        "website_hr_recruitment",  # Website Recruitment
        "hr_recruitment_survey",  # Survey integration for jobs
        "M02_P0200",  # Master Data - Cấu hình Khối và Vị trí mặc định
    ],
    "data": [
        "security/security.xml",
        "security/ir.model.access.csv",
        "data/office_stages.xml",
        "data/cleanup_actions.xml",
        # Legacy one-time archive patch is intentionally not loaded:
        # - data/archive_default_stages.xml
        "data/ir_cron.xml",
        "data/survey_template.xml",
        "data/email_template.xml",
        "data/refuse_reason_data.xml",
        "views/interview_schedule_views.xml",
        "views/hr_job_views.xml",
        "views/survey_user_input_views.xml",
        "views/applicant_get_refuse_reason_views.xml",
        "views/website_job_apply_custom.xml",
        "views/hr_recruitment_stage_views.xml",
        "views/hr_applicant_views.xml",
        "views/menus.xml",
        "views/website_hr_recruitment_templates.xml",
        "views/portal_recruitment_templates.xml",
        "views/backend_oje_templates.xml",
        "views/backend_interview_templates.xml",
        "views/survey_question_views.xml",
        "views/survey_survey_views.xml",
        "views/survey_templates.xml",
        "views/hr_applicant_oje_evaluation_views.xml",
        "wizards/reject_applicant_wizard_views.xml",
        "views/create_job_templates_wizard_views.xml",
        "data/xmlid_aliases.xml",
    ],
    "demo": [],
    "assets": {
        "survey.survey_assets": [
            "M02_P0204/static/src/js/survey_slot_availability.js",
        ],
        "web.assets_backend": [
            "M02_P0204/static/src/js/survey_question_lock_backend.js",
            "M02_P0204/static/src/scss/hr_job_config.scss",
        ],
        "web.assets_frontend": [
            "M02_P0204/static/src/js/oje_backend_staff.js",
            "M02_P0204/static/src/js/interview_backend.js",
            "M02_P0204/static/src/js/portal_recruitment_history.js",
            "M02_P0204/static/src/scss/oje_backend.scss",
            "M02_P0204/static/src/scss/interview_backend.scss",
            "M02_P0204/static/src/scss/website_apply_responsive.scss",
            "M02_P0204/static/src/scss/portal_recruitment.scss",
        ],
    },
    "installable": True,
    "application": False,
    "auto_install": False,
    "license": "LGPL-3",
    "post_init_hook": "post_init_hook",
}
