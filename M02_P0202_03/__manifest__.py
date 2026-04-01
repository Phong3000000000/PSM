{
    'name': 'Quy trình Giới thiệu Nhân sự',
    'version': '19.0.1.0.0',
    'category': 'Human Resources/Recruitment',
    'summary': 'Employee Referral Program',
    'description': """
        Quy trình Giới thiệu Nhân sự
    """,
    'author': 'PSM',
    'depends': [
        'base',
        'mail',
        'hr',
        'hr_recruitment',
        'hr_payroll',
        'website',
        'portal',
        'M02_P0204_01',
        'website_blog',
        'hr_referral',
        'approvals',
        'portal_custom',
        'M02_P0200_00',

    ],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'data/sequence_data.xml',
        'data/approval_category_data.xml',
        'data/email_templates.xml',
        'views/portal_templates.xml',


        'views/approval_request_views.xml',
        'wizard/referral_publish_wizard_views.xml',
        'views/referral_program_ext_views.xml',
        'views/referral_submission_views.xml',
        'views/recruitment_session_views.xml',
        'views/referral_config_override_views.xml',
        'views/hr_job_views.xml',
        'views/referral_report_views.xml',
        'views/menus.xml',
        'views/hr_applicant_views.xml',

    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
    'assets': {
        'web.assets_backend': [
            'M02_P0202_03/static/src/dashboard_patch.xml',
        ],
    },
}
