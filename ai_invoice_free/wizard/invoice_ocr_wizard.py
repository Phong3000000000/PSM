from odoo import api, fields, models
from odoo.exceptions import UserError
class InvoiceOCRWizard(models.TransientModel):
    _name = "invoice.ocr.wizard"
    _description = "Extract Vendor Bill from Attachment"
    attachment_id = fields.Many2one("ir.attachment", required=True)
    engine = fields.Selection([("tesseract","Tesseract"), ("easyocr","EasyOCR")],
        default=lambda self: self.env["ir.config_parameter"].sudo().get_param("ai_invoice_free.engine","tesseract"), required=True)
    lang = fields.Char(default=lambda s: s.env["ir.config_parameter"].sudo().get_param("ai_invoice_free.lang","vie+eng"))
    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        if not res.get("attachment_id") and self.env.context.get("active_id"):
            res["attachment_id"] = self.env.context["active_id"]
        return res
    def action_extract(self):
        self.ensure_one()
        engine = self.env["ai.invoice.ocr.engine"]
        text, hints = engine.extract_text(self.attachment_id, self.engine, self.lang)
        vals = engine.parse_invoice(text, hints)
        bill = engine.create_vendor_bill(vals, self.attachment_id)
        action = self.env.ref("account.action_move_in_invoice_type").read()[0]
        action["res_id"] = bill.id
        action["views"] = [(self.env.ref("account.view_move_form").id, "form")]
        return action
