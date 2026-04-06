# -*- coding: utf-8 -*-
{
    "name": "Quy Trình Tuyển Dụng Khối Cửa Hàng",
    "version": "1.0",
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
    "author": "Your Company",
    "depends": [
        "hr_recruitment",  # Module tuyển dụng
        "calendar",  # Đồng bộ lịch phỏng vấn
        "survey",  # Module khảo sát
        "bus",  # Realtime update slot availability
        "hr",  # HR cơ bản
        "mail",  # Email
        "website_hr_recruitment",  # Website Recruitment
        "hr_recruitment_survey",  # Survey integration for jobs
        "M02_P0211_00",  # Onboarding OPS - Duyệt hồ sơ / Không duyệt buttons
        "M02_P0200_00",  # Master Data - Cấu hình Khối và Vị trí mặc định
    ],
    "data": [
        "security/security.xml",
        "security/ir.model.access.csv",
        "data/store_stages.xml",
        "data/office_stages.xml",
        "data/cleanup_actions.xml",
        "data/ir_cron.xml",
        "data/survey_template.xml",
        "data/email_template.xml",
        "data/refuse_reason_data.xml",
        "data/default_master_fields.xml",
        "data/oje_master_template_data.xml",
        "data/interview_master_template_data.xml",
        "views/interview_schedule_views.xml",
        "views/hr_job_views.xml",
        "views/hr_job_application_field_views.xml",
        "views/hr_job_survey_config_views.xml",
        "views/survey_user_input_views.xml",
        "views/applicant_get_refuse_reason_views.xml",
        "views/website_job_apply_custom.xml",
        "views/hr_recruitment_stage_views.xml",
        "views/hr_applicant_views.xml",
        "views/job_approval_request_views.xml",
        "views/recruitment_type_menus.xml",
        "views/recruitment_master_field_views.xml",
        "views/recruitment_oje_template_views.xml",
        "views/recruitment_interview_template_views.xml",
        "views/menus.xml",
        "views/website_hr_recruitment_templates.xml",
        "views/portal_recruitment_templates.xml",
        "views/backend_oje_templates.xml",
        "views/backend_interview_templates.xml",
        "views/survey_question_views.xml",
        "views/survey_survey_views.xml",
        "views/survey_templates.xml",
        "views/hr_applicant_oje_evaluation_views.xml",
        "wizards/reject_job_approval_wizard_views.xml",
        "wizards/reject_applicant_wizard_views.xml",
        "views/create_job_templates_wizard_views.xml",
    ],
    "demo": [],
    "assets": {
        "survey.survey_assets": [
            "M02_P0204_00/static/src/js/survey_slot_availability.js",
        ],
        "web.assets_frontend": [
            "M02_P0204_00/static/src/js/oje_backend_staff.js",
            "M02_P0204_00/static/src/js/interview_backend.js",
            "M02_P0204_00/static/src/scss/oje_backend.scss",
            "M02_P0204_00/static/src/scss/interview_backend.scss",
        ],
    },
    "installable": True,
    "application": False,
    "auto_install": False,
    "license": "LGPL-3",
    "post_init_hook": "post_init_hook",
}
