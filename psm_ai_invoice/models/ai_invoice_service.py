# -*- coding: utf-8 -*-
import base64
import io
import json
import logging
import re
import requests

from odoo import api, fields, models, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

PROMPT_JSON_SCHEMA = """
You are an expert invoice parser for Vietnam manufacturing (footwear & apparel).
Extract fields from the provided invoice (text extracted from PDF or image OCR).
Return STRICT JSON ONLY with keys:

{
  "invoice_number": "string or null",
  "invoice_date": "YYYY-MM-DD or null",
  "vendor": {
    "name": "string",
    "vat": "string or null",
    "address": "string or null"
  },
  "currency": "VND|USD|... or null",
  "subtotal": number or null,
  "tax_total": number or null,
  "total": number,
  "lines": [
    {
      "description": "string",
      "sku": "string or null",
      "uom": "string or null",
      "quantity": number,
      "unit_price": number,
      "tax_rate": number or null
    }
  ]
}
"""


def extract_json_from_text(text):
    if not text:
        return None
    try:
        return json.loads(text.strip())
    except Exception:
        pass

    start = text.find('{')
    end = text.rfind('}')
    if start != -1 and end != -1 and end > start:
        candidate = text[start:end + 1]
        while candidate:
            try:
                return json.loads(candidate)
            except Exception:
                pos = candidate.rfind('}')
                if pos <= 0:
                    break
                candidate = candidate[:pos]

    matches = re.findall(r'\{(?:[^{}]|\{[^{}]*\})*\}', text)
    for m in matches:
        try:
            return json.loads(m)
        except Exception:
            continue
    return None


