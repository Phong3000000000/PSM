# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase, tagged

@tagged('sc_0402')
class TestSC0402Flow(TransactionCase):

    def setUp(self):
        super(TestSC0402Flow, self).setUp()
        self.supplier = self.env['res.partner'].create({'name': 'Test Supplier', 'supplier_rank': 1})
        self.product_tmpl = self.env['product.template'].create({'name': 'Test Product'})
        
        # Create users
        self.menu_user = self.env['res.users'].create({
            'name': 'Menu User',
            'login': 'menu_user',
            'groups_id': [(4, self.env.ref('SC_0402_supplier_management.group_menu_user').id)],
        })
        self.sourcing_user = self.env['res.users'].create({
            'name': 'Sourcing User',
            'login': 'sourcing_user',
            'groups_id': [(4, self.env.ref('SC_0402_supplier_management.group_sourcing_user').id)],
        })
        self.manager_user = self.env['res.users'].create({
            'name': 'Manager User',
            'login': 'manager_user',
            'groups_id': [(4, self.env.ref('SC_0402_supplier_management.group_sc_0402_manager').id)],
        })

    def test_supplier_evaluation_flow(self):
        """ Test the Supplier Evaluation Workflow """
        evaluation = self.env['supplier.evaluation'].create({
            'partner_id': self.supplier.id,
            'product_tmpl_id': self.product_tmpl.id,
            'evaluation_type': 'new_product',
            'qa_user_id': self.manager_user.id,
        })
        
        # 1. Draft -> Sourcing
        evaluation.action_start_sourcing()
        self.assertEqual(evaluation.state, 'sourcing_search')
        
        # 2. Add certificate (required for completion)
        self.env['supplier.certificate'].create({
            'name': 'HACCP',
            'partner_id': self.supplier.id,
            'certificate_type': 'haccp',
            'evaluation_id': evaluation.id,
        })
        
        # 3. Sourcing -> Review
        evaluation.action_sourcing_complete()
        self.assertEqual(evaluation.state, 'sourcing_review')
        
        # 4. Submit to QA
        evaluation.action_submit_to_qa()
        self.assertEqual(evaluation.state, 'qa_document_review')
        
        # 5. QA Approve Documents
        evaluation.action_qa_document_approve()
        self.assertEqual(evaluation.state, 'qa_testing')
        
        # 6. QA Final Approve
        evaluation.action_qa_final_approve()
        self.assertEqual(evaluation.state, 'approved')
        self.assertTrue(evaluation.scorecard_id, "Scorecard should be auto-created")

    def test_pif_bom_flow(self):
        """ Test PIF/BOM Workflow with McDonald's fields """
        
        # 1. Create Evaluation first (approved)
        evaluation = self.env['supplier.evaluation'].create({
            'partner_id': self.supplier.id,
            'state': 'approved',
            'evaluation_type': 'new_product',
        })
        
        # 2. Create Component Product with GRI
        component = self.env['product.product'].create({
            'name': 'Raw Beef',
            'x_gri': 'GRI-001',
            'x_raw_item_desc': 'Frozen Beef Pattern',
            'standard_price': 50.0,
        })
        
        # Verify computed GRI
        self.assertEqual(component.x_gri_full, 'GRI-001-Frozen Beef Pattern')
        
        # 3. Create PIF BOM
        pif_bom = self.env['mrp.bom'].create({
            'product_tmpl_id': self.product_tmpl.id,
            'is_pif': True,
            'program_name': 'New Burger Campaign',
            'supplier_evaluation_id': evaluation.id,
        })
        
        # 4. Add Line with McDonald's fields
        bom_line = self.env['mrp.bom.line'].create({
            'bom_id': pif_bom.id,
            'product_id': component.id,
            'product_qty': 10,
            'x_conversion_rate': 12.0, # 1 unit = 12 sub-units
        })
        
        # Verify conversion rate logic
        self.assertEqual(bom_line.conversion_rate, 12.0)
        self.assertEqual(bom_line.gri, 'GRI-001')
        
        # 5. PIF Workflow
        pif_bom.action_submit_for_approval()
        self.assertEqual(pif_bom.pif_state, 'menu_review')
        
        pif_bom.action_approve_menu()
        self.assertEqual(pif_bom.pif_state, 'sourcing')
        
        pif_bom.action_approve_sourcing()
        self.assertEqual(pif_bom.pif_state, 'line_manager')
        
        pif_bom.with_user(self.manager_user).action_approve_line_manager()
        self.assertEqual(pif_bom.pif_state, 'ceo')
        
        pif_bom.with_user(self.manager_user).action_approve_ceo()
        self.assertEqual(pif_bom.pif_state, 'approved')
        
        # 6. Verify WRIN Creation Trigger
        self.assertTrue(pif_bom.wrin_created)
        
        # Check Supplier Info created
        supplier_info = self.env['product.supplierinfo'].search([
            ('product_id', '=', component.id),
            ('partner_id', '=', self.supplier.id)
        ])
        self.assertTrue(supplier_info)
        # Check WRIN format (GRI-Ref)
        expected_wrin = 'GRI-001' # No ref on partner yet, likely just GRI or handle fallback
        # In code: f"{line.product_id.x_gri}-{supplier.ref}" if ... else default_code
        # Since supplier.ref is empty, it might look like "GRI-001-" or check implementation details again
