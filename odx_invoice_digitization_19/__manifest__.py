# -*- coding: utf-8 -*-
{
    "name": "ODX Invoice Digitization 19",
    "summary": "Create invoice via OCR (wizard + stub service) for Odoo 19 Enterprise",
    "version": "19.0.1.0.0",
    "category": "Accounting",
    "author": "Jun/PSM Global",
    "maintainer": "Jun/PSM Global",
      "license": "LGPL-3",
    "depends": ["account", "web"],
    "data": [
        "security/ir.model.access.csv",
        "views/account_move_cp_button.xml",
        "views/ocr_wizard_views.xml"
    ],
    "assets": {
        # No JS required; we use Control Panel slot + action link to wizard
    },
    "installable": True,
    "application": False,
}
