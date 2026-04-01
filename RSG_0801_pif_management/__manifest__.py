{
    'name': "RSG PIF Management (0801)",
    'summary': "RSG Department - Product Initiation Forms Management",
    'description': """
        RSG PIF Management Module.
        
        Base module for PIF Implementation workflow:
        - PIF Implementation workflow (RSG → IT → Master Data → Lab Test → Pilot)
        - Finished Good WRIN generation
        - Future: Other PIF types (Marketing, S&I, Digital, Supply Chain)
        
        This module is extended by SC_0402_supplier_management.
    """,
    'author': "MongTuyen",
    'version': '0.2',
    'category': 'Supply Chain/RSG',
    'depends': ['base', 'mail', 'product', 'mrp', 'approvals', 'hr'],
    'data': [
        'security/ir.model.access.csv',
        'data/pif_data.xml',
        'views/pif_views.xml',
    ],
    'installable': True,
    'application': False, 
}
