# -*- coding: utf-8 -*-
{
    'name': 'Food Safety Complaint Management',
    'version': '19.0.1.8.0',
    'category': 'Services/Helpdesk',
    'summary': 'Manage food safety complaints from stores and customers with quality control integration',
    'description': """
Food Safety Complaint Management
==================================
Complete solution for managing food safety complaints in multi-restaurant operations.

Key Features:
* Register complaints from stores and customers
* Track finished products and raw materials (NVL)
* Identify fault source (restaurant vs supplier)
* Integration with Helpdesk and Quality Control
* Multi-store support
* Product and lot traceability
* Automated workflows and notifications
    """,
    'author': 'Your Company',
    'website': 'https://www.yourcompany.com',
    'license': 'OEEL-1',
    'depends': [
        'base',
        'mail',
        'helpdesk',
        'quality',
        'stock',
        'product',
        'purchase',
    ],
    'data': [
        'security/food_safety_security.xml',
        'security/ir.model.access.csv',
        'views/food_safety_complaint_views.xml',
        'views/stock_picking_views.xml',
        'views/food_safety_menus.xml',
        'data/complaint_sequences.xml',
    ],
    'demo': [],
    'installable': True,
    'application': True,
    'auto_install': False,
}
