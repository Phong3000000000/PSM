from odoo import models, fields, api, _

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    pif_status = fields.Selection([
        ('draft', 'Draft'),
        ('approved', 'Approved'),
    ], string='PIF Status', default='draft', tracking=True)

    pif_product_type = fields.Selection([
        ('finished', 'Finished Product'),
        ('raw', 'Raw Material'),
    ], string='PIF Type', default='finished', tracking=True)

    pif_bom_id = fields.Many2one('mrp.bom', string='PIF BOM/Formula', 
                                 domain="[('product_tmpl_id', '=', id)]",
                                 help="Select the main Formula/BOM for this PIF project.")
    
    wrin_code = fields.Char(string='WRIN Code')
    gri_code = fields.Char(string='GRI Code')

class MrpBom(models.Model):
    _inherit = 'mrp.bom'

    pif_status = fields.Selection([
        ('draft', 'Draft'),
        ('approved', 'Approved'),
    ], string='PIF Status', default='draft')
    
class PifRequestRawLine(models.Model):
    _name = 'pif.request.raw.line'
    _description = 'PIF Request Raw Material'

    request_id = fields.Many2one('approval.request', string='Request', ondelete='cascade')
    
    gri_code = fields.Char(string='GRI')
    wrin_code = fields.Char(string='WRIN')
    product_id = fields.Many2one('product.product', string='Raw Item Name')
    quantity = fields.Float(string='Quantity')
    uom_id = fields.Many2one('uom.uom', string='UoM')