class PsmAiInvoiceService(models.AbstractModel):
    _name = "psm.ai.invoice.service"
    _description = "PSM AI Invoice Service (No IAP)"

    # ========================
    # CONFIG
    # ========================

    @api.model
    def _conf(self):
        ICP = self.env["ir.config_parameter"].sudo()
        return {
            "provider": ICP.get_param("psm_ai_invoice.provider", "chatgpt"),
            "openai_api_key": ICP.get_param("psm_ai_invoice.openai_api_key"),
            "openai_model": ICP.get_param("psm_ai_invoice.openai_model", "gpt-4o-mini"),
            "auto_create_vendor": ICP.get_param("psm_ai_invoice.auto_create_vendor", "True") == "True",
            "tax_map_mode": ICP.get_param("psm_ai_invoice.tax_map_mode", "rate"),
        }

    # ========================
    # MAIN PUBLIC ENTRY POINT
    # ========================

    @api.model
    def process_attachment(self, attachment, link_to_move_id=None):
        """
        Nhận ir.attachment -> trích xuất AI -> tạo/cập nhật vendor bill.
        Trả về {"ok": True, "move_id": id, "move_name": name}
        """
        if not attachment:
            raise UserError(_("Attachment not provided."))

        _logger.debug(
            "Processing attachment id=%s name=%s res_model=%s res_id=%s",
            attachment.id, attachment.name, attachment.res_model, attachment.res_id
        )

        # ---- Step 1: Đọc dữ liệu file ----
        content_b64 = None
        try:
            if attachment.datas:
                content_b64 = attachment.datas
            elif getattr(attachment, "store_fname", False):
                try:
                    raw = attachment._file_read(attachment.store_fname)
                    if isinstance(raw, bytes):
                        content_b64 = base64.b64encode(raw).decode("ascii")
                    else:
                        content_b64 = base64.b64encode(raw.encode("utf-8", errors="ignore")).decode("ascii")
                except Exception as e:
                    _logger.warning("Cannot read from filestore for %s: %s", attachment.store_fname, e)
        except Exception as e:
            _logger.exception("Failed to read attachment: %s", e)
            raise UserError(_("Cannot read attachment: %s") % e)

        if not content_b64:
            raise UserError(_("Attachment has no data (id=%s name=%s)") % (attachment.id, attachment.name))

        # Gán tạm để hàm _ai_extract_json có thể dùng attachment.datas
        attachment.datas = content_b64

        # ---- Step 2: Gọi AI trích xuất JSON ----
        parsed = self._ai_extract_json(attachment)
        if not parsed or not parsed.get("total"):
            raise UserError(_("AI could not extract valid total or lines from invoice."))

        # ---- Step 3: Tạo hoặc cập nhật bill ----
        move = None
        if link_to_move_id:
            move = self.env["account.move"].sudo().browse(int(link_to_move_id))
            if not move.exists():
                move = None

        bill = self._create_or_update_bill(parsed, move=move, attachment=attachment)
        return {"ok": True, "move_id": bill.id, "move_name": bill.name}

    # ========================
    # AI EXTRACTION LOGIC
    # ========================

    @api.model
    def _ai_extract_json(self, attachment):
        cfg = self._conf()
        filename = (attachment.name or "invoice.pdf").lower()
        is_pdf = filename.endswith(".pdf")

        if cfg["provider"] == "chatgpt":
            return self._call_openai_with_file(
                content_b64=attachment.datas,
                filename=filename,
                model=cfg["openai_model"],
                api_key=cfg["openai_api_key"],
                is_pdf=is_pdf,
            )
        else:
            raise UserError(_("Unsupported provider: %s") % cfg["provider"])

    @api.model
    def _call_openai_with_file(self, content_b64, filename, model, api_key, is_pdf=False):
        try:
            from pypdf import PdfReader
        except Exception:
            raise UserError(_("Missing dependency 'pypdf'. Please install it."))

        if not api_key:
            raise UserError(_("OpenAI API key not configured."))

        extracted_text = ""
        if is_pdf:
            decoded = base64.b64decode(content_b64)
            reader = PdfReader(io.BytesIO(decoded))
            for page in reader.pages:
                try:
                    extracted_text += page.extract_text() + "\n"
                except Exception:
                    continue
        else:
            extracted_text = base64.b64decode(content_b64).decode("utf-8", errors="ignore")

        if not extracted_text.strip():
            raise UserError(_("Could not extract text from invoice file."))

        if len(extracted_text) > 200000:
            extracted_text = extracted_text[:200000]

        prompt = PROMPT_JSON_SCHEMA + "\n\nExtracted text:\n" + extracted_text
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        body = {
            "model": model,
            "messages": [
                {"role": "system", "content": PROMPT_JSON_SCHEMA},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.0,
        }

        url = "https://api.openai.com/v1/chat/completions"
        resp = requests.post(url, headers=headers, json=body, timeout=180)
        if resp.status_code >= 300:
            raise UserError(_("AI provider error: %s") % resp.text)

        data = resp.json()
        content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
        parsed = extract_json_from_text(content)
        if not parsed:
            raise UserError(_("AI did not return valid JSON."))

        return parsed

    # ========================
    # BILL CREATION LOGIC
    # ========================

    @api.model
    def _create_or_update_bill(self, data, move=None, attachment=None):
        Partner = self.env["res.partner"].sudo()
        Move = self.env["account.move"].sudo()
        Tax = self.env["account.tax"].sudo()
        cfg = self._conf()

        # --- Vendor ---
        vendor_data = data.get("vendor") or {}
        vat = vendor_data.get("vat")
        name = vendor_data.get("name")
        vendor = None

        if vat:
            vendor = Partner.search([("vat", "=", vat)], limit=1)
        if not vendor and name:
            vendor = Partner.search([("name", "ilike", name)], limit=1)
        if not vendor and cfg["auto_create_vendor"] and name:
            vendor = Partner.create({
                "name": name,
                "vat": vat or False,
                "street": vendor_data.get("address") or False,
                "supplier_rank": 1,
                "company_type": "company",
            })
        if not vendor:
            raise UserError(_("Vendor not found and auto-create disabled."))

        # --- Currency ---
        currency = (data.get("currency") or "VND").upper()
        currency_rec = (
            self.env["res.currency"].search([("name", "=", currency)], limit=1)
            or self.env.company.currency_id
        )

        # --- Lines ---
        line_vals = []
        for ln in data.get("lines", []):
            taxes = False
            if ln.get("tax_rate") is not None:
                if cfg["tax_map_mode"] == "rate":
                    taxes = Tax.search([
                        ("amount", "=", ln["tax_rate"]),
                        ("type_tax_use", "in", ["purchase", "none"])
                    ])
                else:
                    taxes = Tax.search([("name", "ilike", str(ln["tax_rate"]))])
                taxes = [(6, 0, taxes.ids)] if taxes else False

            line_vals.append((0, 0, {
                "name": ln.get("description") or "/",
                "quantity": ln.get("quantity") or 1.0,
                "price_unit": ln.get("unit_price") or 0.0,
                "tax_ids": taxes,
            }))

        # --- Move ---
        move_vals = {
            "move_type": "in_invoice",
            "partner_id": vendor.id,
            "invoice_date": data.get("invoice_date") or fields.Date.context_today(self),
            "invoice_origin": data.get("invoice_number") or False,
            "currency_id": currency_rec.id,
            "invoice_line_ids": line_vals,
        }

        if move and move.exists() and move.state == "draft":
            move.write(move_vals)
            bill = move
        else:
            bill = Move.create(move_vals)

        # --- Link attachment ---
        if attachment and not (attachment.res_model and attachment.res_id):
            attachment.write({"res_model": "account.move", "res_id": bill.id})

        return bill
