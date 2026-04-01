# -*- coding: utf-8 -*-
import logging
from datetime import datetime, timedelta

_logger = logging.getLogger(__name__)

def load_demo_data(env):
    """Manually load demo data for SC_0402"""
    
    _logger.info("=" * 60)
    _logger.info("🚀 Loading SC_0402 Demo Data...")
    _logger.info("=" * 60)
    
    # 1. Create supplier
    supplier = env['res.partner'].create({
        'name': 'Golden State Foods Vietnam (Test)',
        'ref': 'GSF-VN-TEST-001',
        'is_company': True,
        'supplier_rank': 1,
        'email': 'contact@gsf-test.vn',
        'phone': '+84 28 1234 5678',
        'street': '123 Nguyen Hue, District 1',
        'city': 'Ho Chi Minh City',
    })
    _logger.info(f"✅ Created supplier: {supplier.name}")
    
    # 2. Create component products
    ProductProduct = env['product.product']
    
    chicken = ProductProduct.create({
        'name': 'Samyang Spicy Chicken Patty (Test)',
        'default_code': 'TEST-CHICK-SAMYANG-001',
        'type': 'product',
        'standard_price': 35000,
        'list_price': 50000,
    })
    chicken.product_tmpl_id.write({
        'x_gri': 'GRI-CHICK-001',
        'x_raw_item_desc': 'Samyang Spicy Breaded Chicken Breast',
    })
    
    bun = ProductProduct.create({
        'name': 'Premium Sesame Seed Bun (Test)',
        'default_code': 'TEST-BUN-002',
        'type': 'product',
        'standard_price': 5000,
    })
    bun.product_tmpl_id.write({
        'x_gri': 'GRI-BUN-002',
        'x_raw_item_desc': '4-inch Sesame Bun',
    })
    
    lettuce = ProductProduct.create({
        'name': 'Fresh Iceberg Lettuce (Test)',
        'default_code': 'TEST-VEG-003',
        'type': 'product',
        'uom_id': env.ref('uom.product_uom_kgm').id,
        'standard_price': 15000,
    })
    lettuce.product_tmpl_id.write({
        'x_gri': 'GRI-VEG-003',
        'x_raw_item_desc': 'Shredded Iceberg Lettuce',
    })
    
    sauce = ProductProduct.create({
        'name': 'Samyang Special Sauce (Test)',
        'default_code': 'TEST-SAUCE-004',
        'type': 'product',
        'uom_id': env.ref('uom.product_uom_litre').id,
        'standard_price': 8000,
    })
    sauce.product_tmpl_id.write({
        'x_gri': 'GRI-SAUCE-004',
        'x_raw_item_desc': 'Hot Chicken Sauce',
    })
    
    _logger.info(f"✅ Created 4 component products")
    
    # 3. Create supplier evaluation
    evaluation = env['supplier.evaluation'].create({
        'partner_id': supplier.id,
        'product_tmpl_id': chicken.product_tmpl_id.id,
        'evaluation_type': 'new_product',
        'is_new_supplier': False,
        'state': 'draft',
        'note': 'Evaluation for TinyTAN Samyang Burger campaign - GSF as chicken supplier',
    })
    _logger.info(f"✅ Created evaluation: {evaluation.name}")
    
    # 4. Add certificates
    env['supplier.certificate'].create({
        'evaluation_id': evaluation.id,
        'partner_id': supplier.id,
        'name': 'HACCP Certificate',
        'certificate_type': 'haccp',
        'issue_date': (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d'),
        'expiry_date': (datetime.now() + timedelta(days=1095)).strftime('%Y-%m-%d'),
        'issued_by': 'Vietnam Food Safety Authority',
        'certificate_number': 'HACCP-VN-2025-TEST-001',
    })
    
    env['supplier.certificate'].create({
        'evaluation_id': evaluation.id,
        'partner_id': supplier.id,
        'name': 'ISO 22000:2018',
        'certificate_type': 'iso',
        'issue_date': (datetime.now() - timedelta(days=180)).strftime('%Y-%m-%d'),
        'expiry_date': (datetime.now() + timedelta(days=1095)).strftime('%Y-%m-%d'),
        'issued_by': 'Bureau Veritas',
        'certificate_number': 'ISO-22000-VN-TEST-456',
    })
    _logger.info(f"✅ Created 2 certificates")
    
    # 5. Add capacity
    capacity = env['supplier.capacity'].create({
        'evaluation_id': evaluation.id,
        'partner_id': supplier.id,
        'monthly_capacity': 500000,
        'current_utilization': 70.0,
        'quality_rating': 'a',
        'financial_stability': 'stable',
        'production_lead_time': 7,
        'notes': 'GSF có đủ năng lực sản xuất 50,000 units cho TinyTAN campaign',
    })
    evaluation.capacity_id = capacity.id
    _logger.info(f"✅ Created capacity assessment")
    
    # 6. Add audit
    admin_user = env.ref('base.user_admin')
    env['supplier.audit'].create({
        'evaluation_id': evaluation.id,
        'partner_id': supplier.id,
        'audit_type': 'factory_visit',
        'audit_date': (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d'),
        'auditor_id': admin_user.id,
        'overall_score': 92,
        'result': 'pass',
        'findings': '<p><strong>Factory Visit Summary:</strong></p><ul><li>Excellent production facility with modern equipment</li><li>Good hygiene practices observed</li><li>Minor improvement needed: Cold storage monitoring system</li><li>Staff well-trained in food safety</li></ul>',
    })
    _logger.info(f"✅ Created factory audit")
    
    # 7. Add lab test
    env['lab.test'].create({
        'evaluation_id': evaluation.id,
        'product_tmpl_id': chicken.product_tmpl_id.id,
        'test_date': (datetime.now() - timedelta(days=5)).strftime('%Y-%m-%d'),
        'test_type': 'microbiological',
        'lab_name': 'SGS Vietnam',
        'result': 'pass',
        'test_report': '<p><strong>Microbiological Test Results:</strong></p><table border="1"><tr><th>Parameter</th><th>Result</th><th>Limit</th><th>Status</th></tr><tr><td>E.coli</td><td>&lt;10 CFU/g</td><td>&lt;100 CFU/g</td><td>✓ Pass</td></tr><tr><td>Salmonella</td><td>Not detected</td><td>Not detected</td><td>✓ Pass</td></tr><tr><td>Total Plate Count</td><td>1.2x10³</td><td>&lt;10⁵</td><td>✓ Pass</td></tr></table>',
    })
    _logger.info(f"✅ Created lab test")
    
    # 8. Add sensory test
    env['sensory.test'].create({
        'evaluation_id': evaluation.id,
        'product_tmpl_id': chicken.product_tmpl_id.id,
        'test_date': (datetime.now() - timedelta(days=3)).strftime('%Y-%m-%d'),
        'tester_ids': [(6, 0, [admin_user.partner_id.id])],
        'appearance_score': 9,
        'taste_score': 9,
        'texture_score': 8,
        'aroma_score': 9,
        'overall_score': 8.75,
        'result': 'pass',
        'notes': 'Excellent spicy flavor matching Samyang brand. Crispy texture maintained after preparation. Aroma appealing. Compared with reference sample - meets all criteria.',
    })
    _logger.info(f"✅ Created sensory test")
    
    # 9. Create PIF
    pif = env['product.pif'].create({
        'program_name': 'TinyTAN Limited Time Campaign',
        'launch_date': (datetime.now() + timedelta(days=45)).strftime('%Y-%m-%d'),
        'forecast_volume': 50000,
        'initiator_id': admin_user.id,
        'state': 'draft',
        'notes': '<p><strong>Campaign Background:</strong></p><ul><li>Partnership with TinyTAN brand (BTS characters)</li><li>Target: Young adults 18-30 years old</li><li>Duration: 6 weeks limited time</li><li>Spicy chicken trend in Vietnam market</li></ul>',
    })
    _logger.info(f"✅ Created PIF: {pif.name}")
    
    # 10. Create PIF line
    pif_line = env['product.pif.line'].create({
        'pif_id': pif.id,
        'sequence': 1,
        'level1_category': 'Regular',
        'level2_category': 'Limited Time',
        'level3_category': 'TinyTAN Collection',
        'level4_category': 'Chicken Series',
        'level5_category': 'Menu Item',
        'level6_category': '1pc Chicken',
        'level7_category': 'Samyang Spicy Chicken',
        'menu_item_code': 'PLU-SAMYANG-TEST-001',
        'product_name_en': 'TinyTAN Samyang Chicken Burger',
        'product_name_vn': 'Burger Gà Samyang TinyTAN',
        'product_type': 'main_item',
        'price_instore': 75000,
        'cost_instore': 45000,
        'price_delivery': 80000,
        'cost_delivery': 47000,
        'price_airport': 90000,
        'cost_airport': 50000,
    })
    _logger.info(f"✅ Created PIF line: {pif_line.product_name_en}")
    
    # 11. Add components
    env['product.pif.parent.component'].create({
        'pif_line_id': pif_line.id,
        'sequence': 1,
        'name': 'Samyang Chicken Patty',
        'product_id': chicken.id,
        'quantity': 1.0,
        'uom_id': env.ref('uom.product_uom_unit').id,
        'conversion_rate': 1.0,
        'unit_price': 35000,
        'case_pack': 50,
        'lead_time_days': 7,
    })
    
    env['product.pif.parent.component'].create({
        'pif_line_id': pif_line.id,
        'sequence': 2,
        'name': 'Sesame Bun',
        'product_id': bun.id,
        'quantity': 1.0,
        'uom_id': env.ref('uom.product_uom_unit').id,
        'conversion_rate': 1.0,
        'unit_price': 5000,
        'case_pack': 100,
        'lead_time_days': 3,
    })
    
    env['product.pif.parent.component'].create({
        'pif_line_id': pif_line.id,
        'sequence': 3,
        'name': 'Fresh Lettuce',
        'product_id': lettuce.id,
        'quantity': 0.02,
        'uom_id': env.ref('uom.product_uom_kgm').id,
        'conversion_rate': 50.0,
        'unit_price': 300,
        'case_pack': 10,
        'lead_time_days': 2,
    })
    
    env['product.pif.parent.component'].create({
        'pif_line_id': pif_line.id,
        'sequence': 4,
        'name': 'Samyang Special Sauce',
        'product_id': sauce.id,
        'quantity': 0.025,
        'uom_id': env.ref('uom.product_uom_litre').id,
        'conversion_rate': 40.0,
        'unit_price': 200,
        'case_pack': 20,
        'lead_time_days': 5,
    })
    
    _logger.info(f"✅ Created 4 parent components")
    
    _logger.info("=" * 60)
    _logger.info("✅✅✅ DEMO DATA LOADED SUCCESSFULLY ✅✅✅")
    _logger.info("=" * 60)
    _logger.info(f"📦 Supplier: {supplier.name} (ID: {supplier.id})")
    _logger.info(f"📋 Evaluation: {evaluation.name} (ID: {evaluation.id})")
    _logger.info(f"🎯 PIF: {pif.name} (ID: {pif.id})")
    _logger.info(f"🧪 Components: {len([chicken, bun, lettuce, sauce])} products")
    _logger.info("=" * 60)
    _logger.info("📍 To test:")
    _logger.info(f"   1. Open: SC_0402 > Supplier Evaluation > {evaluation.name}")
    _logger.info(f"   2. Open: Manufacturing > PIFs > {pif.name}")
    _logger.info("=" * 60)
    
    return {
        'supplier': supplier,
        'evaluation': evaluation,
        'pif': pif,
        'products': [chicken, bun, lettuce, sauce],
    }
