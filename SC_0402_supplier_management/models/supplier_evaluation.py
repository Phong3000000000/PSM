# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class SupplierEvaluation(models.Model):
    _name = 'supplier.evaluation'
    _description = 'Supplier Evaluation'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc, id desc'
    
    # ===== HEADER =====
    
    name = fields.Char(
        string='Evaluation Number',
        required=True,
        copy=False,
        default='New',
        tracking=True,
    )
    
    state = fields.Selection([
        ('draft', 'Draft'),
        ('sourcing_search', 'Sourcing Search'),          # Step 2
        ('sourcing_review', 'Sourcing Review'),          # Steps 3-5
        ('qa_document_review', 'QA Document Review'),    # Steps 6-7
        ('qa_testing', 'QA Testing'),                    # Steps 8-12
        ('approved', 'Approved'),                        # Step 13 - Pass
        ('rejected_sourcing', 'Rejected (Sourcing)'),    # Step 7 - Fail
        ('rejected_qa', 'Rejected (QA)'),                # Step 13 - Fail
    ], default='draft', required=True, tracking=True)
    
    # ===== TYPE & PURPOSE =====
    
    evaluation_type = fields.Selection([
        ('new_product', 'New Product'),          # From Step 1
        ('optimization', 'Supplier Optimization'),  # From Step 21
    ], string='Type', required=True, default='new_product', tracking=True)
    
    # ===== SUPPLIER =====
    
    partner_id = fields.Many2one(
        'res.partner',
        string='Supplier',
        required=True,
        domain="[('is_company', '=', True), ('supplier_rank', '>', 0)]",
        tracking=True,
    )
    
    is_new_supplier = fields.Boolean(
        string='New Supplier',
        help='Check if this is a completely new supplier',
        tracking=True,
    )
    
    # ===== PRODUCT =====
    
    product_tmpl_id = fields.Many2one(
        'product.template',
        string='Product',
        help='Product being evaluated for this supplier',
    )
    
    # ===== OWNERSHIP =====
    
    sourcing_user_id = fields.Many2one(
        'res.users',
        string='Sourcing User',
        default=lambda self: self.env.user,
        tracking=True,
    )
    
    qa_user_id = fields.Many2one(
        'res.users',
        string='QA User',
        tracking=True,
    )
    
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company,
    )
    
    # ===== SUB-RECORDS =====
    
    # Steps 3-4: Certificates
    certificate_ids = fields.One2many(
        'supplier.certificate',
        'evaluation_id',
        string='Certificates',
    )
    
    certificate_count = fields.Integer(
        string='# Certificates',
        compute='_compute_counts',
    )
    
    # Step 5: Capacity
    capacity_id = fields.Many2one(
        'supplier.capacity',
        string='Capacity Assessment',
    )
    
    # Step 9: Factory Audits
    audit_ids = fields.One2many(
        'supplier.audit',
        'evaluation_id',
        string='Factory Audits',
    )
    
    audit_count = fields.Integer(
        string='# Audits',
        compute='_compute_counts',
    )
    
    # Step 10: Lab Tests
    lab_test_ids = fields.One2many(
        'lab.test',
        'evaluation_id',
        string='Lab Tests',
    )
    
    lab_test_count = fields.Integer(
        string='# Lab Tests',
        compute='_compute_counts',
    )
    
    # Step 11: Sensory Tests
    sensory_test_ids = fields.One2many(
        'sensory.test',
        'evaluation_id',
        string='Sensory Tests',
    )
    
    sensory_test_count = fields.Integer(
        string='# Sensory Tests',
        compute='_compute_counts',
    )
    
    # Step 13: Final Scorecard
    scorecard_id = fields.Many2one(
        'supplier.scorecard',
        string='Final Scorecard',
    )
    
    final_score = fields.Float(
        related='scorecard_id.total_score',
        string='Final Score',
        store=True,
    )
    
    # ===== DOCUMENTS INTEGRATION =====
    
    document_folder_id = fields.Many2one(
        'documents.document',
        string='Document Workspace',
        help='Folder for all evaluation documents',
        domain=[('type', '=', 'folder')],
    )
    
    document_count = fields.Integer(
        string='# Documents',
        compute='_compute_document_count',
    )
    
    # ===== NOTES =====
    
    note = fields.Html(string='Notes')
    
    rejection_reason = fields.Text(
        string='Rejection Reason',
        help='Reason for rejection (if applicable)',
    )
    
    # ===== COMPUTE METHODS =====
    
    @api.depends('certificate_ids', 'audit_ids', 'lab_test_ids', 'sensory_test_ids')
    def _compute_counts(self):
        for evaluation in self:
            evaluation.certificate_count = len(evaluation.certificate_ids)
            evaluation.audit_count = len(evaluation.audit_ids)
            evaluation.lab_test_count = len(evaluation.lab_test_ids)
            evaluation.sensory_test_count = len(evaluation.sensory_test_ids)
    
    @api.depends('document_folder_id')
    def _compute_document_count(self):
        for evaluation in self:
            if evaluation.document_folder_id:
                evaluation.document_count = self.env['documents.document'].search_count([
                    ('folder_id', '=', evaluation.document_folder_id.id)
                ])
            else:
                evaluation.document_count = 0
    
    # ===== CRUD =====
    
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('supplier.evaluation') or 'New'
        return super().create(vals_list)
    
    # ===== WORKFLOW METHODS =====
    
    # Step 2
    def action_start_sourcing(self):
        """Start sourcing process"""
        self.ensure_one()
        self.write({'state': 'sourcing_search'})
        self._create_document_workspace()
        return True
    
    # Steps 3-5
    def action_sourcing_complete(self):
        """Mark sourcing assessment as complete"""
        self.ensure_one()
        # Validation: Check if basic requirements are met
        if not self.env.is_admin() and not self.certificate_ids:
            raise UserError(_('Please add at least one certificate before completing sourcing review.'))
        
        self.write({'state': 'sourcing_review'})
        return True
    
    # Step 6
    def action_submit_to_qa(self):
        """Submit evaluation to QA for document review"""
        self.ensure_one()
        if not self.env.is_admin() and not self.qa_user_id:
            raise UserError(_('Please assign a QA user before submitting.'))
        
        self.write({'state': 'qa_document_review'})
        
        if self.qa_user_id:
            # Create activity for QA user
            self.activity_schedule(
                'sc_0402_supplier_management.mail_activity_qa_document_review',
                user_id=self.qa_user_id.id,
                summary=_('QA Document Review Required'),
                note=_('Please review supplier documents for evaluation %s', self.name),
            )
            
            # Send notification
            self.message_post(
                body=_(
                    'Supplier evaluation submitted to QA for document review.<br/>'
                    'Supplier: <b>%s</b><br/>'
                    'Product: <b>%s</b>',
                    self.partner_id.name,
                    self.product_tmpl_id.name if self.product_tmpl_id else 'N/A'
                ),
                subject=_('QA Review Required'),
                partner_ids=[self.qa_user_id.partner_id.id],
            )
        
        return True
    
    # Step 7 - Approve
    def action_qa_document_approve(self):
        """QA approves documents → proceed to testing"""
        self.ensure_one()
        self.write({'state': 'qa_testing'})
        
        self.message_post(
            body=_('Documents approved by QA. Proceeding to testing phase.'),
            subject=_('Documents Approved'),
        )
        
        return True
    
    # Step 7 - Reject
    def action_qa_document_reject(self):
        """QA rejects documents → back to sourcing"""
        self.ensure_one()
        return self._open_rejection_wizard('rejected_sourcing')
    
    # Step 13 - Final Approve
    def action_qa_final_approve(self):
        """QA final approval - also approves the vendor if draft"""
        self.ensure_one()
        self.write({'state': 'approved'})
        
        # Auto-create scorecard if not exists
        if not self.scorecard_id:
            self._create_scorecard()
        
        # AUTO-APPROVE VENDOR if still draft
        if self.partner_id.x_supplier_status == 'draft':
            self.partner_id.action_approve_vendor()
            self.message_post(
                body=_('Vendor <b>%s</b> has been approved and assigned code: <b>%s</b>',
                       self.partner_id.name, self.partner_id.x_supplier_code),
                subject=_('Vendor Approved'),
            )
        
        self.message_post(
            body=_('Supplier evaluation <b>APPROVED</b> by QA.<br/>Final Score: <b>%s</b>', 
                   self.final_score),
            subject=_('Evaluation Approved'),
        )
        
        return True
    
    # Step 13 - Final Reject
    def action_qa_final_reject(self):
        """QA final rejection"""
        self.ensure_one()
        return self._open_rejection_wizard('rejected_qa')
    
    def action_reset_to_draft(self):
        """Reset to draft"""
        self.ensure_one()
        self.write({'state': 'draft', 'rejection_reason': False})
        return True
    
    # ===== HELPER METHODS =====
    
    def _create_document_workspace(self):
        """Create documents folder for this evaluation"""
        self.ensure_one()
        if not self.document_folder_id:
            # Create a folder (documents.document with type='folder')
            folder = self.env['documents.document'].sudo().create({
                'name': f"SE{self.id:04d} - {self.partner_id.name}",
                'type': 'folder',
                'folder_id': self.env.ref('documents.documents_finance_folder', raise_if_not_found=False).id if self.env.ref('documents.documents_finance_folder', raise_if_not_found=False) else False,
            })
            self.document_folder_id = folder.id
    
    def _create_scorecard(self):
        """Auto-create scorecard from evaluation data"""
        self.ensure_one()
        if not self.scorecard_id:
            scorecard = self.env['supplier.scorecard'].create({
                'evaluation_id': self.id,
                'partner_id': self.partner_id.id,
                'product_tmpl_id': self.product_tmpl_id.id,
            })
            self.scorecard_id = scorecard.id
            scorecard.action_calculate_score()
    
    def _open_rejection_wizard(self, new_state):
        """Open wizard to enter rejection reason"""
        self.ensure_one()
        return {
            'name': _('Rejection Reason'),
            'type': 'ir.actions.act_window',
            'res_model': 'supplier.evaluation.rejection.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_evaluation_id': self.id,
                'default_new_state': new_state,
            },
        }
    
    # ===== SMART BUTTONS =====
    
    def action_view_certificates(self):
        """View certificates"""
        self.ensure_one()
        return {
            'name': _('Certificates'),
            'type': 'ir.actions.act_window',
            'res_model': 'supplier.certificate',
            'view_mode': 'list,form',
            'domain': [('evaluation_id', '=', self.id)],
            'context': {'default_evaluation_id': self.id, 'default_partner_id': self.partner_id.id},
        }
    
    def action_view_audits(self):
        """View audits"""
        self.ensure_one()
        return {
            'name': _('Factory Audits'),
            'type': 'ir.actions.act_window',
            'res_model': 'supplier.audit',
            'view_mode': 'list,form',
            'domain': [('evaluation_id', '=', self.id)],
            'context': {'default_evaluation_id': self.id, 'default_partner_id': self.partner_id.id },
        }
    
    def action_view_lab_tests(self):
        """View lab tests"""
        self.ensure_one()
        return {
            'name': _('Lab Tests'),
            'type': 'ir.actions.act_window',
            'res_model': 'lab.test',
            'view_mode': 'list,form',
            'domain': [('evaluation_id', '=', self.id)],
            'context': {'default_evaluation_id': self.id, 'default_product_tmpl_id': self.product_tmpl_id.id},
        }
    
    def action_view_sensory_tests(self):
        """View sensory tests"""
        self.ensure_one()
        return {
            'name': _('Sensory Tests'),
            'type': 'ir.actions.act_window',
            'res_model': 'sensory.test',
            'view_mode': 'list,form',
            'domain': [('evaluation_id', '=', self.id)],
            'context': {'default_evaluation_id': self.id, 'default_product_tmpl_id': self.product_tmpl_id.id},
        }
    
    def action_view_documents(self):
        """View documents folder"""
        self.ensure_one()
        if not self.document_folder_id:
            self._create_document_workspace()
        
        return {
            'name': _('Documents'),
            'type': 'ir.actions.act_window',
            'res_model': 'documents.document',
            'view_mode': 'kanban,tree,form',
            'domain': [('folder_id', '=', self.document_folder_id.id)],
            'context': {'default_folder_id': self.document_folder_id.id},
        }
