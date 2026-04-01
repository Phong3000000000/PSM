from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from datetime import date, timedelta

class ManagerSchedule(models.Model):
    _name = 'mcd.manager.schedule'
    _description = 'Manager Development Schedule'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'schedule_date desc, id desc'

    name = fields.Char(string='Reference', required=True, copy=False, readonly=True, default='New')
    
    employee_id = fields.Many2one('hr.employee', string='Employee', required=True, tracking=True)
    proposed_by_id = fields.Many2one('hr.employee', string='Proposer (RGM)', 
                                      compute='_compute_hierarchy', store=True, readonly=True,
                                      tracking=True, 
                                      help="Direct Manager of Employee (RGM)")
    oc_id = fields.Many2one('hr.employee', string='OC Evaluator', 
                             compute='_compute_hierarchy', store=True, readonly=True,
                             tracking=True, help='Operations Consultant - Manager of RGM')
    
    schedule_date = fields.Date(string='Start Date', required=True, tracking=True)
    schedule_end_date = fields.Date(string='End Date', tracking=True)
    
    development_type = fields.Selection([
        ('shift_manager', 'Develop to Shift Manager'),
        ('dm1', 'Develop to DM1'),
        ('dm2', 'Develop to DM2'),
        ('rgm', 'Develop to RGM'),
    ], string='Development Type', tracking=True)
    
    content = fields.Html(string='Schedule Content')
    
    # =============== B1-B5 WORKFLOW STATES ===============
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        # Vòng lặp chính
        ('b1_course', 'B1: Participate in Course 1'),
        ('b2_rgm_eval', 'B2: RGM Evaluation'),
        ('b3_course', 'B3: Participate in Course 2'),
        ('b4_oc_eval', 'B4: OC Evaluation'),
        # Kiểm tra điều kiện lên RGM
        ('b5_lff', 'B5.1: Participate in LFF'),
        ('b5_lff_eval', 'B5.2: OC evaluates LFF'),
        # Feedback
        ('waiting_feedback', 'Pending Post-Training Evaluation'),
        # Kết thúc
        ('done', 'Done'),
        ('cancelled', 'Cancelled')
    ], string='Status', default='draft', tracking=True)
    
    # Feedback fields
    lnd_feedback_status = fields.Selection([
        ('pending', 'Pending'),
        ('done', 'Done')
    ], string='L&D Evaluation', default='pending', tracking=True)
    lnd_feedback = fields.Text(string='L&D Evaluation Content')
    
    employee_feedback_status = fields.Selection([
        ('pending', 'Pending'),
        ('done', 'Done')
    ], string='Employee Evaluation', default='pending', tracking=True)
    employee_feedback = fields.Text(string='Employee Evaluation Content')
    
    # Course info (để trống, không có nội dung)
    course_1_name = fields.Char(string='Course 1 Name', compute='_compute_course_names')
    course_2_name = fields.Char(string='Course 2 Name', compute='_compute_course_names')
    
    # Evaluation results
    b2_result = fields.Selection([('pass', 'Pass'), ('fail', 'Fail')], string='B2 Result')
    b2_notes = fields.Text(string='B2 Notes')
    b4_result = fields.Selection([('pass', 'Pass'), ('fail', 'Fail')], string='B4 Result')
    b4_notes = fields.Text(string='B4 Notes')
    b5_lff_result = fields.Selection([('pass', 'Pass'), ('fail', 'Fail')], string='LFF Result')
    b5_lff_notes = fields.Text(string='LFF Notes')
    
    company_id = fields.Many2one('res.company', string='Company', 
                                  default=lambda self: self.env.company)
    
    # Link to development config
    config_id = fields.Many2one('mcd.development.config', string='Development Config',
                                 compute='_compute_config_id', store=True, readonly=True)

    @api.depends('development_type', 'company_id')
    def _compute_config_id(self):
        """Find matching development config for this schedule"""
        for record in self:
            if record.development_type:
                config = self.env['mcd.development.config'].search([
                    ('development_type', '=', record.development_type),
                    ('active', '=', True),
                    '|', ('company_id', '=', record.company_id.id), ('company_id', '=', False)
                ], limit=1, order='company_id desc')
                record.config_id = config
            else:
                record.config_id = False

    @api.depends('development_type', 'config_id', 'config_id.course_line_ids')
    def _compute_course_names(self):
        """Compute course names based on development config or fallback to defaults"""
        default_map = {
            'shift_manager': ('Running Areas', 'Shift Leadership Foundation'),
            'dm1': ('Advancing Your Leadership on the Shift', 'System Verification (3 kỹ năng đầu)'),
            'dm2': ('Developing the Leader in Me (DLIM)', 'System Verification (2 kỹ năng tiếp)'),
            'rgm': ('Leading Great Restaurant (LGR)', 'System Verification (4 kỹ năng cuối)'),
        }
        for record in self:
            # Try to get from config first
            if record.config_id and record.config_id.course_line_ids:
                lines = record.config_id.course_line_ids.sorted('sequence')
                record.course_1_name = lines[0].course_name if len(lines) > 0 else ''
                record.course_2_name = lines[1].course_name if len(lines) > 1 else ''
            else:
                # Fallback to default mapping
                courses = default_map.get(record.development_type, ('', ''))
                record.course_1_name = courses[0]
                record.course_2_name = courses[1]

    @api.depends('employee_id', 'employee_id.parent_id', 'employee_id.parent_id.parent_id')
    def _compute_hierarchy(self):
        """Compute RGM and OC based on employee's hierarchy"""
        for record in self:
            if record.employee_id and record.employee_id.parent_id:
                record.proposed_by_id = record.employee_id.parent_id
                # OC is the manager of the RGM
                if record.employee_id.parent_id.parent_id:
                    record.oc_id = record.employee_id.parent_id.parent_id
                else:
                    record.oc_id = False
            else:
                record.proposed_by_id = False
                record.oc_id = False

    @api.constrains('employee_id')
    def _check_employee_contract(self):
        for record in self:
            # Check employment_type from M02_P0206_00
            if hasattr(record.employee_id, 'employment_type') and record.employee_id.employment_type == 'part_time':
                raise ValidationError(_('Part-time employee (%s) is not eligible for the Manager Development Program.') % record.employee_id.name)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('mcd.manager.schedule') or 'MGR-NEW'
        return super().create(vals_list)

    # =============== WORKFLOW ACTIONS ===============
    
    def action_confirm(self):
        """Xác nhận và bắt đầu B1"""
        self.write({'state': 'b1_course'})
        self.message_post(body=_('Process started. Employee participating in course: %s') % self.course_1_name)
    
    def action_complete_b1(self):
        """B1 hoàn thành → chuyển sang B2 (RGM đánh giá)"""
        self.write({'state': 'b2_rgm_eval'})
        self.message_post(body=_('Employee completed Course 1. Waiting for RGM evaluation.'))
    
    def action_b2_pass(self):
        """B2 đạt → chuyển sang B3"""
        self.write({'state': 'b3_course', 'b2_result': 'pass'})
        self.message_post(body=_('RGM evaluation: PASS. Employee continues to course: %s') % self.course_2_name)
        # Gửi email mời nhân viên tham gia khoá 2
        self._send_course_2_invitation_email()
    
    def action_b2_fail(self):
        """B2 không đạt → quay lại B1"""
        self.write({'state': 'b1_course', 'b2_result': 'fail'})
        self.message_post(body=_('RGM evaluation: FAIL. Employee needs to retake Course 1.'))
    
    def action_complete_b3(self):
        """B3 hoàn thành → chuyển sang B4 (OC đánh giá)"""
        self.write({'state': 'b4_oc_eval'})
        self.message_post(body=_('Employee completed Course 2. Waiting for OC evaluation.'))
        # Gửi email thông báo OC
        self._send_oc_notification_email()
    
    def action_b4_pass(self):
        """B4 đạt → kiểm tra điều kiện"""
        self.write({'b4_result': 'pass'})
        
        # B5: Kiểm tra nếu đang lên RGM thì cần thêm LFF
        if self.development_type == 'rgm':
            self.write({'state': 'b5_lff'})
            self.message_post(body=_('OC evaluation: PASS. Proceeding to Leading For Future (LFF).'))
            # Gửi email mời LFF
            self._send_lff_invitation_email()
        else:
            # Hoàn thành và chuyển sang chờ feedback
            self._move_to_feedback_phase()

    def _send_lff_invitation_email(self):
        """Gửi email mời nhân viên tham gia Leading For Future (LFF)"""
        self.ensure_one()
        
        if not self.employee_id.work_email:
            self.message_post(body=_('Employee has no email. Cannot send LFF invitation.'))
            return

        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        # Use portal URL
        schedule_url = f"{base_url}/my/manager/schedule/{self.id}"
        
        self.message_post(body=_('Sending email inviting employee to LFF'))
        
        try:
            self.env['mail.mail'].sudo().create({
                'subject': 'Invitation to Leading For Future (LFF) Program',
                'body_html': f'''
                    <p>Hello <strong>{self.employee_id.name}</strong>,</p>
                    <p>Congratulations on successfully completing the previous stages and being rated PASS by OC.</p>
                    <p>Next, you are invited to a special program for future RGMs:</p>
                    <h3 style="color: #875A7B;">Leading For Future (LFF)</h3>
                    <p>This is a key development step. Please arrange time to participate and confirm completion on the system after finishing.</p>
                    <p style="margin: 20px 0;">
                        <a href="{schedule_url}" 
                           style="background-color: #875A7B; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">
                            Access System
                        </a>
                    </p>
                    <p>Best regards,<br/>L&D Team</p>
                ''',
                'email_to': self.employee_id.work_email,
                'auto_delete': True,
            }).send(raise_exception=False)
            self.message_post(body=_('Sent LFF invitation email to employee.'))
        except Exception as e:
            self.message_post(body=_('Error sending LFF invitation email: %s') % str(e))
    
    def action_b4_fail(self):
        """B4 không đạt → quay lại B3"""
        self.write({'state': 'b3_course', 'b4_result': 'fail'})
        self.message_post(body=_('OC evaluation: FAIL. Employee needs to retake Course 2.'))
    
    def action_complete_lff(self):
        """LFF hoàn thành → chuyển sang đánh giá LFF"""
        self.write({'state': 'b5_lff_eval'})
        self.message_post(body=_('Employee completed LFF. Waiting for OC evaluation.'))
        # Gửi email thông báo OC
        self._send_oc_notification_email()
    
    def action_lff_pass(self):
        """LFF đạt → Hoàn thành toàn bộ và thăng chức lên RGM"""
        self.write({'b5_lff_result': 'pass'})
        self._move_to_feedback_phase()
    
    def action_lff_fail(self):
        """LFF không đạt → quay lại LFF"""
        self.write({'state': 'b5_lff', 'b5_lff_result': 'fail'})
        self.message_post(body=_('OC evaluation LFF: FAIL. Employee needs to retake LFF.'))
    
    def _move_to_feedback_phase(self):
        """Move to feedback phase"""
        self.ensure_one()
        
        self.message_post(body=_('Development program completed evaluation steps! Moving to feedback phase.'))
        
        # Chuyển sang chờ feedback
        self.write({
            'state': 'waiting_feedback',
            'lnd_feedback_status': 'pending',
            'employee_feedback_status': 'pending'
        })
        
        # Gửi email yêu cầu feedback
        self._send_feedback_request_emails()

    def _apply_promotion(self):
        """Apply promotion to the employee - update Job Position"""
        self.ensure_one()
        
        # Mapping development_type to job name
        job_name_map = {
            'shift_manager': 'Shift Manager (SM)',
            'dm1': 'Department Manager 1 (DM1)',
            'dm2': 'Department Manager 2 (DM2)',
            'rgm': 'Restaurant General Manager (RGM)',
        }
        
        new_job_name = job_name_map.get(self.development_type)
        
        if new_job_name:
            # Find or create the job position
            job = self.env['hr.job'].search([
                ('name', 'ilike', new_job_name.split('(')[0].strip())
            ], limit=1)
            
            if not job:
                # Create the job if not exists
                job = self.env['hr.job'].create({
                    'name': new_job_name,
                    'company_id': self.company_id.id,
                })
            
            # Update employee's job position
            old_job = self.employee_id.job_id.name or 'N/A'
            self.employee_id.write({'job_id': job.id})
            
            self.message_post(body=_(
                'Program finished! Employee %s has been promoted from "%s" to "%s".'
            ) % (self.employee_id.name, old_job, new_job_name))
            
            # Gửi email chúc mừng
            if self.employee_id.work_email:
                self.env['mail.mail'].sudo().create({
                    'subject': f'Congratulations on promotion: {new_job_name}',
                    'body_html': f'''
                        <div style="font-family: Arial, sans-serif; color: #333;">
                            <h2 style="color: #875A7B;">Congratulations {self.employee_id.name}!</h2>
                            <p>Congratulations on successfully completing the training and development program.</p>
                            <p>We are pleased to announce that you have been officially promoted to the position:</p>
                            <h3 style="color: #212529; background-color: #f8f9fa; padding: 10px; border-radius: 5px; text-align: center;">
                                {new_job_name}
                            </h3>
                            <p>Thank you for your efforts and dedication.</p>
                            <p>Wishing you even more success in your new role!</p>
                            <br/>
                            <p>Best regards,<br/><strong>L&D Team</strong></p>
                        </div>
                    ''',
                    'email_to': self.employee_id.work_email,
                    'auto_delete': True,
                }).send(raise_exception=False)
                self.message_post(body=_('Sent promotion congratulation email to employee.'))

    def _send_feedback_request_emails(self):
        """Gửi email yêu cầu đánh giá cho L&D và Nhân viên"""
        self.ensure_one()
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        # Use portal URL for everyone safe
        schedule_url = f"{base_url}/my/manager/schedule/{self.id}"
        dev_label = dict(self._fields['development_type'].selection).get(self.development_type, self.development_type)
        
        # 1. Gửi cho L&D (Admin) - still uses portal link which is fine for admin too
        admin_user = self.env.ref('base.user_admin')
        if admin_user.partner_id.email:
            self.env['mail.mail'].sudo().create({
                'subject': f'[Evaluation] Training Effectiveness - {self.employee_id.name}',
                'body_html': f'''
                    <p>Hello L&D Team,</p>
                    <p>Employee <strong>{self.employee_id.name}</strong> has completed the <strong>{dev_label}</strong> program.</p>
                    <p>Please evaluate the training effectiveness.</p>
                    <p><a href="{schedule_url}" style="background-color: #875A7B; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">Evaluate Now</a></p>
                ''',
                'email_to': admin_user.partner_id.email,
            }).send()

        # 2. Gửi cho Nhân viên (Portal User)
        if self.employee_id.work_email:
            self.env['mail.mail'].sudo().create({
                'subject': f'[Evaluation] Course {dev_label}',
                'body_html': f'''
                    <p>Hello <strong>{self.employee_id.name}</strong>,</p>
                    <p>Congratulations on completing the <strong>{dev_label}</strong> program.</p>
                    <p>Please take a moment to evaluate the course.</p>
                    <p><a href="{schedule_url}" style="background-color: #875A7B; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">Evaluate Now</a></p>
                ''',
                'email_to': self.employee_id.work_email,
            }).send()
            
        self.message_post(body=_('Sent evaluation request emails to L&D and Employee (Link Portal).'))
    
    def action_submit_feedback(self):
        """Kiểm tra nếu cả 2 đã feedback thì hoàn thành"""
        if self.lnd_feedback_status == 'done' and self.employee_feedback_status == 'done':
            self.write({'state': 'done'})
            # Apply promotion only when done
            self._apply_promotion()
            self.message_post(body=_('All evaluations completed. Process finished!'))
    
    def action_cancel(self):
        """Hủy chương trình"""
        self.write({'state': 'cancelled'})
        self.message_post(body=_('Program has been cancelled.'))
        
    def _send_course_2_invitation_email(self):
        """Gửi email mời nhân viên tham gia khoá học 2"""
        self.ensure_one()
        
        if not self.employee_id.work_email:
            self.message_post(body=_('Employee has no email. Cannot send Course 2 invitation.'))
            return

        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        # Use portal URL
        schedule_url = f"{base_url}/my/manager/schedule/{self.id}"
        
        self.message_post(body=_('Sending email inviting employee to Course 2: %s') % self.course_2_name)
        
        try:
            self.env['mail.mail'].sudo().create({
                'subject': f'Invitation to Course: {self.course_2_name}',
                'body_html': f'''
                    <p>Hello <strong>{self.employee_id.name}</strong>,</p>
                    <p>Congratulations on completing Course 1 and being rated PASS.</p>
                    <p>Next, you are invited to join the course:</p>
                    <h3 style="color: #875A7B;">{self.course_2_name}</h3>
                    <p>Please arrange time to participate and confirm completion on the system after finishing.</p>
                    <p style="margin: 20px 0;">
                        <a href="{schedule_url}" 
                           style="background-color: #875A7B; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">
                            Access System
                        </a>
                    </p>
                    <p>Best regards,<br/>L&D Team</p>
                ''',
                'email_to': self.employee_id.work_email,
                'auto_delete': True,
            }).send(raise_exception=False)
            self.message_post(body=_('Sent Course 2 invitation email to employee.'))
        except Exception as e:
            self.message_post(body=_('Error sending Course 2 invitation email: %s') % str(e))
        
    def action_reset_draft(self):
        """Reset to draft"""
        self.write({'state': 'draft'})
    
    def _send_oc_notification_email(self):
        """Gửi email thông báo cho OC (manager của RGM) về việc cần đánh giá"""
        self.ensure_one()
        
        # Log debug
        self.message_post(body=_('Attempting to send email to OC...'))
        
        # OC được xác định trên form, nếu không có thì lấy Manager của RGM
        oc = self.oc_id or self.proposed_by_id.parent_id
        
        if not oc:
             self.message_post(body=_('OC (Manager of RGM) info not found. Please check employee configuration (proposer).'))
             return False
             
        if not oc.work_email:
            self.message_post(body=_('OC %s has no work email. Cannot send notification.') % oc.name)
            return False
            
        self.message_post(body=_('Found OC: %s (Email: %s). Creating email...') % (oc.name, oc.work_email))
        
        # Get base URL
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        # Use portal URL - OC might be partial internal/portal, safer to use Portal URL if they have user access
        schedule_url = f"{base_url}/my/manager/schedule/{self.id}"
        
        dev_label = dict(self._fields['development_type'].selection).get(self.development_type, self.development_type)
        
        mail_values = {
            'subject': f'[Action Required] Development Program {dev_label} - {self.employee_id.name}',
            'body_html': f'''
                <p>Hello <strong>{oc.name}</strong>,</p>
                <p>Employee <strong>{self.employee_id.name}</strong> has completed the courses and needs evaluation.</p>
                <p><strong>Details:</strong></p>
                <ul>
                    <li><strong>Employee:</strong> {self.employee_id.name}</li>
                    <li><strong>Program:</strong> {dev_label}</li>
                    <li><strong>Proposer (RGM):</strong> {self.proposed_by_id.name}</li>
                    <li><strong>Course 1:</strong> {self.course_1_name} ✅</li>
                    <li><strong>Course 2:</strong> {self.course_2_name} ✅</li>
                </ul>
                <p style="margin: 20px 0;">
                    <a href="{schedule_url}" 
                       style="background-color: #875A7B; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; display: inline-block;">
                        View and Evaluate
                    </a>
                </p>
                <p>Please evaluate to complete the process.</p>
                <p>Best regards,<br/>L&D Team</p>
            ''',
            'email_to': oc.work_email,
            'auto_delete': True,
        }
        
        try:
            mail = self.env['mail.mail'].sudo().create(mail_values)
            mail.send(raise_exception=False)
            self.message_post(body=_('Successfully sent notification email to OC: %s') % oc.work_email)
        except Exception as e:
            self.message_post(body=_('Exception sending OC email: %s') % str(e))
        
        return True

    # Access rights for feedback
    can_evaluate_lnd = fields.Boolean(compute='_compute_access_rights')
    can_evaluate_employee = fields.Boolean(compute='_compute_access_rights')

    @api.depends_context('uid')
    def _compute_access_rights(self):
        is_admin = self.env.is_admin()
        user = self.env.user
        
        # Check if user belongs to L&D department
        is_lnd = is_admin
        if not is_lnd and user.employee_id:
            # Check department name of the user's employee
            if user.employee_id.department_id.name and 'L&D' in user.employee_id.department_id.name:
                is_lnd = True
                
        for record in self:
            # L&D check
            record.can_evaluate_lnd = is_lnd
            
            # Employee check: Admin or the employee themselves
            if is_admin:
                record.can_evaluate_employee = True
            elif user.employee_id and user.employee_id == record.employee_id:
                record.can_evaluate_employee = True
            else:
                record.can_evaluate_employee = False

    def submit_feedback(self, feedback_type, content, rating=None):
        """Submit feedback from wizard"""
        self.ensure_one()
        
        # Enforce access rights
        if feedback_type == 'lnd' and not self.can_evaluate_lnd:
            raise ValidationError(_('You are not authorized to perform L&D evaluation. Only L&D staff or Admin allowed.'))
            
        if feedback_type == 'employee' and not self.can_evaluate_employee:
            raise ValidationError(_('You are not authorized to perform evaluation for this employee. Only %s or Admin allowed.') % self.employee_id.name)

        if feedback_type == 'lnd':
            self.write({
                'lnd_feedback': content,
                'lnd_feedback_status': 'done'
            })
            self.message_post(body=_('L&D has evaluated training effectiveness.'))
        elif feedback_type == 'employee':
            self.write({
                'employee_feedback': content,
                'employee_feedback_status': 'done'
            })
            self.message_post(body=_('Employee submitted course evaluation.'))
            
        # Check completion
        self.action_submit_feedback()
