# -*- coding: utf-8 -*-
from odoo import api, models
import logging
_logger = logging.getLogger(__name__)

class OdxOCRService(models.AbstractModel):
    _name = "odx.ocr.service"
    _description = "ODX OCR Service (stub)"

    def parse_invoice(self, binary_content, filename, move_type, options=None):
        """Stub OCR parser.
        Return minimal dict to create account.move and lines.
        In production, integrate your OCR here (tesseract/cloud)."""
        _logger.info("ODX OCR: received file %s (%s bytes), move_type=%s, options=%s",
                     filename, len(binary_content or b""), move_type, options)
        # Minimal draft payload (empty invoice; user fills later)
        partner_id = self.env.user.company_id.partner_id.id
        return {
            "move_type": move_type or "in_invoice",
            "partner_id": partner_id,
            "invoice_line_ids": [
                (0, 0, {
                    "name": "OCR placeholder",
                    "quantity": 1.0,
                    "price_unit": 0.0,
                })
            ],
        }
