# -*- coding: utf-8 -*-
{
    'name': 'M02_P0200 Master Data',
    'version': '1.1',
    'summary': 'Master Data: Users, Employees, Hierarchy, Department Blocks, Restaurant Config',
    'category': 'Human Resources',
    'author': 'PSM',
    'description': """
M02_P0200: HR Master Data
========================
Creates standard users and employees with strict 1-to-1 linking and hierarchy.
Also adds 'x_is_portal_manager' field to Users to identify Portal Managers (DM, SM).

Features:
- Department Blocks (RST/OPS)
- POS integration for OPS departments
- Restaurant Area / Positioning Area / Station configuration
- Shift (Ca làm) configuration

Hierarchy:
RGM (Internal) -> DM (Portal) -> SM (Portal) -> Crew (Portal)
    """,
    'depends': [
        'base',
        'hr',
        'hr_recruitment',
        'mail',
        'accountant',
        'l10n_vn',
        'approvals',
        'point_of_sale',
        'planning',
    ],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'data/hr_job_grade_data.xml',
        'data/hr_job_level_data.xml',
        'data/department_block_data.xml',
        'data/rst_department_data.xml',
        'data/hr_job_position_default_data.xml',
        'data/rst_job_data.xml',
        'data/hr_master_data.xml',
        'views/portal_approval_views.xml',
        'views/res_users_views.xml',
        'views/hr_employee_views.xml',
        'views/department_block_views.xml',
        'views/hr_department_views.xml',
        'views/hr_job_views.xml',
        'views/hr_job_position_default_views.xml',
        'views/hr_job_level_views.xml',
        'views/hr_job_grade_views.xml',
        'views/restaurant_config_views.xml',
        'views/pos_config_views.xml',
        'data/store_data.xml',
        'data/shift_log_checklist_data.xml',
        'wizard/shift_log_generate_wizard_views.xml',
        'views/shift_log_views.xml',
        'views/shift_log_checklist_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'M02_P0200/static/src/mic_assignment_matrix/**/*',
        ],
    },
    'installable': True,
    'application': True,
    'license': 'OEEL-1',
}
