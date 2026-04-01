# -*- coding: utf-8 -*-
{
    'name': 'M02_P0206_00',
    'version': '1.0',
    'category': 'Human Resources',
    'summary': 'Hệ thống quản lý lực lượng lao động RGM (Merged Module)',
    'description': """
        Hệ thống tích hợp Workforce RGM:
        - Core Engine: Forecasting, Smart Scheduling, Planning Periods.
        - Kiosk Mode: Đánh giá hiệu suất và xác nhận giờ công.
        - Portal: Đăng ký ca làm việc (Open Shifts).
        - Reports: Báo cáo lương Adecco.
    """,
    'author': 'RGM Vietnam',
    'depends': [
        'planning', 
        'hr', 
        'hr_attendance', 
        'hr_holidays',  # For leave-planning sync
        'mail', 
        'website', 
        'portal', 
        'portal_custom',
        'product',
        
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/master_roles.xml',
        'data/test_slots.xml',
        'data/master_data.xml',
        'views/workforce_forecast_views.xml',
        'views/planning_period_views.xml',
        'views/planning_slot_views.xml',
        'views/shift_template_views.xml',
        'views/workforce_station_views.xml',
        'views/workforce_config_views.xml',
        'views/hr_employee_views.xml',
        'wizard/smart_scheduler_wizard_views.xml',
        'views/menu.xml',
        'views/attendance_rating_views.xml',
        'views/portal_templates.xml',
        'wizard/adecco_report_wizard_views.xml',
        'report/adecco_report_templates.xml',
        'report/adecco_report.xml',
        'views/report_menu.xml',
        'views/month_closing_views.xml',
        'security/security.xml',
        'data/cron_jobs.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'M02_P0206_00/static/src/js/kiosk_rating.js',
            'M02_P0206_00/static/src/xml/kiosk_rating.xml',
        ],
        'web.assets_frontend': [
            'M02_P0206_00/static/src/js/shift_register.js',
        ],
    },
    'installable': True,
    'application': True,
    'license': 'OEEL-1',
}

