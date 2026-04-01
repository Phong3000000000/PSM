{
    'name': 'Dev Admin Tools',
    'version': '19.0.1.0.0',
    'category': 'Administration',
    'summary': 'Auto-extends database expiration and patches subscription check on install',
    'author': 'Local Dev',
    'depends': ['base', 'web_enterprise'],
    'assets': {
        'web.assets_backend': [
            'dev_admin_tools/static/src/js/subscription_patch.js',
        ],
    },
    'post_init_hook': 'post_init_hook',
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
