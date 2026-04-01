# -*- coding: utf-8 -*-
{
    'name': 'PostgreSQL/MySQL Database Sync Module',
    'version': '19.0.2.1.0',
    'summary': 'Đồng bộ dữ liệu từ các CSDL ngoài vào Odoo',
    'description': """
Module Đồng Bộ Dữ Liệu Cơ Sở Dữ Liệu
=====================================
Module này cho phép đồng bộ dữ liệu từ các cơ sở dữ liệu ngoài (MySQL, MSSQL, MariaDB, PostgreSQL, Oracle) vào Odoo.

Tính năng chính:
----------------
* Kết nối đa dạng tới các loại CSDL
* Ánh xạ mô hình và trường dữ liệu
* Đồng bộ dữ liệu thủ công hoặc tự động
    """,
    'author': 'PSM Global <raico@psmerp.vn>',
    'website': "http://www.psmerp.vn",
    'support': "hung.nguyen@psmerp.vn",
    'category': 'Services',
    'depends': ['base', 'mail', 'web', 'queue_job'],
    'data': [
        'security/psm_db_sync_security.xml',
        'security/ir.model.access.csv',
        'data/psm_db_sync_data.xml',
        'views/psm_db_connection_views.xml',
        'views/psm_db_mapping_model_views.xml',
        'views/psm_db_mapping_field_views.xml',
        'views/psm_db_mapping_data_views.xml',
        'views/psm_db_sync_views.xml',
        'views/psm_db_sync_log_views.xml',
        'views/psm_db_sync_menu.xml',
        'wizards/psm_db_wizard_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'psm_db_sync/static/src/js/sync_data.js',
            'psm_db_sync/static/src/xml/sync_data.xml',
            'psm_db_sync/static/src/js/dashboard.js',
            'psm_db_sync/static/src/css/style.css',
            'psm_db_sync/static/src/xml/dashboard.xml',
        ],
    },
    'external_dependencies': {
        'python': ['sqlalchemy', 'pymysql', 'pyodbc'],
    },
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
