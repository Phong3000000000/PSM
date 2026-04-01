from odoo import models, fields, api
from odoo.exceptions import ValidationError

class Employee(models.Model):
    _inherit = 'hr.employee'

    # Sorting helper for Potential List
    is_trainer_job = fields.Boolean(
        compute='_compute_is_trainer_job',
        string='Is Trainer',
        store=True,
        help='True if job title contains "Trainer".'
    )
    
    @api.depends('job_id', 'job_id.name')
    def _compute_is_trainer_job(self):
        for employee in self:
            job_name = employee.job_id.name or ''
            employee.is_trainer_job = 'trainer' in job_name.lower()

    # Field to check if employee can receive new proposal
    can_propose_manager = fields.Boolean(
        compute='_compute_can_propose_manager',
        string='Can Propose Manager Development',
        help='True if no pending proposal exists or last proposal is done/cancelled.'
    )
    
    @api.depends('training_progress')
    def _compute_can_propose_manager(self):
        """Check if employee can receive new manager development proposal"""
        ManagerSchedule = self.env['mcd.manager.schedule']
        for employee in self:
            # Check if employee is already RGM
            job_name = employee.job_id.name or ''
            if 'RGM' in job_name or 'Restaurant General Manager' in job_name:
                employee.can_propose_manager = False
                continue

            # Must have 100% SOC completion
            if employee.training_progress < 100:
                employee.can_propose_manager = False
                continue
            
            # Check if there's any pending/confirmed proposal
            pending_schedule = ManagerSchedule.search([
                ('employee_id', '=', employee.id),
                ('state', 'in', ['draft', 'confirmed'])  # Not done yet
            ], limit=1)
            
            # Can propose only if no pending schedule exists
            employee.can_propose_manager = not bool(pending_schedule)

    def action_open_manager_proposal(self):
        """Open Manager Development Proposal Wizard"""
        self.ensure_one()
        
        # Validate: check if can propose
        if not self.can_propose_manager:
            from odoo.exceptions import UserError
            raise UserError('Nhân viên này đang có chương trình phát triển chưa hoàn thành. Vui lòng chờ OC đánh giá hoàn thành trước khi tạo đề xuất mới.')
        
        return {
            'type': 'ir.actions.act_window',
            'name': 'Đề xuất phát triển Manager',
            'res_model': 'mcd.manager.proposal.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_employee_id': self.id,
            }
        }

    # --- B12: Capacity Check Configuration ---
    current_station_id = fields.Many2one('mcd.soc.station', string='Current Station', help='The station the employee is currently being trained on.')

    # --- B5: Gap Analysis Fields ---
    missing_soc_ids = fields.Many2many(
        'slide.slide',
        compute='_compute_training_gaps',
        string='Missing Training (SOCs)',
        help='SOCs required by the Job Position but not yet passed.'
    )
    
    # B5 Improvement: Track recent failures explicitly
    recent_failure_soc_ids = fields.Many2many(
        'slide.slide',
        'employee_soc_failure_rel',
        'employee_id', 'slide_id',
        compute='_compute_training_gaps',
        string='Failed SOCs (Retake Required)',
        help='B5 Loop Logic: SOCs that were attempted but Failed.'
    )

    training_progress = fields.Float(
        compute='_compute_training_gaps',
        string='Total Path Progress (%)',
        store=True,
        help='Completion percentage of ALL required training for this job.'
    )

    # --- B12 - B17: Progression Logic ---
    station_progress = fields.Float(
        compute='_compute_training_gaps',
        string='Current Station Progress (%)',
        help='Completion percentage of the CURRENT STATION.'
    )

    soc_completed_count = fields.Integer(
        compute='_compute_training_gaps',
        string='SOCs Completed',
        store=True,
        help='Number of SOCs completed (Passed).'
    )
    
    soc_total_count = fields.Integer(
        compute='_compute_training_gaps',
        string='Total SOCs Required',
        help='Total number of SOCs required for this job.'
    )
    
    soc_progress_display = fields.Char(
        compute='_compute_training_gaps',
        string='SOC Progress',
        help='SOC completion displayed as X/Y format.'
    )

    is_station_fully_competent = fields.Boolean(
        compute='_compute_training_gaps',
        string='Station Full Capacity',
        help='True if 100% of SOCs in current station are passed.'
    )

    next_suggested_station_id = fields.Many2one('mcd.soc.station', 
        compute='_compute_training_gaps',
        string='Suggested Cross-Training (B13)',
        help='The next station recommended for cross-training if current station is full.'
    )
    
    is_path_completed = fields.Boolean(
        compute='_compute_training_gaps',
        string='Path Completed (B14)',
        store=True,
        help='True if ALL required training for the job is completed.'
    )

    is_manager_candidate = fields.Boolean(
        compute='_compute_training_gaps',
        string='Manager Candidate (B15)',
        help='Eligible for Manager Trainee program.'
    )
    
    # B16: RGM Approval
    is_manager_trainee = fields.Boolean(string='Manager Trainee (Approved)', readonly=True, tracking=True)

    @api.depends('job_id.course_ids', 'job_id.manager_course_ids', 'user_id', 'current_station_id', 'is_manager_trainee')
    def _compute_training_gaps(self):
        # Get ALL SOC templates in the system (once, for performance)
        all_soc_templates = self.env['slide.slide'].search([
            ('is_soc', '=', True),
            ('is_published', '=', True)
        ])
        total_socs_in_system = len(all_soc_templates)
        
        for employee in self:
            # Initialize default values
            employee.missing_soc_ids = False
            employee.recent_failure_soc_ids = False
            employee.training_progress = 0.0
            employee.station_progress = 0.0
            employee.soc_completed_count = 0
            employee.soc_total_count = total_socs_in_system
            employee.soc_progress_display = f'0/{total_socs_in_system}'
            employee.is_station_fully_competent = False
            employee.next_suggested_station_id = False
            employee.is_path_completed = False
            employee.is_manager_candidate = False

            # 1. Get SOCs PASSED by the employee (from evaluations)
            # Count SOCs where employee has a PASS evaluation (state=done, result=pass)
            passed_evals = self.env['mcd.soc.evaluation'].search([
                ('employee_id', '=', employee.id),
                ('state', '=', 'done'),
                ('result', '=', 'pass'),
                ('soc_id', 'in', all_soc_templates.ids)
            ])
            completed_slide_ids = passed_evals.mapped('soc_id')

            # 2. Calculate SOC progress (all SOCs in system)
            done_count = len(completed_slide_ids)
            employee.soc_completed_count = done_count
            employee.soc_total_count = total_socs_in_system
            employee.soc_progress_display = f"{done_count}/{total_socs_in_system}"
            employee.training_progress = (done_count / total_socs_in_system) * 100.0 if total_socs_in_system > 0 else 0.0

            # 3. Calculate Missing SOCs
            missing_slides = all_soc_templates - completed_slide_ids
            employee.missing_soc_ids = missing_slides
            
            # --- Check For Failed Attempts (Loop Logic) ---
            if missing_slides:
                failed_evals = self.env['mcd.soc.evaluation'].search([
                    ('employee_id', '=', employee.id),
                    ('soc_id', 'in', missing_slides.ids),
                    ('result', '=', 'fail')
                ])
                if failed_evals:
                     employee.recent_failure_soc_ids = failed_evals.mapped('soc_id')

            # 4. Path Completion Check
            if employee.training_progress >= 100.0:
                employee.is_path_completed = True
                employee.is_manager_candidate = True # B15 Trigger

            # 5. Station Logic (B12 & B13)
            if employee.current_station_id:
                # Filter SOCs for THIS station from all SOC templates
                station_required = all_soc_templates.filtered(lambda s: s.soc_station_id == employee.current_station_id)
                station_completed = completed_slide_ids.filtered(lambda s: s.soc_station_id == employee.current_station_id)
                
                s_total = len(station_required)
                s_done = len(station_completed)
                
                if s_total > 0:
                    employee.station_progress = (s_done / s_total) * 100.0
                else:
                    employee.station_progress = 100.0
                
                # B12 Check: Full Capacity?
                if employee.station_progress >= 100.0:
                    employee.is_station_fully_competent = True
                    
                    # B13: Suggestion Logic (Cross-training)
                    missing_areas = list(set(missing_slides.mapped('soc_station_id')))
                    potential_stations = [st for st in missing_areas if st and st != employee.current_station_id]
                    
                    if potential_stations:
                        employee.next_suggested_station_id = potential_stations[0]
    
    def action_approve_manager_training(self):
        """B16: RGM Approves Promotion to Manager Trainee"""
        self.ensure_one()
        if not self.is_manager_candidate:
            return
        
        self.is_manager_trainee = True
        self.message_post(body="B16: RGM Approved Promotion. User is now a Manager Trainee (B17 Workflow Activated).")

    def action_open_planning(self):
        """B6: Open Planning Module via URL (Safest Method)"""
        self.ensure_one()
        
        # Check if planning is installed
        if not self.env['ir.module.module'].search_count([('name', '=', 'planning'), ('state', '=', 'installed')]):
             raise ValidationError("Please install the 'Planning' app (Odoo Enterprise) to use the scheduling feature.")

        # Construct URL to bypass any server-side default actions/wizards
        # Target: /web#model=planning.slot&view_type=calendar
        url = "/web#model=planning.slot&view_type=calendar"
        
        return {
            'type': 'ir.actions.act_url',
            'url': url,
            'target': 'self', # Open in same tab
        }

    def action_assess_training_needs(self):
        """B5, B13, B15: Explicitly analyze training gaps and suggestions"""
        self.ensure_one()
        # Trigger re-computation (although for non-stored it happens on access, this ensures logic runs)
        self._compute_training_gaps()
        
        # Log Logic
        messages = []
        if self.missing_soc_ids:
            messages.append(f"Found {len(self.missing_soc_ids)} missing SOCs.")
        
        if self.recent_failure_soc_ids:
            messages.append("WARNING: Retraining required for failed SOCs.")
            
        if self.next_suggested_station_id:
            messages.append(f"Suggestion (B13): Cross-train at '{self.next_suggested_station_id.name}'.")
            
        if self.is_manager_candidate:
            messages.append("Suggestion (B15): Candidate is eligible for Manager Training.")
            
        if not messages:
            messages.append("All Good! Training path is on track.")
            
        # Post to Chatter
        self.message_post(body="<ul>" + "".join([f"<li>{m}</li>" for m in messages]) + "</ul>")
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Analysis Complete',
                'message': 'Training Needs Updated & Logged in Chatter.',
                'type': 'success',
                'sticky': False,
            }
        }

    # ====================================================
    # PORTAL HELPER: STATION / SOC STATUS
    # ====================================================
    def get_station_soc_status(self):
        """
        Returns structured data for Portal/UI display:
        Returns a list of dicts:
        [
            {
                'code': 'production',
                'name': 'Production',
                'status': 'completed', # 'completed', 'in_progress', 'pending'
                'socs': [
                    {'name': 'Grill', 'status': 'checked'}, # 'checked', 'unchecked'
                    ...
                ]
            },
            ...
        ]
        """
        self.ensure_one()
        result = []
        
        # 1. Get all SOCs relevant to this Employee's Job
        if not self.job_id:
            return []
            
        required_courses = self.job_id.course_ids
        # Include Manager courses if trainee
        if self.is_manager_trainee:
             required_courses |= self.job_id.manager_course_ids
             
        # Find SOC slides
        socs = self.env['slide.slide'].search([
            ('channel_id', 'in', required_courses.ids),
            ('is_soc', '=', True),
            ('is_published', '=', True),
             ('soc_station_id', '!=', False) # Must likely belong to a station
        ])
        
        # 2. Group by Station
        stations = {}
        
        # Get completed slides for this user
        completed_soc_ids = []
        if self.user_id:
             completed_soc_ids = self.env['slide.slide.partner'].sudo().search([
                ('slide_id', 'in', socs.ids),
                ('partner_id', '=', self.user_id.partner_id.id),
                ('completed', '=', True)
            ]).mapped('slide_id').ids

        for soc in socs:
            st = soc.soc_station_id
            st_code = st.code if st else 'other'
            st_name = st.name if st else 'Other'
            
            if st_code not in stations:
                stations[st_code] = {
                    'code': st_code,
                    'name': st_name,
                    'socs': [],
                    'total': 0,
                    'passed': 0
                }
            
            # Check status
            is_passed = soc.id in completed_soc_ids
            
            stations[st_code]['socs'].append({
                'id': soc.id,
                'name': soc.name,
                'status': 'checked' if is_passed else 'unchecked'
            })
            stations[st_code]['total'] += 1
            if is_passed:
                stations[st_code]['passed'] += 1
                
        # 3. Compute final station status and result list
        for st_code, data in stations.items():
            if data['passed'] == data['total'] and data['total'] > 0:
                data['status'] = 'completed'
            elif data['passed'] > 0:
                data['status'] = 'in_progress'
            else:
                data['status'] = 'pending'
            result.append(data)
            
        return result

    # ====================================================
    # BACKEND HELPER: STATION / SOC STATUS HTML
    # ====================================================
    soc_status_html = fields.Html(string='Station / SOC Status', compute='_compute_soc_status_html', sanitize=False)

    @api.depends('missing_soc_ids', 'user_id') # Trigger on gap analysis change
    def _compute_soc_status_html(self):
        for rec in self:
            try:
                data = rec.get_station_soc_status()
            except Exception:
                rec.soc_status_html = "<p>Error loading SOC data.</p>"
                continue

            if not data:
                rec.soc_status_html = '<p class="text-muted">No SOC Training Data found for this Job Position.</p>'
                continue

            html = """<div class="o_soc_status_container" style="padding: 10px;">"""
            
            for st in data:
                # Color logic
                bg_class = 'bg-success' if st['status'] == 'completed' else 'bg-warning' if st['status'] == 'in_progress' else 'bg-secondary'
                badge_text = 'Completed' if st['status'] == 'completed' else 'In Progress' if st['status'] == 'in_progress' else 'Pending'
                
                html += f"""
                <div class="mb-2 border rounded">
                    <div class="p-2 {bg_class} text-white d-flex justify-content-between align-items-center" 
                         onclick="this.nextElementSibling.classList.toggle('d-none');" style="cursor: pointer;">
                        <strong>{st['name']}</strong>
                        <span class="badge bg-white text-dark">{badge_text} ({st['passed']}/{st['total']})</span>
                    </div>
                    <div class="d-none bg-light p-2">
                        <ul class="list-unstyled mb-0">
                """
                
                for soc in st['socs']:
                    color = 'green' if soc['status'] == 'checked' else 'gray'
                    icon = 'fa-check-square-o' if soc['status'] == 'checked' else 'fa-square-o'
                    status_text = 'Passed' if soc['status'] == 'checked' else 'Pending'
                    
                    html += f"""
                            <li class="d-flex justify-content-between border-bottom py-1">
                                <span>{soc['name']}</span>
                                <span style="color: {color};">
                                    <i class="fa {icon}"></i> {status_text}
                                </span>
                            </li>
                    """
                html += """</ul></div></div>"""
            
            html += "</div>"
            rec.soc_status_html = html
