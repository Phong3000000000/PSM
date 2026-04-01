{
    "name": "AI Invoice OCR (Free)",
    "version": "19.0.1.0.0",
    "summary": "Free OCR for Vendor Bills using Tesseract/EasyOCR",
    "author": "Your Team",
    "license": "LGPL-3",
    "depends": ["account", "documents"],
    "data": [
        "security/ir.model.access.csv",
        "data/ir_config.xml",
        "data/server_actions.xml",
        "views/invoice_ocr_wizard_views.xml",
        "views/res_config_settings_views.xml"
    ],
    "installable": true,
    "application": false
}
