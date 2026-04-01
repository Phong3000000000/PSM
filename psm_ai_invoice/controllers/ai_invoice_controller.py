import json
from base64 import b64decode
from odoo import http
from odoo.http import request

class AiInvoiceController(http.Controller):
    @http.route('/psm_ai_invoice/ingest', type='json', auth='user', methods=['POST'], csrf=False)
    def ingest(self, **payload):
        """
        Payload:
        {
          "filename": "inv_abc.pdf",
          "content_base64": "<...>",
          "move_id": 123,  # optional: attach to a draft bill
          "company_id": 1   # optional
        }
        """
        env = request.env
        company = env.company
        if payload.get("company_id"):
            company = env["res.company"].browse(int(payload["company_id"])) or env.company
        content_b64 = payload.get("content_base64")
        if not content_b64:
            return {"ok": False, "error": "content_base64 is required"}

        # Create attachment
        attachment = env["ir.attachment"].sudo().create({
            "name": payload.get("filename", "invoice_upload.bin"),
            "type": "binary",
            "datas": content_b64,
            "res_model": "account.move" if payload.get("move_id") else False,
            "res_id": int(payload["move_id"]) if payload.get("move_id") else False,
            "company_id": company.id,
        })

        # Call service to extract + create/update bill
        service = env["psm.ai.invoice.service"].with_company(company)
        result = service.process_attachment(attachment, link_to_move_id=payload.get("move_id"))
        return result
