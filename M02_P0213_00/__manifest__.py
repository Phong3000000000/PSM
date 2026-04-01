# -*- coding: utf-8 -*-
{
    'name': 'Quy trình nghỉ việc',
    'version': '19.0.1.0.0',
    'category': 'Human Resources',
    'summary': 'Quy trình nghỉ việc',
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
        # nên depend thêm 0200 để có thể approval trên portal, tạo nhanh account portal bằng 1 nút
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
        'data/offboarding_activity_plan_data.xml',
        'views/resignation_portal_template.xml',
        'views/resignation_request_views.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
