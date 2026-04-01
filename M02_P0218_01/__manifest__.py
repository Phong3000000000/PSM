{
    'name': 'M02_P0218_01',
    'version': '1.0',
    'category': 'Human Resources',
    'summary': 'Department Quận 1 with employees',
    'description': """
        Module for Department Quận 1 with:
        - 1 RGM (Regional General Manager)
        - 2 Managers
        - 3 Staff members
    """,
    'depends': ['hr', 'hr_appraisal', 'hr_appraisal_survey', 'survey', 'approvals', 'portal_custom', 'M02_P0200_00'],
    'data': [
        'security/ir.model.access.csv',
        # 'data/hr_department_data.xml',
        # 'data/hr_employee_data.xml',
        'data/hr_appraisal_note_data.xml',
        'data/salary_increase_config_data.xml',
        'data/approval_category_data.xml',
        'data/mail_template_salary_increase.xml',
        'data/survey_360_feedback.xml',
        'wizard/create_performance_appraisal_wizard_views.xml',
        'wizard/salary_increase_plan_wizard_views.xml',
        'views/salary_increase_config_views.xml',
        'views/hr_appraisal_note_views.xml',
        'views/hr_appraisal_views.xml',
        'views/hr_appraisal_goal_views.xml',
        'views/approval_request_views.xml',
        'report/salary_increase_report_views.xml',
        'views/portal_goals_templates.xml',
        'views/hr_employee_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
