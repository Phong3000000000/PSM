# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import UserError
from datetime import timedelta


class FoodSafetyComplaint(models.Model):
    _name = 'food.safety.complaint'
    _description = 'Food Safety Complaint'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

    # Basic Information
    name = fields.Char(
        string='Complaint Number',
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: self.env['ir.sequence'].next_by_code('food.safety.complaint') or 'New'
    )
    
    title = fields.Char(
        string='Title',
        required=True,
        tracking=True
    )
    
    description = fields.Html(
        string='Description',
        tracking=True
    )
    
    # Complaint Source
    source_type = fields.Selection([
        ('store', 'From Store'),
        ('customer', 'From Customer')
    ], string='Complaint Source', required=True, default='store', tracking=True)
    
    # Store Information (Multi-store support)
    store_id = fields.Many2one(
        'stock.warehouse',
        string='Store/Restaurant',
        required=True,
        tracking=True,
        help='The store/restaurant where the complaint originated'
    )
    
    # Customer Information (if source is customer)
    partner_id = fields.Many2one(
        'res.partner',
        string='Customer',
        tracking=True,
        help='Customer who reported the complaint'
    )
    
    partner_phone = fields.Char(
        string='Customer Phone',
        related='partner_id.phone',
        readonly=True
    )
    
    partner_email = fields.Char(
        string='Customer Email',
        related='partner_id.email',
        readonly=True
    )
    
    # Product Information
    product_type = fields.Selection([
        ('finished', 'Finished Product'),
        ('material', 'Raw Material (NVL)')
    ], string='Product Type', tracking=True)
    
    product_id = fields.Many2one(
        'product.product',
        string='Product',
        required=True,
        tracking=True
    )

    @api.onchange('product_id')
    def _onchange_product_id(self):
        if self.product_id:
            # Map Odoo product type to our product_type selection
            if self.product_id.type == 'product':
                self.product_type = 'finished'
            else:
                self.product_type = 'material'
        else:
            self.product_type = False
    
    # Lot/Serial Number for traceability
    lot_id = fields.Many2one(
        'stock.lot',
        string='Lot/Serial Number',
        tracking=True,
        help='For product traceability'
    )
    
    # Food Safety Specific Fields
    safety_issue_type = fields.Selection([
        ('contamination', 'Contamination'),
        ('foreign_object', 'Foreign Object'),
        ('spoilage', 'Spoilage/Expiry'),
        ('quality_defect', 'Quality Defect'),
        ('packaging', 'Packaging Issue'),
        ('labeling', 'Labeling Issue'),
        ('allergen', 'Allergen Issue'),
        ('temperature', 'Temperature Abuse'),
        ('other', 'Other')
    ], string='Safety Issue Type', required=True, tracking=True)
    
    severity = fields.Selection([
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('critical', 'Critical')
    ], string='Severity', default='medium', required=True, tracking=True)
    
    # Fault Analysis
    fault_source = fields.Selection([
        ('pending', 'Pending Analysis'),
        ('restaurant', 'Restaurant Fault'),
        ('supplier', 'Supplier Fault'),
        ('both', 'Both'),
        ('external', 'External Factor')
    ], string='Fault Source', default='pending', tracking=True)
    
    supplier_id = fields.Many2one(
        'res.partner',
        string='Supplier',
        domain=[('supplier_rank', '>', 0)],
        tracking=True,
        help='Supplier if fault is from supplier'
    )
    
    # Dates
    complaint_date = fields.Datetime(
        string='Complaint Date',
        default=fields.Datetime.now,
        required=True,
        tracking=True
    )


    # Error origin (set when user selects error type)
    error_origin = fields.Selection([
        ('store', 'Store'),
        ('supplier', 'Supplier')
    ], string='Error Origin', readonly=True, tracking=True)
    receipt_id = fields.Many2one(
        'stock.picking',
        string='Receipt',
        domain=[('picking_type_code', '=', 'incoming')],
        help='Select the incoming receipt if the error is caused by the supplier'
    )
    isolate_lot = fields.Boolean(string='Isolate Lot', help='Mark if the lot needs to be quarantined')
    receipt_supplier_id = fields.Many2one(
        'res.partner',
        string='Receipt Supplier',
        compute='_compute_receipt_supplier',
        store=True,
        help='Supplier from the selected receipt'
    )

    @api.depends('receipt_id')
    def _compute_receipt_supplier(self):
        for rec in self:
            if rec.receipt_id and rec.receipt_id.partner_id:
                rec.receipt_supplier_id = rec.receipt_id.partner_id
            else:
                rec.receipt_supplier_id = False
    
    # Supplier Workflow
    supplier_accepts_fault = fields.Boolean(
        string='Supplier Accepts Fault',
        help='Check if supplier acknowledges the error'
    )
    capa_file = fields.Binary(
        string='CAPA File',
        help='Corrective and Preventive Action file from supplier'
    )
    capa_filename = fields.Char(string='CAPA Filename')
    
    # CAPA Evaluation
    capa = fields.Html(
        string='CAPA Evaluation',
        help='Corrective and Preventive Action evaluation notes'
    )
    
    # Store Handling
    store_capa_file = fields.Binary(
        string='Store CAPA File',
        help='Corrective and Preventive Action file from store'
    )
    store_capa_filename = fields.Char(string='Store CAPA Filename')
    
    # Evaluation Notes
    evaluation_notes = fields.Text(string='Evaluation Notes')
    
    # Compensation Pickings
    compensation_picking_ids = fields.One2many(
        'stock.picking',
        'complaint_id',
        string='Compensation Pickings',
        readonly=True
    )
    compensation_picking_count = fields.Integer(
        string='Compensation Count',
        compute='_compute_compensation_picking_count'
    )
    
    @api.depends('compensation_picking_ids')
    def _compute_compensation_picking_count(self):
        for rec in self:
            rec.compensation_picking_count = len(rec.compensation_picking_ids)


    # New Workflow Actions
    def action_submit(self):
        """Submit complaint"""
        self.write({'state': 'submitted'})
        # Send notification to assigned user
        if self.user_id:
            self.message_post(
                body=f"Food Safety Complaint {self.name} has been submitted and assigned to you.",
                subject=f"FSC {self.name} - New Assignment",
                partner_ids=[self.user_id.partner_id.id],
                message_type='notification'
            )
    
    def action_select_store_error(self):
        """Select Store Error - move to store evaluation"""
        self.ensure_one()
        self.write({
            'state': 'evaluation_store',
            'error_origin': 'store'
        })
        self.message_post(body="Error identified as Store fault. Moved to Store Evaluation.")
    
    def action_select_supplier_error(self):
        """Select Supplier Error - move to supplier evaluation"""
        self.ensure_one()
        self.write({
            'state': 'evaluation_supplier',
            'error_origin': 'supplier'
        })
        self.message_post(body="Error identified as Supplier fault. Moved to Supplier Evaluation.")
    
    def action_request_store_capa(self):
        """Request Store to provide CAPA again"""
        self.ensure_one()
        self.message_post(
            body="Store has been requested to provide CAPA document.",
            subject=f"FSC {self.name} - CAPA Request"
        )
        # Could send email to store manager here
        return True
    
    def action_approve_store_capa(self):
        """Approve Store CAPA and move to follow up"""
        self.ensure_one()
        self.write({'state': 'follow_up'})
        self.message_post(body="Store CAPA approved. Moved to Follow Up.")
    
    def action_request_supplier_capa_resend(self):
        """Request supplier to resend CAPA - reopen email composer"""
        self.ensure_one()
        # Get supplier from receipt
        supplier_partner = self.receipt_supplier_id
        if not supplier_partner:
            raise UserError('Please select a faulty receipt first to identify the supplier.')
        
        self.message_post(body=f"Re-requested CAPA from supplier {supplier_partner.name}.")
        
        # Prepare email body for RESEND
        body = f"""
        <p>Dear {supplier_partner.name},</p>
        
        <p><strong style="color: #d9534f;">This is a RE-REQUEST for CAPA submission.</strong></p>
        
        <p>We are following up on our previous request regarding the food safety complaint. 
        The previously submitted CAPA was not satisfactory. Please review and provide an improved CAPA document.</p>
        
        <h4>Complaint Details:</h4>
        <ul>
            <li><strong>Complaint Number:</strong> {self.name}</li>
            <li><strong>Product:</strong> {self.product_id.name}</li>
            <li><strong>Receipt:</strong> {self.receipt_id.name}</li>
            <li><strong>Issue Type:</strong> {dict(self._fields['safety_issue_type'].selection).get(self.safety_issue_type, '')}</li>
            <li><strong>Severity:</strong> {dict(self._fields['severity'].selection).get(self.severity, '')}</li>
        </ul>
        
        <p><strong>Please submit an updated CAPA as soon as possible.</strong></p>
        
        <p>Best regards,<br/>
        Quality Assurance Team</p>
        """
        
        return {
            'type': 'ir.actions.act_window',
            'name': 'Re-send CAPA Request to Supplier',
            'res_model': 'mail.compose.message',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_model': 'food.safety.complaint',
                'default_res_ids': [self.id],
                'default_partner_ids': [(6, 0, [supplier_partner.id])],
                'default_subject': f'[RE-REQUEST] Food Safety Complaint {self.name} - CAPA Required',
                'default_body': body,
                'default_email_from': self.env.user.email or self.env.company.email,
            }
        }
    
    def action_approve_supplier_capa(self):
        """Approve Supplier CAPA and move to follow up"""
        self.ensure_one()
        # Validate receipt is selected
        if not self.receipt_id:
            raise UserError('Please select the faulty receipt before approving CAPA.')
        self.write({'state': 'follow_up'})
        self.message_post(body="Supplier CAPA approved. Moved to Follow Up.")
    
    def action_reject_supplier_capa(self):
        """Reject Supplier CAPA"""
        self.ensure_one()
        # Validate receipt is selected
        if not self.receipt_id:
            raise UserError('Please select the faulty receipt before rejecting CAPA.')
        self.write({'state': 'capa_rejected'})
        self.message_post(
            body="Supplier CAPA has been rejected.",
            message_type='notification'
        )
    
    def action_create_quarantine_request(self):
        """Create quarantine request for the lot (placeholder)"""
        self.ensure_one()
        # Placeholder for future implementation
        self.message_post(body="Quarantine request created for this lot.")
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Quarantine Request',
                'message': 'Quarantine request functionality will be implemented soon.',
                'type': 'info',
                'sticky': False,
            }
        }
    
    def action_mark_completed(self):
        """Mark complaint as completed"""
        self.ensure_one()
        self.write({'state': 'completed'})
        self.message_post(body="Complaint has been marked as completed.")
    
    def action_view_compensation_pickings(self):
        """Smart button to view compensation pickings"""
        self.ensure_one()
        
        return {
            'type': 'ir.actions.act_window',
            'name': 'Compensation Pickings',
            'res_model': 'stock.picking',
            'view_mode': 'list,form',
            'domain': [('id', 'in', self.compensation_picking_ids.ids)],
            'context': {'create': False}
        }
    
    # Compensation Actions (for Supplier CAPA approved)
    def action_create_compensation_receipt(self):
        """Create compensation receipt (incoming without PO)"""
        self.ensure_one()
        
        if not self.receipt_id or not self.product_id:
            raise UserError('Receipt and Product are required to create compensation receipt.')
        
        # Get the warehouse from original receipt
        warehouse = self.receipt_id.picking_type_id.warehouse_id
        if not warehouse:
            raise UserError('Cannot determine warehouse from the original receipt.')
        
        # Create incoming picking
        picking_type = self.env['stock.picking.type'].search([
            ('code', '=', 'incoming'),
            ('warehouse_id', '=', warehouse.id)
        ], limit=1)
        
        if not picking_type:
            raise UserError(f'No incoming picking type found for warehouse {warehouse.name}')
        
        # Create the picking
        picking_vals = {
            'picking_type_id': picking_type.id,
            'partner_id': self.receipt_supplier_id.id,
            'location_id': self.env.ref('stock.stock_location_suppliers').id,
            'location_dest_id': picking_type.default_location_dest_id.id,
            'origin': f'Compensation for {self.receipt_id.name} - FSC {self.name}',
            'move_ids': [(0, 0, {
                'product_id': self.product_id.id,
                'product_uom_qty': 1.0,  # Default quantity, user can change
                'product_uom': self.product_id.uom_id.id,
                'location_id': self.env.ref('stock.stock_location_suppliers').id,
                'location_dest_id': picking_type.default_location_dest_id.id,
            })]
        }
        
        new_picking = self.env['stock.picking'].create(picking_vals)
        
        # Link picking to this complaint
        new_picking.write({'complaint_id': self.id})
        
        self.message_post(
            body=f'Compensation receipt created: <a href="#" data-oe-model="stock.picking" data-oe-id="{new_picking.id}">{new_picking.name}</a>'
        )
        
        # Return action to open the new picking
        return {
            'type': 'ir.actions.act_window',
            'name': 'Compensation Receipt',
            'res_model': 'stock.picking',
            'res_id': new_picking.id,
            'view_mode': 'form',
            'target': 'current',
        }
    
    def action_deduct_payables(self):
        """Deduct from supplier payables (placeholder)"""
        self.ensure_one()
        self.message_post(body="Payable deduction request logged.")
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Deduct Payables',
                'message': 'Payable deduction functionality will be implemented soon.',
                'type': 'info',
                'sticky': False,
            }
        }
    
    def action_compensation_payment(self):
        """Request compensation payment (placeholder)"""
        self.ensure_one()
        self.message_post(body="Compensation payment request logged.")
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Compensation Payment',
                'message': 'Compensation payment functionality will be implemented soon.',
                'type': 'info',
                'sticky': False,
            }
        }
    
    def action_view_supplier_agreements(self):
        """Smart button to view supplier agreements"""
        self.ensure_one()
        if not self.receipt_supplier_id:
            raise UserError('No supplier selected for this complaint.')
        
        # Check if agreement model exists
        if 'agreement' not in self.env:
            # Fallback: show supplier form if agreement module not installed
            return {
                'type': 'ir.actions.act_window',
                'name': f'Supplier: {self.receipt_supplier_id.name}',
                'res_model': 'res.partner',
                'res_id': self.receipt_supplier_id.id,
                'view_mode': 'form',
                'target': 'current',
            }
        
        # Return action to view agreements for this supplier
        return {
            'type': 'ir.actions.act_window',
            'name': f'Agreements with {self.receipt_supplier_id.name}',
            'res_model': 'agreement',
            'view_mode': 'list,form',
            'domain': [('partner_id', '=', self.receipt_supplier_id.id)],
            'context': {'default_partner_id': self.receipt_supplier_id.id}
        }
    
    def action_send_supplier_email(self):
        """Send email to supplier"""
        self.ensure_one()
        
        # Get supplier email from receipt
        supplier_partner = self.receipt_supplier_id
        if not supplier_partner:
            raise UserError('Please select a faulty receipt first to identify the supplier.')
        
        self.message_post(body=f"Email prepared for supplier {supplier_partner.name}.")
        
        # Prepare email body
        body = f"""
        <p>Dear {supplier_partner.name},</p>
        
        <p>We are writing to inform you about a food safety complaint related to a delivery from your company.</p>
        
        <h4>Complaint Details:</h4>
        <ul>
            <li><strong>Complaint Number:</strong> {self.name}</li>
            <li><strong>Product:</strong> {self.product_id.name}</li>
            <li><strong>Receipt:</strong> {self.receipt_id.name}</li>
            <li><strong>Issue Type:</strong> {dict(self._fields['safety_issue_type'].selection).get(self.safety_issue_type, '')}</li>
            <li><strong>Severity:</strong> {dict(self._fields['severity'].selection).get(self.severity, '')}</li>
        </ul>
        
        <p>We kindly request your explanation and corrective action plan (CAPA) regarding this matter.</p>
        
        <p>Please respond within 48 hours.</p>
        
        <p>Best regards,<br/>
        Quality Assurance Team</p>
        """
        
        return {
            'type': 'ir.actions.act_window',
            'name': 'Send Email to Supplier',
            'res_model': 'mail.compose.message',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_model': 'food.safety.complaint',
                'default_res_ids': [self.id],
                'default_partner_ids': [(6, 0, [supplier_partner.id])],
                'default_subject': f'Food Safety Complaint {self.name} - Request for Explanation',
                'default_body': body,
                'default_email_from': self.env.user.email or self.env.company.email,
            }
        }

    
    incident_date = fields.Date(
        string='Incident Date',
        tracking=True,
        help='When the incident actually occurred'
    )
    
    # Status and Workflow
    state = fields.Selection([
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('evaluation_store', 'Evaluation - Store Error'),
        ('evaluation_supplier', 'Evaluation - Supplier Error'),
        ('follow_up', 'Follow Up'),
        ('completed', 'Completed'),
        ('capa_rejected', 'CAPA Rejected'),
        ('cancelled', 'Cancelled')
    ], string='Status', default='draft', required=True, tracking=True)
    
    priority = fields.Selection([
        ('0', 'Low'),
        ('1', 'Normal'),
        ('2', 'High'),
        ('3', 'Urgent')
    ], string='Priority', default='1', tracking=True)
    
    # Assigned Users
    user_id = fields.Many2one(
        'res.users',
        string='Assigned To',
        tracking=True,
        default=lambda self: self.env.user
    )
    
    qa_user_id = fields.Many2one(
        'res.users',
        string='QA Inspector',
        tracking=True,
        help='Quality Assurance person assigned to analyze'
    )
    
    # Images and Attachments
    image_1920 = fields.Image(
        string='Image',
        max_width=1920,
        max_height=1920
    )
    
    # Analysis and Actions
    root_cause = fields.Text(
        string='Root Cause Analysis',
        tracking=True
    )
    
    corrective_action = fields.Text(
        string='Corrective Action',
        tracking=True
    )
    
    preventive_action = fields.Text(
        string='Preventive Action',
        tracking=True
    )
    
    resolution_notes = fields.Text(
        string='Resolution Notes',
        tracking=True
    )
    
    # Quality Control Integration
    quality_check_ids = fields.Many2many(
        'quality.check',
        string='Quality Checks',
        help='Related quality control checks'
    )
    
    # Additional Info
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company,
        required=True
    )
    
    active = fields.Boolean(
        default=True
    )
    
    # Computed Fields
    is_from_customer = fields.Boolean(
        compute='_compute_is_from_customer',
        store=True
    )
    
    @api.depends('source_type')
    def _compute_is_from_customer(self):
        for record in self:
            record.is_from_customer = record.source_type == 'customer'
    
    # Actions
    def action_submit(self):
        self.write({'state': 'submitted'})
        
    def action_start_analysis(self):
        self.write({'state': 'analysis'})
        
    def action_start_action(self):
        self.write({'state': 'action'})
        
    def action_resolve(self):
        self.write({'state': 'resolved'})
        
    def action_cancel(self):
        self.write({'state': 'cancelled'})
        
    def action_reset_to_draft(self):
        self.write({'state': 'draft'})
