# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.exceptions import UserError
import base64

class OdxOCRWizard(models.TransientModel):
    _name = "odx.ocr.wizard"
    _description = "ODX OCR Upload Wizard"

    upload = fields.Binary(string="File (PDF/Image)", required=True, attachment=True)
    filename = fields.Char(string="Filename")
    move_type = fields.Selection([
        ("out_invoice","Customer Invoice"),
        ("in_invoice","Vendor Bill"),
    ], string="Type", required=True, default=lambda self: self._default_move_type())
    create_partner_if_missing = fields.Boolean(string="Create partner if missing", default=True)
    create_product_if_missing = fields.Boolean(string="Create product if missing", default=True)

    def _default_move_type(self):
        ctx = self.env.context or {}
        return ctx.get("default_move_type") or "in_invoice"

    def action_process(self):
        self.ensure_one()
        if not self.upload:
            raise UserError("Please upload a file.")
        binary = base64.b64decode(self.upload)
        payload = self.env["odx.ocr.service"].parse_invoice(
            binary, self.filename or "upload", self.move_type, {
                "create_partner": self.create_partner_if_missing,
                "create_product": self.create_product_if_missing,
            }
        )
        move = self.env["account.move"].create(payload)
        action = self.env.ref("account.action_move_in_invoice_type").sudo().read()[0]
        # choose the correct action based on move type
        if self.move_type == "out_invoice":
            action = self.env.ref("account.action_move_out_invoice_type").sudo().read()[0]
        action["domain"] = [("id", "=", move.id)]
        action["views"] = [(self.env.ref("account.view_move_form").id, "form")]
        action["res_id"] = move.id
        return action
