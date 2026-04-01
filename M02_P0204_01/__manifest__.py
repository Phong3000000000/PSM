# -*- coding: utf-8 -*-
{
    'name': 'Quy Trình Tuyển Dụng Khối Cửa Hàng',
    'version': '1.0',
    'category': 'Human Resources/Recruitment',
    'summary': 'Quản lý lịch phỏng vấn cửa hàng, gửi email mời PV kèm khảo sát',
    'description': """
        Quy Trình Tuyển Dụng Khối Cửa Hàng (M02_P0204_01)
        ===================================
        
        Tính năng:
        - Store Manager đặt lịch phỏng vấn (3 ngày/tuần) cho từng cửa hàng
        - HR gửi email mời ứng viên kèm 3 ngày có thể phỏng vấn
        - Tích hợp Survey để ứng viên điền thông tin trước khi phỏng vấn
        - Kanban view hiển thị lịch các cửa hàng dạng card
        
        Menu mới: Recruitment > Lịch phỏng vấn dự kiến
    """,
    'author': 'Your Company',
    'depends': [
        'hr_recruitment',  
        'survey',          
        'hr',              
        'mail',            
        'website_hr_recruitment',
        'hr_recruitment_survey',  
        'website_blog',
        'hr_payroll',
        'M04_P0400_00',
    ],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'data/store_stages.xml',
        'data/office_stages.xml',
        'data/cleanup_actions.xml',
        'data/survey_template.xml',
        'data/email_template.xml',
        'views/interview_schedule_views.xml',
        'views/hr_job_views.xml',
        'views/hr_applicant_views.xml',
        'views/recruitment_type_menus.xml',
        'views/menus.xml',
        'views/website_hr_recruitment_templates.xml',
        'views/recruitment_session_views.xml',
        'views/referral_config_views.xml',
        'views/referral_program_views.xml',
    ],
    'demo': [],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
    'post_init_hook': 'post_init_hook',
}
