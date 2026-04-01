# -*- coding: utf-8 -*-
import re
import os
import io
import base64
import tempfile
import subprocess
import glob
from odoo import models
from odoo.exceptions import UserError

# Optional OCR libraries
try:
    import pytesseract
    from PIL import Image
except Exception:
    pytesseract = None

try:
    import easyocr as _easyocr
except Exception:
    _easyocr = None


class AIInvoiceOCREngine(models.AbstractModel):
    _name = "ai.invoice.ocr.engine"
    _description = "AI Invoice OCR Engine (Free)"

    # ---------------------------
    # PDF → Image conversion
    # ---------------------------
    def _pdf_to_images(self, binary_pdf):
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=True) as f:
            f.write(binary_pdf)
            f.flush()
            out_dir = tempfile.mkdtemp()
            subprocess.run(
                ["pdftoppm", "-png", f.name, os.path.join(out_dir, "page")],
                check=True,
                capture_output=True
            )
            pages = sorted(glob.glob(os.path.join(out_dir, "page-*.png")))
            if not pages:
                raise UserError("Không chuyển được PDF sang ảnh.")
            return pages

    # ---------------------------
    # OCR bằng Tesseract
    # ---------------------------
    def _tesseract_ocr(self, image_paths, lang):
        if not pytesseract:
            raise UserError("Chưa cài pytesseract/Pillow trên máy chủ.")
        texts = []
        for path in image_paths:
            img = Image.open(path)
            texts.append(pytesseract.image_to_string(img, lang=lang.replace("+", "+")))
        return "\n".join(texts), {"engine": "tesseract"}

    # ---------------------------
    # OCR bằng EasyOCR
    # ---------------------------
    def _easyocr_ocr(self, image_paths, lang):
        if not _easyocr:
            raise UserError("Chưa cài easyocr trên máy chủ.")
        reader = _easyocr.Reader(lang.split("+"), gpu=False)
        texts = []
        for path in image_paths:
            result = reader.readtext(path, detail=0, paragraph=True)
            texts.append("\n".join(result))
        return "\n".join(texts), {"engine": "easyocr"}

    # ---------------------------
    # Entry point OCR
    # ---------------------------
    def extract_text(self, attachment, engine="tesseract", lang="eng"):
        # Đọc dữ liệu nhị phân
        if attachment.datas:
            binary = base64.b64decode(attachment.datas)
        else:
            with open(attachment._full_path(attachment.store_fname), "rb") as f:
                binary = f.read()

        # Phân loại file
        fname = (attachment.name or "").lower()
        if fname.endswith(".pdf") or (attachment.mimetype or "").endswith("/pdf"):
            image_paths = self._pdf_to_images(binary)
        else:
            with tempfile.NamedTemporaryFile(suffix=".img", delete=False) as f:
                f.write(binary)
                image_paths = [f.name]

        # Gọi OCR engine
        if engine == "easyocr":
            return self._easyocr_ocr(image_paths, lang)
        return self._tesseract_ocr(image_paths, lang)

    # ---------------------------
    # Phân tích dữ liệu hóa đơn từ text
    # ---------------------------
    def parse_invoice(self, text, hints=None):
        norm = " ".join(text.split())
        vals = {
            "partner_name": None,
            "vat": None,
            "invoice_date": None,
            "invoice_number": None,
            "amount_total": None,
            "amount_tax": None,
            "currency": "VND",
            "lines": [],
        }

        # Tên công ty
        m = re.search(r"(C[ôo]ng ty[\w\s\.\-&]*)", norm, re.IGNORECASE)
        vals["partner_name"] = m.group(1).strip()[:120] if m else None

        # Mã số thuế
        m = re.search(r"(MST|VAT|Tax\s*Code)[:\s\-]*([0-9]{8,14})", norm, re.IGNORECASE)
        vals["vat"] = m.group(2) if m else None

        # Số hóa đơn
        m = re.search(r"(S[ốo]\s*h[óo]a\s*đ[ơo]n|Invoice\s*No\.?)[:\s\-]*([A-Z0-9\-\/]{4,30})", norm, re.IGNORECASE)
        vals["invoice_number"] = m.group(2) if m else None

        # Ngày hóa đơn
        m = re.search(r"(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{4}|\d{4}[\/\-]\d{1,2}[\/\-]\d{1,2})", norm)
        vals["invoice_date"] = m.group(1) if m else None

        # Tổng tiền (ước lượng đơn giản)
        m = re.findall(r"([0-9\.,]{5,})", norm)
        if m:
            try:
                vals["amount_total"] = float(m[-1].replace(".", "").replace(",", ""))
            except Exception:
                vals["amount_total"] = None

        return vals
