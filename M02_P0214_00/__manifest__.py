# -*- coding: utf-8 -*-
{
    'name': 'Quy trình nghỉ việc RST',
    'version': '19.0.1.0.0',
    'category': 'Human Resources',
    'summary': 'Quy trình nghỉ việc RST',
    'description': """
        Module cho phép nhân viên gửi yêu cầu nghỉ việc từ Portal.
        - Form đơn giản với họ tên, line manager, lý do nghỉ việc
        - Tích hợp với Approvals để duyệt yêu cầu
    """,
    'author': 'PSM',
    'depends': [
        'base',
        'mail',
        'approvals',
        'hr',
        'portal',
        'survey',
        'M02_P0213_00',
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/approval_category_data.xml',
        'data/survey_exit_interview_data.xml',
        'data/email_template_exit_survey.xml',
        'data/email_template_adecco_notification.xml',
        'data/email_template_social_insurance.xml',
        'data/email_template_offboarding_reminder.xml',
        'data/email_template_dept_offboarding_reminder.xml',
        'data/ir_cron_data.xml',
        'views/resignation_portal_template.xml',
        'views/resignation_request_views.xml',
        'views/hr_employee_views.xml',
        'views/offboarding_report_views.xml',

        # 'data/offboarding_activity_plan_data.xml'
        'data/rst_demo_data.xml',
        'data/offboarding_plan_rst.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
