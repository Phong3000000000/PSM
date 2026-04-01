{
    'name': 'Employee Rewards & Recognition (M02_P0216_00)',
    'version': '1.0',
    'summary': 'Post-shift evaluation, EOTM/EOTQ, Points & Vouchers',
    'description': """
        Module M02_P0216_00
        ===================
        - Shift Evaluations
        - Best Employee Recognition (EOTM/EOTQ)
        - Point Funds & History
        - Urbox Integration (Vouchers)
    """,
    'category': 'Human Resources',
    'author': 'PSM',
    'depends': ['hr', 'base', 'mail', 'portal', 'portal_custom'],
    'data': [
        'security/security.xml',
        'security/shift_reward_security.xml',
        'security/shift_point_fund_security.xml',
        'security/ir.model.access.csv',
        'data/hr_demo_data.xml',
        'data/branch_1_demo_data.xml',
        'data/hq_demo_data.xml',
        'data/shift_reward_mail_template.xml',
        'views/post_shift_views.xml',
        'views/hr_department_views.xml',
        'views/hr_employee_views.xml',
        'views/res_company_views.xml',
        'views/shift_evaluation_views.xml',
        'views/shift_reward_report.xml',
        'views/shift_reward_views.xml',
        'views/shift_point_fund_views.xml',
        'views/point_grant_views.xml',
        'views/voucher_views.xml',
        'views/urbox_partner_views.xml',
        'data/urbox_partner_demo_data.xml',
        'views/portal_templates.xml',
        'views/portal_voucher_templates.xml',
    ],
    'demo': [],
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}
