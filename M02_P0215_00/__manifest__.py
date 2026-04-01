# -*- coding: utf-8 -*-
{
    "name": "Disciplinary Process (M02_P0215_00)",
    "summary": """
        Manage Disciplinary Process: Violation Recording, Tracking, and Handling.
    """,
    "description": """
        Disciplinary Process (M02_P0215_00)
        ====================================
        Streamlines the disciplinary process for employees.
        
        Key Features:
        - Master Data: Violation Rules, Disciplinary Actions.
        - Process: Counseling Log -> Tường trình -> Review -> Decision.
        - Automation: Checks for repeat offenses within improvement period.
        - Levels: Store Level vs Company Level handling.
    """,
    "author": "TS-Solution",
    "category": "Human Resources",
    "version": "0.1",
    "depends": ["base", "hr", "mail", "portal", "calendar", "portal_custom"],
    "data": [
        "security/ir.model.access.csv",
        "data/mail_template.xml",
        "data/email_template_rejection.xml",
        "views/hr_discipline_master_views.xml",
        "views/hr_discipline_record_views.xml",
        "views/hr_discipline_reject_wizard_views.xml",
        "views/portal_templates.xml",
        "data/hr_discipline_violation_data.xml",
        "data/hr_discipline_action_data.xml",
        "data/cron_auto_archive.xml",
        "data/email_template_discipline_done.xml",
        "reports/discipline_reports.xml",
    ],
    "installable": True,
    "application": True,
    "license": "LGPL-3",
}
