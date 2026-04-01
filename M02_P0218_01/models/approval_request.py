# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)


class ApprovalRequest(models.Model):
    _inherit = 'approval.request'
    
    salary_plan_line_ids = fields.One2many(
        'salary.increase.plan.line',
        'approval_request_id',
        string='Salary Plan Lines'
    )
    
    email_sent = fields.Boolean(
        string='Salary Emails Sent',
        default=False,
        help='Track if salary increase emails have been sent to employees'
    )
    
    def action_approve(self, approver=None):
        # Call super to perform approval logic
        result = super().action_approve(approver=approver)
        
        # Check if the request is now fully approved AND is OPS category
        for request in self:
            ops_category = self.env.ref('M02_P0218_01.approval_category_salary_increase', raise_if_not_found=False)
            if (ops_category and request.category_id == ops_category
                    and request.request_status == 'approved' and not request.email_sent):
                request.action_send_salary_emails()
                request.action_update_employee_wage()  
                request.email_sent = True
            
        return result
    
    def _send_salary_increase_emails(self):
        """Send notification emails to employees when salary increase is approved."""
        for request in self:
            # Check if this is a salary increase approval
            salary_category = self.env.ref('M02_P0218_01.approval_category_salary_increase', raise_if_not_found=False)
            if not salary_category or request.category_id != salary_category:
                continue
            
            if not request.salary_plan_line_ids:
                _logger.warning(f'Approval request {request.name} has no salary plan lines to send emails to.')
                continue
            
            # Track email sending results
            success_count = 0
            failed_employees = []
            no_email_employees = []
            
            # Send email to each employee in the plan
            for line in request.salary_plan_line_ids:
                try:
                    result = line._send_notification_email()
                    if result == 'no_email':
                        no_email_employees.append(line.employee_id.name)
                    elif result == 'success':
                        success_count += 1
                    else:
                        failed_employees.append(line.employee_id.name)
                except Exception as e:
                    _logger.error(f'Failed to send salary increase email to {line.employee_id.name}: {str(e)}')
                    failed_employees.append(line.employee_id.name)
            
            # Post summary message to chatter
            total = len(request.salary_plan_line_ids)
            message_parts = [
                f'<p><strong>Kết quả gửi email thông báo tăng lương:</strong></p>',
                f'<ul>',
                f'<li>Tổng số nhân viên: {total}</li>',
                f'<li>Gửi thành công: <span style="color: green;">{success_count}</span></li>',
            ]
            
            if no_email_employees:
                message_parts.append(
                    f'<li>Không có email: <span style="color: orange;">{len(no_email_employees)}</span> '
                    f'({", ".join(no_email_employees[:5])}'
                    f'{"..." if len(no_email_employees) > 5 else ""})</li>'
                )
            
            if failed_employees:
                message_parts.append(
                    f'<li>Gửi thất bại: <span style="color: red;">{len(failed_employees)}</span> '
                    f'({", ".join(failed_employees[:5])}'
                    f'{"..." if len(failed_employees) > 5 else ""})</li>'
                )
            
            message_parts.append('</ul>')
            
            request.message_post(
                body=''.join(message_parts),
                subject='Thông báo gửi email tăng lương'
            )
            
            _logger.info(
                f'Salary increase emails sent for approval {request.name}: '
                f'{success_count}/{total} successful, '
                f'{len(no_email_employees)} no email, '
                f'{len(failed_employees)} failed'
            )
            
            # Mark as sent to prevent duplicate sends
            request.email_sent = True
    
    def action_send_salary_emails(self):
        """Manual action to send salary increase emails with UI notification."""
        self.ensure_one()
        
        # Check if this is a salary increase approval
        salary_category = self.env.ref('M02_P0218_01.approval_category_salary_increase', raise_if_not_found=False)
        if not salary_category or self.category_id != salary_category:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': 'This is not a salary increase approval request.',
                    'type': 'warning',
                    'sticky': False,
                }
            }
        
        if not self.salary_plan_line_ids:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': 'No salary plan lines found.',
                    'type': 'warning',
                    'sticky': False,
                }
            }
        
        # Track email sending results
        success_count = 0
        failed_employees = []
        no_email_employees = []
        
        # Send email to each employee
        for line in self.salary_plan_line_ids:
            try:
                result = line._send_notification_email()
                if result == 'no_email':
                    no_email_employees.append(line.employee_id.name)
                elif result == 'success':
                    success_count += 1
                else:
                    failed_employees.append(line.employee_id.name)
            except Exception as e:
                _logger.error(f'Failed to send email to {line.employee_id.name}: {str(e)}')
                failed_employees.append(line.employee_id.name)
        
        # Build notification message
        total = len(self.salary_plan_line_ids)
        message_lines = [f'📊 Kết quả gửi email:\n']
        message_lines.append(f'✅ Thành công: {success_count}/{total}')
        
        if no_email_employees:
            message_lines.append(f'⚠️ Không có email: {len(no_email_employees)}')
        
        if failed_employees:
            message_lines.append(f'❌ Thất bại: {len(failed_employees)}')
        
        message = '\n'.join(message_lines)
        
        # Post to chatter
        chatter_parts = [
            f'<p><strong>Kết quả gửi email thông báo tăng lương:</strong></p>',
            f'<ul>',
            f'<li>Tổng số nhân viên: {total}</li>',
            f'<li>Gửi thành công: <span style="color: green;">{success_count}</span></li>',
        ]
        
        if no_email_employees:
            chatter_parts.append(
                f'<li>Không có email: <span style="color: orange;">{len(no_email_employees)}</span> '
                f'({", ".join(no_email_employees[:5])}'
                f'{"..." if len(no_email_employees) > 5 else ""})</li>'
            )
        
        if failed_employees:
            chatter_parts.append(
                f'<li>Gửi thất bại: <span style="color: red;">{len(failed_employees)}</span> '
                f'({", ".join(failed_employees[:5])}'
                f'{"..." if len(failed_employees) > 5 else ""})</li>'
            )
        
        chatter_parts.append('</ul>')
        
        self.message_post(
            body=''.join(chatter_parts),
            subject='Thông báo gửi email tăng lương'
        )
        
        # Return notification
        notification_type = 'success' if success_count == total else 'warning' if success_count > 0 else 'danger'
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Gửi Email Tăng Lương',
                'message': message,
                'type': notification_type,
                'sticky': True,
            }
        }

    def action_update_employee_wage(self):
        """Action cập nhật lương (wage) cho nhân viên dựa trên các dòng kế hoạch lương."""
        self.ensure_one()
        
        # Kiểm tra xem có dòng kế hoạch lương hay không
        if not self.salary_plan_line_ids:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': 'Không có dòng kế hoạch lương nào để cập nhật.',
                    'type': 'warning',
                    'sticky': False,
                }
            }
            
        # Kiểm tra xem trường wage có tồn tại trên hr.employee không
        if 'wage' not in self.env['hr.employee']._fields:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': 'Không tìm thấy trường "wage" trên nhân viên (hr.employee). Hãy đảm bảo đã tạo trường này.',
                    'type': 'danger',
                    'sticky': True,
                }
            }
            
        success_count = 0
        error_count = 0
        
        for line in self.salary_plan_line_ids:
            try:
                # Chỉ cập nhật nếu có nhân viên và phần trăm tăng lương cuối cùng dương
                if line.employee_id and line.increase_percentage_final:
                    # Lấy lương hiện tại, mặc định là 0 nếu không có
                    current_wage = line.employee_id.wage or 0.0
                    
                    if current_wage:
                        # Tính lương mới = lương hiện tại * (1 + %tăng) (vì %tăng được lưu dạng decimal, VD: 0.03 cho 3%)
                        new_wage = current_wage * (1 + line.increase_percentage_final)
                        
                        # Cập nhật vào trường wage của hr.employee
                        line.employee_id.sudo().write({'wage': new_wage})
                        
                        # Nếu module có các trường lưu vết ở salary.increase.plan.line, thì ghi nhận
                        line_vals = {}
                        if 'old_wage' in line._fields:
                            line_vals['old_wage'] = current_wage
                        if 'new_wage' in line._fields:
                            line_vals['new_wage'] = new_wage
                        if 'is_applied' in line._fields:
                            line_vals['is_applied'] = True
                            
                        if line_vals:
                            line.sudo().write(line_vals)
                            
                        success_count += 1
            except Exception as e:
                _logger.error(f'Cập nhật lương thất bại cho {line.employee_id.name}: {str(e)}')
                error_count += 1
                
        # Tạo nội dung thông báo phản hồi
        message_lines = [f'📊 Kết quả cập nhật lương:\n']
        message_lines.append(f'✅ Thành công: {success_count} nhân viên')
        
        if error_count:
            message_lines.append(f'❌ Thất bại: {error_count} nhân viên')
            
        message = '\n'.join(message_lines)
        
        # Ghi nhận log vào khu vực trò chuyện (chatter) của phiếu duyệt
        self.message_post(
            body=f'<p><strong>Kết quả cập nhật lương:</strong></p><p>{message.replace(chr(10), "<br/>")}</p>',
            subject='Thông báo cập nhật lương'
        )
        
        # Xác định loại thông báo (xanh, đỏ, hoặc cam)
        notification_type = 'success' if error_count == 0 and success_count > 0 else 'warning' if success_count > 0 else 'danger'
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Cập Nhật Lương',
                'message': message,
                'type': notification_type,
                'sticky': False,
            }
        }
