from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from datetime import date, timedelta

class ManagerProposalWizard(models.TransientModel):
    _name = 'mcd.manager.proposal.wizard'
    _description = 'Manager Development Proposal Wizard'

    employee_id = fields.Many2one('hr.employee', string='Employee', required=True, readonly=True)
    employee_job = fields.Char(related='employee_id.job_id.name', string='Current Job Position')
    employee_soc_count = fields.Char(related='employee_id.soc_progress_display', string='SOC Completed')
    
    # Available options based on employee's current level
    available_development_types = fields.Char(compute='_compute_available_development_types')
    
    # To enforce "No Choice" UI when only 1 option is available
    is_single_option = fields.Boolean(compute='_compute_is_single_option', store=False)

    development_type = fields.Selection([
        ('shift_manager', 'Develop to Shift Manager'),
        ('dm1', 'Develop to DM1'),
        ('dm2', 'Develop to DM2'),
        ('rgm', 'Develop to RGM'),
    ], string='Development Type', required=True)
    
    schedule_date = fields.Date(string='Start Date', required=True,
                                 help='Can only select from next Monday onwards')
    schedule_end_date = fields.Date(string='End Date')
    content = fields.Html(string='Schedule Content', required=True,
                          default="""
<p>Hello <strong>[Employee Name]</strong>,</p>

<p>You have been nominated to participate in the <strong>Shift Manager Development Program</strong>.</p>

<h4>Course 1 Information:</h4>
<ul>
    <li><strong>Course Name:</strong> [Course 1 Name]</li>
    <li><strong>Time:</strong> [Start Date] - [End Date]</li>
    <li><strong>Format:</strong> E-Learning on the system</li>
</ul>

<h4>Requirements:</h4>
<ul>
    <li>Complete 100% of course content</li>
    <li>Achieve minimum score in the final exam</li>
    <li>Completion deadline: Within 1 week from start date</li>
</ul>

<h4>Note:</h4>
<ul>
    <li>After completing this Course, you will be evaluated by the RGM</li>
    <li>If you pass, you will proceed to the next Course</li>
    <li>Please contact your direct manager if you have any questions</li>
</ul>

<p>Wishing you a successful completion of the program!</p>
<p><em>L&D Team</em></p>
""")

    @api.depends('available_development_types')
    def _compute_is_single_option(self):
        for wizard in self:
            options = (wizard.available_development_types or '').split(',')
            # Filter empty strings
            options = [o for o in options if o]
            wizard.is_single_option = len(options) <= 1

    @api.depends('employee_id')
    def _compute_available_development_types(self):
        """Compute which development types are available based on employee's current level"""
        for wizard in self:
            options = wizard._get_available_options()
            wizard.available_development_types = ','.join(options)
            
            # Auto-select if only one option or if current selection is invalid
            if options:
                if len(options) == 1:
                    wizard.development_type = options[0]
                elif wizard.development_type not in options:
                    wizard.development_type = options[0]

    def _get_available_options(self):
        """Get list of available development type options based on employee's current job and history"""
        self.ensure_one()
        if not self.employee_id:
            return ['shift_manager']
        
        # Check Contract Type (Part-time employees cannot develop)
        if hasattr(self.employee_id, 'is_part_time') and self.employee_id.is_part_time:
             return []
        
        job_name = (self.employee_id.job_id.name or '').lower()
        
        # Refactored to use Group checks (User Request)
        user = self.employee_id.user_id
        is_rgm_group = user.has_group('M02_P0209_00.group_rgm') if user else False
        is_dm2_group = user.has_group('M02_P0209_00.group_dm2') if user else False
        is_dm1_group = user.has_group('M02_P0209_00.group_dm1') if user else False
        is_sm_group = user.has_group('M02_P0209_00.group_sm') if user else False
        
        # Prioritize group checks
        # Only fallback to job name if NO relevant groups are found (backward compatibility)
        if is_rgm_group:
            is_rgm = True
            is_dm = True
            is_sm = True
        elif is_dm2_group or is_dm1_group:
            is_rgm = False
            is_dm = True
            is_sm = True
        elif is_sm_group:
             is_rgm = False
             is_dm = False
             is_sm = True
        else:
             # Fallback to string matching if no groups found
             is_rgm = 'rgm' in job_name or 'restaurant general manager' in job_name
             is_dm = 'dm1' in job_name or 'dm2' in job_name or 'department manager' in job_name
             is_sm = 'sm' in job_name or 'shift manager' in job_name
        
        if is_rgm:
             if passed_dm1 and passed_dm2:
                return ['rgm']
             else:
                passed_dm1 = self._check_passed_program('dm1')
                passed_dm2 = self._check_passed_program('dm2')
                
                if passed_dm1 and passed_dm2:
                    return ['rgm']
                else:
                    options = []
                    if not passed_dm1:
                        options.append('dm1')
                    if not passed_dm2:
                        options.append('dm2')
                    return options if options else ['rgm']

        elif is_dm:
            passed_dm1 = self._check_passed_program('dm1')
            passed_dm2 = self._check_passed_program('dm2')
            
            if passed_dm1 and passed_dm2:
                return ['rgm']
            else:
                options = []
                if not passed_dm1:
                    options.append('dm1')
                if not passed_dm2:
                    options.append('dm2')
                return options if options else ['rgm']
        elif is_sm:
            # SM can develop to DM1 or DM2
            return ['dm1', 'dm2']
        else:
            # Crew, Trainer, etc -> only Shift Manager
            return ['shift_manager']
    
    def _check_passed_program(self, program_type):
        """Check if employee has completed a development program of given type"""
        self.ensure_one()
        passed_schedule = self.env['mcd.manager.schedule'].search([
            ('employee_id', '=', self.employee_id.id),
            ('development_type', '=', program_type),
            ('state', '=', 'done')
        ], limit=1)
        return bool(passed_schedule)

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        
        # Auto-fill employee from context
        employee_id = self.env.context.get('default_employee_id')
        if employee_id and 'employee_id' in fields_list:
            res['employee_id'] = employee_id
            
            # Auto-determine development_type based on available options
            # We use a temporary record to calculate options
            temp = self.new({'employee_id': employee_id})
            available = temp._get_available_options()
            if available:
                res['available_development_types'] = ','.join(available)
                res['development_type'] = available[0]
                res['is_single_option'] = len(available) <= 1
        
        # Default schedule_date to next Monday
        if 'schedule_date' in fields_list:
            today = date.today()
            days_until_monday = (7 - today.weekday()) % 7
            if days_until_monday == 0:
                days_until_monday = 7  # Next week's Monday
            next_monday = today + timedelta(days=days_until_monday)
            res['schedule_date'] = next_monday
            
            # Calculate end date (Friday of the same week)
            schedule_end = next_monday + timedelta(days=4)
            res['schedule_end_date'] = schedule_end
        
        # Generate dynamic email content
        if 'content' in fields_list and employee_id:
            employee = self.env['hr.employee'].browse(employee_id)
            dev_type = res.get('development_type', 'shift_manager')
            
            # Get development type label
            dev_labels = {
                'shift_manager': 'Develop to Shift Manager',
                'dm1': 'Develop to DM1',
                'dm2': 'Develop to DM2',
                'rgm': 'Develop to RGM',
            }
            dev_label = dev_labels.get(dev_type, 'Manager Development')
            
            course_1 = ''
            has_config = False
            config = self.env['mcd.development.config'].search([
                ('development_type', '=', dev_type),
                ('active', '=', True),
                '|', ('company_id', '=', self.env.company.id), ('company_id', '=', False)
            ], limit=1, order='company_id desc')
            
            if config and config.course_line_ids:
                lines = config.course_line_ids.sorted('sequence')
                course_1 = lines[0].course_name if len(lines) > 0 else ''
                has_config = True
            
            # Format dates
            start_date = res.get('schedule_date', date.today())
            end_date = res.get('schedule_end_date', start_date + timedelta(days=4))
            start_str = start_date.strftime('%d/%m/%Y')
            end_str = end_date.strftime('%d/%m/%Y')
            
            # Generate content based on whether config exists
            if has_config:
                res['content'] = f"""
<p>Hello <strong>{employee.name}</strong>,</p>

<p>You have been nominated to participate in <strong>{dev_label}</strong>.</p>

<h4>Course 1 Information:</h4>
<ul>
    <li><strong>Course Name:</strong> {course_1}</li>
    <li><strong>Time:</strong> {start_str} - {end_str}</li>
    <li><strong>Format:</strong> E-Learning on the system</li>
</ul>

<h4>Requirements:</h4>
<ul>
    <li>Complete 100% of course content</li>
    <li>Achieve minimum score in the final exam</li>
    <li>Completion deadline: Within 1 week from start date</li>
</ul>

<h4>Note:</h4>
<ul>
    <li>After completing this Course, you will be evaluated by the RGM</li>
    <li>If you pass, you will proceed to the next Course</li>
    <li>Please contact your direct manager if you have any questions</li>
</ul>

<p>Wishing you a successful completion of the program!</p>
<p><em>L&D Team</em></p>
"""
            else:
                res['content'] = f"""
<p>Hello <strong>{employee.name}</strong>,</p>

<p>You have been nominated to participate in <strong>{dev_label}</strong>.</p>

<div style="background-color: #fff3cd; border: 1px solid #ffc107; padding: 15px; border-radius: 5px; margin: 15px 0;">
    <strong>⚠️ No courses configured for this program!</strong>
    <p style="margin: 10px 0 0 0;">Please contact L&D department to configure courses before proceeding.</p>
</div>

<p><strong>Expected Schedule:</strong> {start_str} - {end_str}</p>

<p><em>L&D Team</em></p>
"""
        
        return res
    
    @api.constrains('development_type')
    def _check_development_type_allowed(self):
        """Validate that selected development type is allowed for this employee"""
        for wizard in self:
            available = wizard._get_available_options()
            # Handle empty available (e.g. part time)
            if not available:
                 raise ValidationError(_('Employee is not eligible for any development program (e.g. Part-time).'))

            if wizard.development_type not in available:
                raise ValidationError(
                    _('Development type "%s" not available for this employee. Valid options: %s') % (
                        wizard._get_development_type_label(),
                        ', '.join([dict(wizard._fields['development_type'].selection).get(opt, opt) for opt in available])
                    )
                )

    @api.constrains('schedule_date')
    def _check_schedule_date(self):
        """Validate that schedule_date is at least next week's Monday"""
        for wizard in self:
            if wizard.schedule_date:
                today = date.today()
                # Calculate next Monday
                days_until_monday = (7 - today.weekday()) % 7
                if days_until_monday == 0:
                    days_until_monday = 7  # Must be at least next Monday
                next_monday = today + timedelta(days=days_until_monday)
                
                if wizard.schedule_date < next_monday:
                    raise ValidationError(
                        _('Start date must be from next Monday onwards (%s)!') % next_monday.strftime('%d/%m/%Y')
                    )

    @api.onchange('schedule_date')
    def _onchange_schedule_date(self):
        """Auto-set end date to Friday of the same week"""
        if self.schedule_date:
            # Set end date to Friday of the same week
            days_to_friday = 4 - self.schedule_date.weekday()
            if days_to_friday < 0:
                days_to_friday += 7
            self.schedule_end_date = self.schedule_date + timedelta(days=days_to_friday)

    def _get_development_type_label(self):
        """Get human-readable label for development type"""
        labels = dict(self._fields['development_type'].selection)
        return labels.get(self.development_type, self.development_type)

    def action_confirm_proposal(self):
        """Create the manager schedule, planning slot and send email"""
        self.ensure_one()
        
        # 1. Create manager schedule record and start B1
        schedule = self.env['mcd.manager.schedule'].create({
            'employee_id': self.employee_id.id,
            'schedule_date': self.schedule_date,
            'schedule_end_date': self.schedule_end_date,
            'content': self.content,
            'development_type': self.development_type,
            'state': 'b1_course',  # Bắt đầu ngay từ B1: Tham gia khoá học 1
        })
        
        # 2. Create planning slot for the employee
        self._create_planning_slot()
        
        # 3. Mark employee as manager trainee (if field exists)
        if hasattr(self.employee_id, 'is_manager_trainee'):
            self.employee_id.write({'is_manager_trainee': True})
        
        # 4. Send email notification to employee
        self._send_notification_email(schedule)
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Success'),
                'message': _('Created development schedule %s for %s and sent notification email!') % (
                    self._get_development_type_label(), self.employee_id.name
                ),
                'type': 'success',
                'sticky': False,
                'next': {'type': 'ir.actions.act_window_close'},
            }
        }

    def _create_planning_slot(self):
        """Create planning slot for the development program"""
        self.ensure_one()
        
        # Check if planning module is available
        if 'planning.slot' not in self.env:
            return False
        
        # Get development type label for slot name
        dev_label = self._get_development_type_label()
        
        # Create planning slot
        slot_vals = {
            'resource_id': self.employee_id.resource_id.id if self.employee_id.resource_id else False,
            'start_datetime': fields.Datetime.to_datetime(self.schedule_date),
            'end_datetime': fields.Datetime.to_datetime(self.schedule_end_date) if self.schedule_end_date else fields.Datetime.to_datetime(self.schedule_date),
            'name': f'Manager Development Program - {dev_label}',
        }
        
        # Remove empty values
        slot_vals = {k: v for k, v in slot_vals.items() if v}
        
        if slot_vals.get('resource_id'):
            try:
                self.env['planning.slot'].create(slot_vals)
            except Exception:
                pass  # Ignore errors if planning slot creation fails
        
        return True

    def _send_notification_email(self, schedule):
        """Send email notification to employee about the development program"""
        self.ensure_one()
        
        # Check if employee has email
        if not self.employee_id.work_email:
            return False
        
        dev_label = self._get_development_type_label()
        
        # Get base URL - use portal URL instead of backend
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        schedule_url = f"{base_url}/my/manager/schedule/{schedule.id}"
        
        # Create and send email
        mail_values = {
            'subject': f'Notification: Development Schedule {dev_label}',
            'body_html': f'''
                <p>Hello <strong>{self.employee_id.name}</strong>,</p>
                <p>You have been nominated to participate in the program <strong>{dev_label}</strong>.</p>
                <p><strong>Details:</strong></p>
                <ul>
                    <li><strong>Start Date:</strong> {self.schedule_date.strftime('%d/%m/%Y')}</li>
                    <li><strong>End Date:</strong> {self.schedule_end_date.strftime('%d/%m/%Y') if self.schedule_end_date else 'N/A'}</li>
                    <li><strong>Course 1:</strong> {schedule.course_1_name}</li>
                    <li><strong>Course 2:</strong> {schedule.course_2_name}</li>
                </ul>
                <p style="margin: 20px 0;">
                    <a href="{schedule_url}" 
                       style="background-color: #875A7B; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; display: inline-block;">
                        Join Course
                    </a>
                </p>
                <p><strong>Program Content:</strong></p>
                {self.content or ''}
                <p>Please contact your manager if you have any questions.</p>
                <p>Best regards,<br/>L&D Team</p>
            ''',
            'email_to': self.employee_id.work_email,
            'auto_delete': True,
        }
        
        try:
            self.env['mail.mail'].sudo().create(mail_values)
            # Async send is default behavior of create if not forced, but explicit .send() forces it.
            # We remove .send() to let it queue.
        except Exception:
            pass
        
        return True

