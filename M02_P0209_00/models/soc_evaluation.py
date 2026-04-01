from odoo import models, fields, api
from odoo.exceptions import ValidationError

class SocEvaluation(models.Model):
    _name = 'mcd.soc.evaluation'
    _description = 'B10: SOC Evaluation Session'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date_evaluation desc, id desc'

    name = fields.Char(string='Reference', required=True, copy=False, readonly=True, default=lambda self: 'New')
    
    # 1. Participants
    employee_id = fields.Many2one('hr.employee', string='Trainee', required=True, tracking=True)
    trainer_id = fields.Many2one('hr.employee', string='Trainer', required=True, tracking=True, default=lambda self: self.env.user.employee_id)
    
    # 2. Content
    soc_id = fields.Many2one('slide.slide', string='SOC', required=True, domain=[('is_soc', '=', True)])
    channel_id = fields.Many2one('slide.channel', related='soc_id.channel_id', string='Course', readonly=True)
    
    # 3. Session Info
    date_evaluation = fields.Date(string='Date', default=fields.Date.context_today)
    
    # 4. Scoring
    line_ids = fields.One2many('mcd.soc.evaluation.line', 'evaluation_id', string='Checklist')
    score_achieved = fields.Float(string='Score (%)', compute='_compute_score', store=True, tracking=True)
    result = fields.Selection([
        ('pass', 'Pass'),
        ('fail', 'Fail')
    ], string='Result', compute='_compute_result', store=True, tracking=True)
    
    state = fields.Selection([
        ('draft', 'Draft'),
        ('in_progress', 'In Progress'),
        ('done', 'Completed'),
        ('cancel', 'Cancelled')
    ], string='Status', default='draft', tracking=True)

    @api.constrains('employee_id', 'trainer_id')
    def _check_evaluation_rules(self):
        for rec in self:
            if not rec.employee_id or not rec.trainer_id:
                continue
            
            # 1. Same Department Check (User Request)
            # Only check if BOTH have departments assigned
            trainer = rec.trainer_id
            if trainer.department_id and rec.employee_id.department_id:
                if trainer.department_id != rec.employee_id.department_id:
                    raise ValidationError(f"Bạn chỉ có thể đánh giá nhân viên cùng phòng ban ({trainer.department_id.name}). Nhân viên {rec.employee_id.name} thuộc {rec.employee_id.department_id.name}.")

            # 2. Cannot evaluate own Manager Check (User Request)
            # If the Trainee is the Manager of the Trainer
            if trainer.parent_id == rec.employee_id:
                raise ValidationError("Bạn không thể đánh giá quản lý trực tiếp của mình!")

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('mcd.soc.evaluation') or 'New'
        return super(SocEvaluation, self).create(vals_list)

    @api.depends('line_ids.is_checked', 'line_ids.is_critical')
    def _compute_score(self):
        for record in self:
            total_items = len(record.line_ids)
            if total_items == 0:
                record.score_achieved = 0.0
                continue
            
            checked_items = len(record.line_ids.filtered(lambda l: l.is_checked))
            record.score_achieved = (checked_items / total_items) * 100.0

    @api.depends('score_achieved', 'line_ids.is_critical', 'line_ids.is_checked')
    def _compute_result(self):
        for record in self:
            # 1. Critical Factor Check (K.O)
            # If ANY critical item is NOT checked -> Fail
            failed_critical = record.line_ids.filtered(lambda l: l.is_critical and not l.is_checked)
            if failed_critical:
                record.result = 'fail'
                continue
            
            # 2. Score Check
            # Assuming 100% required? Or soc_id.pass_score?
            # User requirement: "No -> B5". Usually strict SOC requires 100% or very high.
            # Let's use SOC's configured pass_score or 100% default.
            required_score = record.soc_id.pass_score or 100.0
            if record.score_achieved >= required_score:
                record.result = 'pass'
            else:
                record.result = 'fail'

    @api.onchange('soc_id')
    def _onchange_soc_id(self):
        """Auto-populate checklist from SOC Template"""
        if not self.soc_id:
            self.line_ids = False
            return
        
        lines = []
        for item in self.soc_id.soc_item_ids:
            lines.append((0, 0, {
                'soc_item_id': item.id,
                'name': item.name,
                'section_id': item.section_id.id,
                'is_critical': item.is_critical,
                'sequence': item.sequence,
            }))
        self.line_ids = lines

    def action_confirm_start(self):
        self.state = 'in_progress'

    def action_submit_evaluation(self):
        self.ensure_one()
        self.state = 'done'
        
        # CHỈ CẤP CHỨNG CHỈ KHI ĐẠT 100%
        if self.result == 'pass' and self.score_achieved >= 100.0:
            # B11 Trigger: Update eLearning Progress
            # Find the slide.slide.partner record
            user = self.employee_id.user_id
            if user:
                slide_partner = self.env['slide.slide.partner'].search([
                    ('slide_id', '=', self.soc_id.id),
                    ('partner_id', '=', user.partner_id.id)
                ], limit=1)
                
                if not slide_partner:
                    slide_partner = self.env['slide.slide.partner'].create({
                        'slide_id': self.soc_id.id,
                        'partner_id': user.partner_id.id,
                        'channel_id': self.soc_id.channel_id.id
                    })
                
                # Mark as Completed -> This triggers _grant_soc_skill in soc_skill_automation.py
                slide_partner.write({'completed': True})
                
                # Grant skill directly to ensure it's saved to Skills & Certifications
                if self.soc_id.soc_skill_id and self.soc_id.soc_skill_level_id:
                    self.soc_id.grant_soc_skill_to_employee(self.employee_id)
                
                self.message_post(body="SOC Passed 100%! Training record updated and Skills granted to Skills & Certifications.")
            else:
                self.message_post(body="WARNING: Trainee has no User account. Skill not auto-granted.")
        elif self.result == 'pass':
            self.message_post(body=f"SOC Passed ({self.score_achieved}%) but not 100%. Certificate not granted. Please retake to achieve 100%.")
        else:
            self.message_post(body="SOC Failed. Please schedule retraining (B5).")
    
    @api.model
    def get_soc_status_for_employee(self, employee_id):
        """
        Tính trạng thái SOC cho một nhân viên theo cấu trúc phân cấp:
        - Area -> Station -> SOC
        - SOC pass nếu có evaluation done với result='pass' và score=100%
        - Station pass nếu TẤT CẢ SOC trong Station đều pass
        - Area pass nếu TẤT CẢ Station trong Area đều pass
        
        Returns:
            {
                'area_name': {
                    'status': 'pass'|'fail'|'partial'|'none',
                    'stations': {
                        'station_name': {
                            'status': 'pass'|'fail'|'partial'|'none',
                            'socs': [
                                {'id': soc_id, 'name': soc_name, 'code': soc_code, 'status': 'pass'|'fail'|'none'}
                            ]
                        }
                    }
                }
            }
        """
        employee = self.env['hr.employee'].browse(employee_id)
        if not employee.exists():
            return {}
        
        # Lấy tất cả SOCs
        all_socs = self.env['slide.slide'].search([
            ('is_soc', '=', True),
            ('is_published', '=', True),
            ('channel_id.is_published', '=', True)
        ], order='soc_area, soc_sub_area, sequence')
        
        # Lấy tất cả evaluations done của nhân viên này
        evaluations = self.search([
            ('employee_id', '=', employee_id),
            ('state', '=', 'done')
        ])
        soc_eval_map = {eval.soc_id.id: eval for eval in evaluations}
        
        # Build hierarchy
        Slide = self.env['slide.slide']
        area_labels = dict(Slide._fields['soc_area'].selection or [])
        station_labels = dict(Slide._fields['soc_sub_area'].selection or [])
        
        hierarchy = {}
        
        for soc in all_socs:
            area_key = soc.soc_area or 'other'
            station_key = soc.soc_sub_area or 'other'
            
            area_label = area_labels.get(area_key, area_key)
            station_label = station_labels.get(station_key, station_key)
            
            # Xác định trạng thái SOC
            eval_record = soc_eval_map.get(soc.id)
            if eval_record and eval_record.result == 'pass' and eval_record.score_achieved >= 100.0:
                soc_status = 'pass'
            elif eval_record:
                soc_status = 'fail'
            else:
                soc_status = 'none'
            
            if area_label not in hierarchy:
                hierarchy[area_label] = {
                    'status': 'none',
                    'stations': {}
                }
            
            if station_label not in hierarchy[area_label]['stations']:
                hierarchy[area_label]['stations'][station_label] = {
                    'status': 'none',
                    'socs': []
                }
            
            hierarchy[area_label]['stations'][station_label]['socs'].append({
                'id': soc.id,
                'name': soc.name,
                'code': soc.soc_code or '',
                'status': soc_status
            })
        
        # Tính trạng thái Station và Area
        for area_name, area_data in hierarchy.items():
            station_statuses = []
            for station_name, station_data in area_data['stations'].items():
                soc_statuses = [soc['status'] for soc in station_data['socs']]
                if all(s == 'pass' for s in soc_statuses) and soc_statuses:
                    station_data['status'] = 'pass'
                elif any(s == 'pass' for s in soc_statuses):
                    station_data['status'] = 'partial'
                elif any(s == 'fail' for s in soc_statuses):
                    station_data['status'] = 'fail'
                else:
                    station_data['status'] = 'none'
                station_statuses.append(station_data['status'])
            
            # Tính trạng thái Area
            if all(s == 'pass' for s in station_statuses) and station_statuses:
                area_data['status'] = 'pass'
            elif any(s == 'pass' for s in station_statuses):
                area_data['status'] = 'partial'
            elif any(s == 'fail' for s in station_statuses):
                area_data['status'] = 'fail'
            else:
                area_data['status'] = 'none'
        
        return hierarchy
    
    hierarchy_data = fields.Text(string='Hierarchy Data', compute='_compute_hierarchy_data', store=False)
    hierarchy_html = fields.Html(string='Hierarchy HTML', compute='_compute_hierarchy_html')
    
    @api.depends('employee_id')
    def _compute_hierarchy_html(self):
        for record in self:
            record.hierarchy_html = record.render_hierarchy_html()
    
    @api.model
    def default_get(self, fields_list):
        """Set default employee_id from current user"""
        res = super(SocEvaluation, self).default_get(fields_list)
        if 'employee_id' in fields_list and not res.get('employee_id'):
            user = self.env.user
            if user.employee_id:
                res['employee_id'] = user.employee_id.id
        return res
    
    @api.depends('employee_id')
    def _compute_hierarchy_data(self):
        """Compute hierarchy data for current employee"""
        import json
        for record in self:
            if record.employee_id:
                hierarchy = self.get_soc_status_for_employee(record.employee_id.id)
                # Convert to list format for template
                hierarchy_list = []
                for area_name, area_data in hierarchy.items():
                    stations_list = []
                    for station_name, station_data in area_data['stations'].items():
                        stations_list.append({
                            'name': station_name,
                            'status': station_data['status'],
                            'socs': station_data['socs']
                        })
                    hierarchy_list.append({
                        'name': area_name,
                        'status': area_data['status'],
                        'stations': stations_list
                    })
                record.hierarchy_data = json.dumps(hierarchy_list)
            else:
                record.hierarchy_data = '[]'
    
    def render_hierarchy_html(self):
        """Render hierarchy HTML for view"""
        self.ensure_one()
        if not self.employee_id:
            return '<p>No employee selected.</p>'
        
        hierarchy = self.get_soc_status_for_employee(self.employee_id.id)
        html_parts = []
        
        for area_name, area_data in sorted(hierarchy.items()):
            status = area_data['status']
            status_class = {'pass': 'success', 'fail': 'danger', 'partial': 'warning'}.get(status, 'secondary')
            status_text = {'pass': '✓ Pass', 'fail': '✗ Fail', 'partial': '⚠ Partial'}.get(status, '○ Not Started')
            
            html_parts.append(f'''
                <div class="card mb-3">
                    <div class="card-header bg-{status_class}">
                        <h5 class="mb-0">
                            <i class="fa fa-folder me-2"></i>
                            {area_name}
                            <span class="badge bg-white text-dark ms-2">{status_text}</span>
                        </h5>
                    </div>
                    <div class="card-body">
            ''')
            
            for station_name, station_data in sorted(area_data['stations'].items()):
                station_status = station_data['status']
                station_class = {'pass': 'success', 'fail': 'danger', 'partial': 'warning'}.get(station_status, 'secondary')
                station_text = {'pass': '✓ Pass', 'fail': '✗ Fail', 'partial': '⚠ Partial'}.get(station_status, '○ Not Started')
                
                html_parts.append(f'''
                    <div class="mb-3 border-start border-3 ps-3 border-{station_class}">
                        <h6 class="mb-2">
                            <i class="fa fa-map-marker me-2"></i>
                            {station_name}
                            <span class="badge ms-2 bg-{station_class}">{station_text}</span>
                        </h6>
                        <ul class="list-unstyled ms-4">
                ''')
                
                for soc in sorted(station_data['socs'], key=lambda x: x['code'] or ''):
                    soc_status = soc['status']
                    soc_class = {'pass': 'success', 'fail': 'danger'}.get(soc_status, 'secondary')
                    soc_text = {'pass': '✓ Pass', 'fail': '✗ Fail'}.get(soc_status, '○ Not Started')
                    
                    html_parts.append(f'''
                        <li class="mb-1">
                            <i class="fa fa-file me-2"></i>
                            <strong>{soc['code']}</strong>: {soc['name']}
                            <span class="badge ms-2 bg-{soc_class}">{soc_text}</span>
                        </li>
                    ''')
                
                html_parts.append('</ul></div>')
            
            html_parts.append('</div></div>')
        
        return ''.join(html_parts) if html_parts else '<p>No SOC data available.</p>'
    
    def action_open_check_soc(self):
        """Open SOC Check page"""
        # Allow calling without record (from menu)
        if not self:
            employee = self.env.user.employee_id
            if not employee:
                raise ValidationError("No employee linked to your user account.")
            return {
                'type': 'ir.actions.act_url',
                'url': f'/soc/check/{employee.id}',
                'target': 'new',
            }
        
        self.ensure_one()
        employee_id = self.employee_id.id if self.employee_id else (self.env.user.employee_id.id if self.env.user.employee_id else False)
        if not employee_id:
            raise ValidationError("No employee selected or linked to your user account.")
        return {
            'type': 'ir.actions.act_url',
            'url': f'/soc/check/{employee_id}',
            'target': 'new',
        }

class SocEvaluationLine(models.Model):
    _name = 'mcd.soc.evaluation.line'
    _description = 'B10: Checklist Result'
    _order = 'sequence, id'
    
    evaluation_id = fields.Many2one('mcd.soc.evaluation', string='Evaluation', ondelete='cascade')
    soc_item_id = fields.Many2one('mcd.soc.item', string='Template Item')
    
    sequence = fields.Integer(default=10)
    section_id = fields.Many2one('mcd.soc.section', string='Section')
    name = fields.Text(string='Description', required=True)
    is_critical = fields.Boolean(string='Critical (K.O)')
    
    is_checked = fields.Boolean(string='Pass?')
    comment = fields.Text(string='Trainer Comment')
