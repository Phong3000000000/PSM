{
    "name": "PSM AI Invoice (No IAP)",
    "version": "19.0.1.0",
    "summary": "Read invoices with ChatGPT (or local AI) and create Vendor Bills without Odoo IAP",
    "author": "PSM Global",
    "license": "LGPL-3",
    "depends": ["account", "base_automation", "documents"],
    "data": [
        "security/ir.model.access.csv",
        "views/res_config_settings_views.xml",
        "views/account_move_views.xml",
        "data/ir_cron.xml",
        "data/ir_actions_server.xml"
    ],
    "installable": True,
}