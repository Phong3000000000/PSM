from odoo import api, fields, models

class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    psm_ai_provider = fields.Selection([
        ("chatgpt", "ChatGPT"),
        ("local", "Local OCR/LLM")
    ], string="AI Provider", default="chatgpt", config_parameter="psm_ai_invoice.provider")

    psm_ai_openai_api_key = fields.Char(string="OpenAI API Key", config_parameter="psm_ai_invoice.openai_api_key")
    psm_ai_openai_model = fields.Char(string="OpenAI Model", default="gpt-4o-mini", config_parameter="psm_ai_invoice.openai_model")
    psm_ai_auto_create_vendor = fields.Boolean(string="Auto-create vendor if missing", default=True,
                                               config_parameter="psm_ai_invoice.auto_create_vendor")
    psm_ai_auto_add_service = fields.Boolean(string="Auto-add service if missing", default=True,config_parameter="psm_ai_invoice.auto_add_service")
    psm_ai_tax_map_mode = fields.Selection([
        ("name", "By tax name"),
        ("rate", "By tax rate (%)")
    ], string="Tax Mapping", default="rate", config_parameter="psm_ai_invoice.tax_map_mode")