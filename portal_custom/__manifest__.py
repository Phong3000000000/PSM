{
    'name': 'Custom Portal',
    'version': '1.3',
    'summary': 'Custom Portal Module inheriting from standard Portal',
    'description': """
        This module extends the standard Odoo Portal with social media style layout.
        Includes Line Manager Approval App for portal users.
    """,
    'category': 'Website/Website',
    'author': 'Duong Van',
    'depends': ['portal', 'website_blog', 'website_slides', 'hr', 'approvals'],
    'data': [
        'security/ir.model.access.csv',
        'views/portal_templates.xml',
        'views/portal_management.xml',
        'data/blog_config.xml',
        'data/demo_data.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'portal_custom/static/src/css/global.css',
            'portal_custom/static/src/js/portal_approvals.js',
        ],
    },
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}

