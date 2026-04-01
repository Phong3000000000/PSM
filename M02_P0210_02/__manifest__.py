{
    'name': 'OPS Management Capacity Development (M02_P0210_02)',
    'version': '2.0',
    'summary': 'Manage OPS Capacity Development Workflow (B1-B32)',
    'description': """
        OPS Management Capacity Development Module
        ==========================================
        This module manages the full capacity development lifecycle for OPS roles:
        - Crew -> Shift Manager (SM) -> DM1 -> DM2 -> RGM -> Future Leader
        
        Features:
        - Complete B1-B32 workflow with exact step tracking
        - Gateway logic (B7, B17, B22) with auto-skip for already achieved levels
        - Evaluation system for RGM (SET/PET, Course checks) and OC (SLV, SV)
        - Profile Update subprocess (B12-B16) with skill granting
        - Integration with M02_P0209_02 (SOC/eLearning) for course completion
    """,
    'author': 'PSM',
    'depends': ['base', 'hr', 'hr_skills', 'mail', 'M02_P0209_02', 'M02_P0206_00'],
    'data': [
        'security/ir.model.access.csv',
        'security/security_rules.xml',
        'wizard/wizard_views.xml',
        'wizard/manager_proposal_wizard_views.xml',
        'wizard/feedback_wizard_views.xml',
        'views/ops_capacity_views.xml',
        'views/manager_schedule_views.xml',
        'views/hr_employee_views.xml',
        'views/potential_list_extension.xml',
        'views/portal_templates.xml',
        'views/development_config_views.xml',
        'views/menu_views.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': True,
    'license': 'LGPL-3',
}
