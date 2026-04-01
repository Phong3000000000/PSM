from odoo import models
class Attachment(models.Model):
    _inherit = "ir.attachment"
    def action_extract_vendor_bill(self):
        self.ensure_one()
        wiz = self.env["invoice.ocr.wizard"].create({"attachment_id": self.id})
        return {"type":"ir.actions.act_window","res_model":"invoice.ocr.wizard","view_mode":"form","target":"new","res_id":wiz.id}
