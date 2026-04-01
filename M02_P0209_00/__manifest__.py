{
    'name': 'M02_P0209_00 - L&D & People Development',
    'version': '19.0.1.0.2',
    'category': 'Human Resources/Training',
    'summary': 'McDonald\'s OPS Personnel Capability Development Process',
    'description': """
        M02_P0209_00 - Quy Trình Phát Triển Năng Lực Nhân Viên OPS
        ========================================================

        Process Flow:
        1. L&D: Create SOC (Station Observation Checklist)
        2. L&D: Plan Training Schedule
        3. L&D: Define Skill Categories
        4. L&D: Create Online Lessons
        5. System: Suggest Training Needs
        6. Crew: E-Schedule & Online Learning
        7. Trainer: Training & Evaluation (SOC)
        8. RGM: Final Review & Promotion

        Key Features:
        - SOC Template Management
        - Training Schedule & E-Learning
        - Skill Tracking & Capacity Planning
    """,
    'assets': {
        'web.assets_frontend': [
            'M02_P0209_00/static/src/js/soc_evaluation.js',
            'M02_P0209_00/static/src/js/soc_trainer_evaluation.js',
            'M02_P0209_00/static/src/js/soc_course_fullscreen_player.js',
        ],
    },
    'author': 'PSM',
    'depends': ['base', 'mail', 'website_slides', 'hr_skills', 'planning', 'portal', 'point_of_sale', 'M02_P0206_00', 'portal_custom'],
    'data': [
        'security/security_rules.xml',
        'security/ir.model.access.csv',
        'data/ir_sequence_data.xml',
        'wizard/soc_import_wizard_views.xml',
        'wizard/soc_select_wizard_views.xml',
        'wizard/soc_server_actions.xml',
        'views/soc_version_views.xml',
        'views/elearning_views.xml',
        'views/soc_web_templates.xml',
        'views/soc_trainer_templates.xml',
        'views/secure_content_templates.xml',
        'views/potential_list_views.xml',
        'views/portal_templates.xml',
        'views/hr_job_views.xml',
        'views/hr_employee_views.xml',
        'views/soc_evaluation_views.xml',
        'views/planning_slot_views.xml',
        'views/soc_sidebar_templates.xml',
        'views/menu_views.xml',
        'data/soc_server_actions.xml',
        'data/mail_templates.xml',
    ],
    'demo': [
    ],
    'application': True,
    'installable': True,
    'auto_install': False,
}
