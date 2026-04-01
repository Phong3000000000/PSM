# -*- coding: utf-8 -*-
{
    'name': 'Purchase Receiving - Barcode Scanner',
    'version': '1.0',
    'category': 'Inventory/Purchase',
    'summary': 'Barcode scanner for purchase receiving process',
    'description': """
Purchase Receiving - Barcode Scanner
=========================================
This module combines barcode scanning functionality for the purchase receiving workflow:

1. **Scan Receipt Barcode**: Scan receipt barcode (e.g., WH/IN/00001) from Purchase Order 
   to quickly open the stock picking form.

2. **Scan Product Filter**: In stock picking, scan product barcode to filter operations 
   and quickly input quantity for specific products.

Features:
---------
- Auto-detect barcode scanner input
- Search and open stock picking by barcode
- Filter stock picking operations by product barcode
- Visual filtering (hide/show rows)
- Manual input fallback when no scanner available
    """,
    'depends': ['purchase', 'stock', 'barcodes'],
    'data': [
        'security/security_groups.xml',
        'security/ir.model.access.csv',
        'data/report_config.xml',
        'views/receiving_views.xml',
        'views/report_purchase_order.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'psm_purchase_receiving_0405/static/src/**/*',
        ],
    },
    'installable': True,
    'auto_install': False,
    'application': False,
    'license': 'LGPL-3',
}
