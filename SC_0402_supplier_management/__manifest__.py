# -*- coding: utf-8 -*-
{
    'name': 'SC_0402 - Supplier Management & PIF',
    'version': '19.0.1.0.0',
    'category': 'Supply Chain/Purchasing',
    'sequence': 100,
    'summary': 'McDonald\'s Supplier Management, Product Information Form (PIF), and WRIN Management',
    'description': """
SC_0402 - Quản Lý Nhà Cung Cấp & Giá Bán
==========================================

Quy trình 22 bước:
- B1-B13: Phát triển sản phẩm mới & Đánh giá NCC
- B14-B16: PIF Management & Approval
- B17-B18: Contract Approval
- B19-B20: WRIN Creation & System Sync
- B21-B22: Supplier Optimization & Version Control

Features:
- Supplier Evaluation Workflow (QA Review, Audit, Lab Test)
- Multi-Vendor Proposal System
- WRIN Code Management (GRI + Supplier)
- BOM Integration với conversion rates
    """,
    'author': 'McDonald\'s Vietnam',
    'website': 'https://www.mcdonalds.com.vn',
    'license': 'LGPL-3',
    
    'depends': [
        'base',
        'product',
        'purchase',
        'purchase_requisition',
        'stock',
        'mrp',
        'mail',
        'quality_control',  # Required for supplier_audit.quality_check_ids
        'documents',        # Required for lab_test document management
        'approvals',        # Required for approval workflow
        'RSG_0801_pif_management',  # PIF Implementation workflow
    ],
    
    'data': [
        # Security
        'security/sc_0402_security.xml',
        'security/ir.model.access.csv',
        
        # Data
        'data/ir_sequence_data.xml',           # NEW: SE & GRI sequences
        'data/sequence_data.xml',
        'data/approval_category_data.xml',
        
        # Views - NEW: Refactored Models
        'views/res_partner_views.xml',          # Vendor draft/approval + Filter
        'views/product_template_views.xml',     # GRI code display
        
        # Views - Product & BOM Extensions
        'views/product_supplierinfo_views.xml',
        'views/mrp_bom_views.xml',              # Extended BOM views with PIF fields
        'views/mrp_bom_line_views.xml',         # Extended BOM line views
        
        # Menus (must be loaded before views that reference menu items)
        'views/menu_views.xml',
        
        # Views - Supplier Evaluation
        'views/supplier_evaluation_views.xml',
        'views/supplier_certificate_views.xml',
        'views/vendor_draft_views.xml',
    ],
    
    'demo': [],
    
    'application': True,
    'installable': True,
    'auto_install': False,
}
