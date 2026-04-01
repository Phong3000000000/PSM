{
    "name": "M01_P0103_00 - Approval Advance Claim",
    "version": "1.0.0",
    "category": "Approvals",
    "summary": "Approval Advance Cliam",
    "depends": [
        "approvals",
        "hr",
        "hr_expense",
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/approval_category_view.xml",
        "views/approval_category_rule_view.xml",
        "views/approval_request_view.xml",
    ],
    "installable": True,
    "license": "LGPL-3",
}