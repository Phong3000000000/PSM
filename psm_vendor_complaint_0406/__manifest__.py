# -*- coding: utf-8 -*-
{
    'name': 'Vendor Complaint',
    'version': '1.0',
    'category': 'Inventory/Inventory',
    'summary': 'Handle excess, shortage, and defective goods complaints from receiving process',
    'description': """
Vendor Complaint
====================
Quy trình xử lý hàng thiếu, thừa, kém chất lượng phát sinh từ quy trình nhận hàng.

Intercept stock picking validation to handle vendor complaints for:
- TH1: Excess goods (Hàng thừa) - Auto accept
- TH2: Shortage (Hàng thiếu) - FSC review → Backorder in 48h
- TH3: Defective goods - Province QIP (Hàng lỗi Tỉnh) - QA review → FSC review
- TH4: Defective goods - Metro QIP HCM/HN (Hàng lỗi Metro) - Auto reject

This module depends on psm_purchase_receiving for QIP status field.
    """,
    'depends': ['stock', 'purchase', 'mail', 'psm_purchase_receiving_0405'],
    'data': [
        'security/security_groups.xml',
        'security/ir.model.access.csv',
        'data/sequence.xml',
        'data/metro_config.xml',
        'views/vendor_complaint_views.xml',
        'views/stock_picking_views.xml',
        'wizard/vendor_complaint_wizard_views.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
    'license': 'LGPL-3',
}
