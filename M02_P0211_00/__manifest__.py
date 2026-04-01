{
    'name': 'Onboarding OPS',
    'version': '1.0',
    'summary': 'Allow candidates to upload personal documents via portal (psm_onboarding_ops_0211)',
    'category': 'Human Resources',
    'author': 'Your Company',
    'depends': ['base', 'portal', 'mail', 'hr_recruitment'],
    'data': [
        'security/ir.model.access.csv',
        'views/res_partner_views.xml',
        'views/hr_applicant_views.xml',
        'views/portal_templates.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}