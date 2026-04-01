from odoo import models, fields, api, _

class ApprovalCategory(models.Model):
    _inherit = 'approval.category'
    
    is_pif = fields.Boolean(string='Is PIF Process', help='If checked, approving a request of this category will create a PIF Object.')

class ApprovalRequest(models.Model):
    _inherit = 'approval.request'
    
    pif_object_id = fields.Many2one('pif.object', string='Related PIF', copy=False)
    pif_object_count = fields.Integer(compute='_compute_pif_count')
    is_pif_category = fields.Boolean(related='category_id.is_pif')
    
    pif_request_type = fields.Selection([
        ('menu', 'Menu'),
        ('marketing', 'Marketing'),
        ('si', 'S&I'),
        ('digital', 'Digital'),
        ('supply_chain', 'Supply Chain'),
    ], string='Request Type', default='menu')
    
    # NEW LOGIC: Select Product directly (must be approved)
    pif_product_id = fields.Many2one('product.product', string='Select Approved Product', 
                                     domain="[('pif_status', '=', 'approved')]",
                                     help='Select a product that has been approved for PIF.')
    
    # Auto-filled from Selected Product (Readonly)
    pif_product_name = fields.Char(related='pif_product_id.name', string='Product Name', readonly=True)
    pif_product_code = fields.Char(related='pif_product_id.default_code', string='Code/WRIN', readonly=True)
    
    pif_vendor_id = fields.Many2one('res.partner', string='Vendor', readonly=True, compute='_compute_from_product', store=True)
    pif_bom_id = fields.Many2one('mrp.bom', string='BOM', readonly=True, compute='_compute_from_product', store=True)
    
    raw_item_ids = fields.One2many('pif.request.raw.line', 'request_id', string='Raw Items', readonly=True)

    # Computed fields for Headers
    request_owner_department_id = fields.Many2one('hr.department', compute='_compute_owner_info', string='Department')
    request_owner_job_id = fields.Many2one('hr.job', compute='_compute_owner_info', string='Job Position')

    @api.depends('request_owner_id')
    def _compute_owner_info(self):
        for rec in self:
            employee = self.env['hr.employee'].search([('user_id', '=', rec.request_owner_id.id)], limit=1)
            rec.request_owner_department_id = employee.department_id if employee else False
            rec.request_owner_job_id = employee.job_id if employee else False

    @api.depends('pif_product_id')
    def _compute_from_product(self):
        for rec in self:
            if rec.pif_product_id:
                # Find BOM for this product
                # Logic: Find BOM where product_id is this product OR product_tmpl_id is this product's template
                # Use standard search
                bom = self.env['mrp.bom'].search([
                    '|',
                    ('product_id', '=', rec.pif_product_id.id),
                    '&',
                    ('product_tmpl_id', '=', rec.pif_product_id.product_tmpl_id.id),
                    ('product_id', '=', False)
                ], limit=1, order='sequence, id')
                
                rec.pif_bom_id = bom
                
                # Vendor: from product.seller_ids (first one)
                seller = rec.pif_product_id.seller_ids[:1]
                rec.pif_vendor_id = seller.partner_id if seller else False
            else:
                rec.pif_vendor_id = False
                rec.pif_bom_id = False

    @api.onchange('pif_product_id')
    def _onchange_pif_product_id_populate(self):
        if not self.pif_product_id:
            self.raw_item_ids = [(5, 0, 0)]
            self.pif_vendor_id = False # Force clear
            self.pif_bom_id = False
            return
        
        # Trigger compute manually or rely on depends. 
        # Onchange primarily for One2many population which isn't computed stored easily.
        self._compute_from_product()
        
        # Populate Raw Items from BOM
        lines = []
        if self.pif_bom_id:
            for bom_line in self.pif_bom_id.bom_line_ids:
                 lines.append((0, 0, {
                    'gri_code': bom_line.product_id.default_code, 
                    'wrin_code': '', 
                    'product_id': bom_line.product_id.id,
                    'quantity': bom_line.product_qty,
                    'uom_id': bom_line.product_uom_id.id,
                }))
        self.raw_item_ids = [(5, 0, 0)] + lines
        
    @api.depends('pif_product_id') # Keeping for compatibility if used elsewhere
    def _compute_pif_product_vendor(self):
         # Redundant but kept to avoid breaking view if referenced by old name
         for rec in self:
            partners = rec.pif_product_id.seller_ids.mapped('partner_id.name')
            # We already have pif_vendor_id, but view uses this field potentially? 
            # I will check view next. For now, basic logic.
            rec.pif_product_vendor = ", ".join(partners) if partners else ""
            

    @api.model
    def default_get(self, fields_list):
        defaults = super(ApprovalRequest, self).default_get(fields_list)
        defaults['name'] = _('Request Creation PIF')
        defaults['request_owner_id'] = self.env.user.id
        return defaults

    @api.onchange('category_id')
    def _onchange_category_id_pif(self):
        if self.category_id.is_pif:
            self.name = _('Request Creation PIF')

    def _compute_pif_count(self):
        for rec in self:
            rec.pif_object_count = 1 if rec.pif_object_id else 0

    def action_approve(self, approver=None):
        super(ApprovalRequest, self).action_approve(approver=approver)
        for rec in self:
            if rec.category_id.is_pif and not rec.pif_object_id:
                # Create PIF Object
                pif_vals = {
                    'approval_request_id': rec.id,
                    'pif_request_type': rec.pif_request_type, 
                    'pif_product_id': rec.pif_product_id.id,
                    'request_owner_id': rec.request_owner_id.id,
                    'request_owner_department_id': rec.request_owner_department_id.id,
                    'request_owner_job_id': rec.request_owner_job_id.id,
                }

                pif = self.env['pif.object'].create(pif_vals)
                rec.pif_object_id = pif.id

    def action_open_pif(self):
        self.ensure_one()
        return {
            'name': _('PIF Execution'),
            'type': 'ir.actions.act_window',
            'res_model': 'pif.object',
            'res_id': self.pif_object_id.id,
            'view_mode': 'form',
            'target': 'current',
        }
