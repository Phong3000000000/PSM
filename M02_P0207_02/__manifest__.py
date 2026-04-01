# -*- coding: utf-8 -*-
{
    'name': 'Quy trình tính lương - bảng lương OPS (02)',
    'version': '1.0',
    'summary': 'Payroll Calculation Process for HR Department - Variant 02',
    'description': """
        M02_P0207_02: Quy trình tính lương OPS - Variant 02
        - Tính toán lương tự động từ Attendance Sheet
        - Xác nhận và phê duyệt lương
        - Tạo Ủy Nhiệm Chi (Payment Authorization)
        - Gửi phiếu lương cho nhân viên
    """,
    'category': 'Human Resources/Payroll',
    'author': 'PSM',
    'depends': [
        'hr_work_entry',
        'hr_payroll',
        'hr_attendance',
        'hr_holidays',
        'account',
        'approvals',
        'documents',
    ],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'data/approval_category_data.xml',
        'data/approval_category_clevel_data.xml',
        'data/hr_work_entry_type_data.xml',
        'data/hr_leave_type_data.xml',
        'data/archive_default_work_entry_types.xml',
        'data/ir_sequence_data.xml',
        # Payroll configuration data (migrated from hr_payroll_custom)
        'data/hr_payslip_inputs.xml',
        'data/salary_rules.xml',
        'data/salary_structure_13th.xml',
        'data/mail_template_data.xml',
        'wizard/data_loader_wizard_views.xml',
        'wizard/payslip_refuse_wizard_views.xml',
        'views/hr_attendance_sheet_views.xml',
        'views/payment_authorization_views.xml',
        'views/hr_payslip_views.xml',
        'views/approval_request_views.xml',
        'views/payroll_ops_config_views.xml',
        'views/menu.xml',
        # Reports
        # 'report/report_payment_order.xml',
    ],
    'external_dependencies': {
        'python': ['docx'],  # python-docx: tự động cài khi chưa có
    },
    'license': 'LGPL-3',
    'installable': True,
    'application': False,
    'auto_install': False,
    'assets': {
        'web.assets_backend': [
            'M02_P0207_02/static/src/css/payslip_approval.css',
            'M02_P0207_02/static/src/xml/payslip_approval_action.xml',
            'M02_P0207_02/static/src/xml/payrun_card_override.xml',
            'M02_P0207_02/static/src/js/payslip_approval_action.js',
        ],
    },
}

