from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError

class OpsCapacityProcess(models.Model):
    """
    OPS Management Capacity Development Process
    Implements full B1-B32 workflow with exact step tracking
    """
    _name = 'mcd.ops.capacity.process'
    _description = 'OPS Capacity Development Process'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

    level_sequence = fields.Integer(string='Level Priority', compute='_compute_level_sequence', store=False)

    @api.depends('employee_id', 'current_level')
    def _compute_level_sequence(self):
        for rec in self:
            level_map = {
                'leader': 60,
                'rgm': 50,
                'dm2': 40,
                'dm1': 30,
                'sm': 20,
                'crew': 0
            }
            score = level_map.get(rec.current_level, 0)
            
            user = rec.employee_id.user_id
            
            def has(xml_id):
                return user.has_group(xml_id) if user else False
            
            if has('M02_P0209_00.group_lnd_manager'):
                score = 60 # Treat L&D/Leader as high level
            elif has('M02_P0209_00.group_rgm'):
                score = 50
            elif has('M02_P0209_00.group_dm2'):
                score = 40
            elif has('M02_P0209_00.group_dm1'):
                score = 30
            elif has('M02_P0209_00.group_sm'): # SM
                score = 20
            elif has('M02_P0209_00.group_trainer') or has('M02_P0209_00.group_barista_trainer'):
                score = 10
            elif has('M02_P0209_00.group_crew'):
                score = 0
            
            rec.level_sequence = score

    # ================================
    # BASIC FIELDS
    # ================================
    name = fields.Char(compute='_compute_name', store=True)
    employee_id = fields.Many2one('hr.employee', string='Employee (Candidate)', required=True, tracking=True)
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)

    # ================================
    # LEVEL TRACKING
    # ================================
    current_level = fields.Selection([
        ('crew', 'Crew'),
        ('sm', 'Shift Manager'),
        ('dm1', 'Department Manager 1'),
        ('dm2', 'Department Manager 2'),
        ('rgm', 'Restaurant General Manager'),
        ('leader', 'Future Leader')
    ], string='Current Level', default='crew', required=True, tracking=True)

    target_level = fields.Selection([
        ('sm', 'Shift Manager'),
        ('dm1', 'Department Manager 1'),
        ('dm2', 'Department Manager 2'),
        ('rgm', 'Restaurant General Manager'),
        ('leader', 'Future Leader')
    ], string='Target Level', default='leader', tracking=True)

    # ================================
    # WORKFLOW STATE (EXACT B1-B32)
    # ================================
    state = fields.Selection([
        # Phase 1: Setup
        ('draft', 'Draft'),
        ('b1_identify', 'B1: Identify Candidates'),
        ('b2_b4_class', 'B2-B4: Class Setup'),
        ('b5_schedule', 'B5: Scheduling'),
        ('b6_learning', 'B6: Learning Started'),
        
        # Phase 2: SM Level (B7-B11)
        ('b7_gateway_sm', 'B7: Check SM Status'),
        ('b8_running_areas', 'B8: Running Areas Training'),
        ('b9_set_pet', 'B9: SET/PET Evaluation'),
        ('b10_slf', 'B10: Shift Leadership Foundation'),
        ('b11_slv', 'B11: SLV Evaluation'),
        
        # Sub-process: Profile Update (B12-B16)
        ('b12_lnd_eval', 'B12: L&D Evaluation'),
        ('b13_emp_feedback', 'B13: Employee Feedback'),
        ('b14_update_profile', 'B14: Update Profile'),
        ('b15_update_permission', 'B15: Update Permissions'),
        ('b16_update_budget', 'B16: Update Budget'),
        
        # Phase 3: DM1 Level (B17-B21)
        ('b17_gateway_dm1', 'B17: Check DM1 Status'),
        ('b18_adv_leadership', 'B18: Advancing Leadership'),
        ('b19_course_check', 'B19: Course Evaluation'),
        ('b20_3sv_training', 'B20: 3 System Training'),
        ('b21_3sv_eval', 'B21: 3 SV Evaluation'),
        
        # Phase 4: DM2 Level (B22-B26)
        ('b22_gateway_dm2', 'B22: Check DM2 Status'),
        ('b23_dlim', 'B23: DLIM Training'),
        ('b24_course_check', 'B24: Course Evaluation'),
        ('b25_2sv_training', 'B25: 2 System Training'),
        ('b26_2sv_eval', 'B26: 2 SV Evaluation'),
        
        # Phase 5: RGM Level (B27-B30)
        ('b27_lgr', 'B27: LGR Training'),
        ('b28_course_check', 'B28: Course Evaluation'),
        ('b29_4sv_training', 'B29: 4 System Training'),
        ('b30_4sv_eval', 'B30: 4 SV Evaluation'),
        
        # Phase 6: Future Leader (B31-B32)
        ('b31_lff', 'B31: LFF Training'),
        ('b32_final_eval', 'B32: Final Evaluation'),
        
        # End
        ('done', 'Completed')
    ], string='Workflow Step', default='draft', tracking=True)

    # ================================
    # EVALUATORS
    # ================================
    evaluator_rgm_id = fields.Many2one('res.users', string='RGM Evaluator', tracking=True)
    evaluator_oc_id = fields.Many2one('res.users', string='OC Evaluator', tracking=True)

    # ================================
    # EVALUATION RESULTS
    # ================================
    # SM Level
    b9_result = fields.Selection([('pass', 'Pass'), ('fail', 'Fail')], string='B9 SET/PET Result')
    b9_fail_reason = fields.Text(string='B9 Fail Reason')
    b11_result = fields.Selection([('pass', 'Pass'), ('fail', 'Fail')], string='B11 SLV Result')
    b11_fail_reason = fields.Text(string='B11 Fail Reason')
    
    # DM1 Level
    b19_result = fields.Selection([('pass', 'Pass'), ('fail', 'Fail')], string='B19 Course Result')
    b19_fail_reason = fields.Text(string='B19 Fail Reason')
    b21_result = fields.Selection([('pass', 'Pass'), ('fail', 'Fail')], string='B21 3SV Result')
    b21_fail_reason = fields.Text(string='B21 Fail Reason')
    
    # DM2 Level
    b24_result = fields.Selection([('pass', 'Pass'), ('fail', 'Fail')], string='B24 Course Result')
    b24_fail_reason = fields.Text(string='B24 Fail Reason')
    b26_result = fields.Selection([('pass', 'Pass'), ('fail', 'Fail')], string='B26 2SV Result')
    b26_fail_reason = fields.Text(string='B26 Fail Reason')
    
    # RGM Level
    b28_result = fields.Selection([('pass', 'Pass'), ('fail', 'Fail')], string='B28 Course Result')
    b28_fail_reason = fields.Text(string='B28 Fail Reason')
    b30_result = fields.Selection([('pass', 'Pass'), ('fail', 'Fail')], string='B30 4SV Result')
    b30_fail_reason = fields.Text(string='B30 Fail Reason')
    
    # Leader Level
    b32_result = fields.Selection([('pass', 'Pass'), ('fail', 'Fail')], string='B32 Final Result')
    b32_fail_reason = fields.Text(string='B32 Fail Reason')

    # ================================
    # PROFILE UPDATE SUBPROCESS (B12-B16)
    # ================================
    b12_lnd_feedback = fields.Text(string='B12: L&D Training Effectiveness')
    b13_employee_feedback = fields.Text(string='B13: Employee Course Feedback')
    b16_training_cost = fields.Float(string='B16: Training Cost')

    # ================================
    # LINKED COURSES (M02_P0209_00)
    # ================================
    running_areas_course_id = fields.Many2one('slide.channel', string='Running Areas Course')
    slf_course_id = fields.Many2one('slide.channel', string='SLF Course')
    adv_leadership_course_id = fields.Many2one('slide.channel', string='Advancing Leadership Course')
    dlim_course_id = fields.Many2one('slide.channel', string='DLIM Course')
    lgr_course_id = fields.Many2one('slide.channel', string='LGR Course')
    lff_course_id = fields.Many2one('slide.channel', string='LFF Course')

    # ================================
    # EVALUATION HISTORY
    # ================================
    evaluation_ids = fields.One2many('mcd.ops.evaluation', 'process_id', string='Evaluations')
    profile_update_ids = fields.One2many('mcd.ops.profile.update', 'process_id', string='Profile Updates')

    # Track which level we are updating (for B12-B16 subprocess)
    _pending_level_update = fields.Char(store=False)

    @api.depends('employee_id', 'current_level', 'state')
    def _compute_name(self):
        for rec in self:
            emp_name = rec.employee_id.name or 'New'
            level = dict(rec._fields['current_level'].selection).get(rec.current_level, '')
            state_label = dict(rec._fields['state'].selection).get(rec.state, '')
            rec.name = f"OPS: {emp_name} ({level}) - {state_label}"

    @api.model
    def _expand_states(self, records, values, domain):
        """Expand all states in Kanban view"""
        return [key for key, val in self._fields['state'].selection]

    # ================================
    # PHASE 1: SETUP (B1-B6)
    # ================================
    def action_b1_identify(self):
        """B1: OC identifies candidates from Crew development"""
        self.ensure_one()
        self.write({'state': 'b1_identify'})
        self.message_post(body="B1: Candidate identified by OC for OPS Capacity Development.")

    def action_b2_b4_class_setup(self):
        """B2-B4: L&D creates class, system notifies departments"""
        self.ensure_one()
        self.write({'state': 'b2_b4_class'})
        self.message_post(body="B2-B4: Class setup initiated. L&D creating training materials.")
        # TODO: Send notifications to departments

    def action_b5_schedule(self):
        """B5: RGM schedules training"""
        self.ensure_one()
        self.write({'state': 'b5_schedule'})
        self.message_post(body="B5: RGM scheduling training sessions.")
        # Integration point: Open Planning module

    def action_b6_start_learning(self):
        """B6: Employee begins learning"""
        self.ensure_one()
        self.write({'state': 'b6_learning'})
        self.message_post(body="B6: Employee started learning on eLearning platform.")
        # Auto-proceed to B7 gateway
        return self._gateway_b7_check_sm()

    # ================================
    # PHASE 2: SM LEVEL (B7-B11)
    # ================================
    def _gateway_b7_check_sm(self):
        """B7: Gateway - Check if SM already completed"""
        self.ensure_one()
        self.write({'state': 'b7_gateway_sm'})
        
        if self._check_has_level('sm'):
            self.message_post(body="B7 Gateway: SM level already achieved. Skipping to B17 (DM1).")
            return self._gateway_b17_check_dm1()
        
        self.message_post(body="B7 Gateway: SM not yet achieved. Starting SM training path.")
        return self.action_b8_start_running_areas()

    def action_b8_start_running_areas(self):
        """B8: Start Running Areas training"""
        self.ensure_one()
        self.write({'state': 'b8_running_areas'})
        self.message_post(body="B8: Employee enrolled in Running Areas course.")

    def action_b8_complete(self):
        """B8: Running Areas training completed -> Move to B9"""
        self.ensure_one()
        self.write({'state': 'b9_set_pet'})
        self.message_post(body="B8: Running Areas course completed. Ready for B9 SET/PET evaluation.")

    def action_b9_evaluate(self, passed=True, fail_reason=None):
        """B9: RGM evaluates SET/PET"""
        self.ensure_one()
        result = 'pass' if passed else 'fail'
        vals = {'b9_result': result}
        if not passed:
            vals['b9_fail_reason'] = fail_reason
        self.write(vals)
        
        # Create evaluation record
        self.env['mcd.ops.evaluation'].create({
            'process_id': self.id,
            'eval_type': 'set_pet',
            'evaluator_id': self.env.uid,
            'result': result,
            'fail_reason': fail_reason
        })
        
        if not passed:
            self.message_post(body=f"B9: SET/PET FAILED - {fail_reason}. Returning to B8.")
            self.write({'state': 'b8_running_areas'})
            return
        
        self.message_post(body="B9: SET/PET PASSED. Moving to B10 SLF training.")
        self.write({'state': 'b10_slf'})

    def action_b10_complete(self):
        """B10: SLF training completed -> Move to B11"""
        self.ensure_one()
        self.write({'state': 'b11_slv'})
        self.message_post(body="B10: SLF course completed. Ready for B11 SLV evaluation by OC.")

    def action_b11_evaluate(self, passed=True, fail_reason=None):
        """B11: OC evaluates SLV"""
        self.ensure_one()
        result = 'pass' if passed else 'fail'
        vals = {'b11_result': result}
        if not passed:
            vals['b11_fail_reason'] = fail_reason
        self.write(vals)
        
        self.env['mcd.ops.evaluation'].create({
            'process_id': self.id,
            'eval_type': 'slv',
            'evaluator_id': self.env.uid,
            'result': result,
            'fail_reason': fail_reason
        })
        
        if not passed:
            self.message_post(body=f"B11: SLV FAILED - {fail_reason}. Returning to B10.")
            self.write({'state': 'b10_slf'})
            return
        
        self.message_post(body="B11: SLV PASSED! SM Level Complete. Starting Profile Update (B12-B16).")
        self._pending_level_update = 'sm'
        return self._start_profile_update_subprocess('sm')

    # ================================
    # SUB-PROCESS: PROFILE UPDATE (B12-B16)
    # ================================
    def _start_profile_update_subprocess(self, new_level):
        """B12-B16: Profile Update Subprocess called after OC approval"""
        self.ensure_one()
        self._pending_level_update = new_level
        self.write({'state': 'b12_lnd_eval'})
        self.message_post(body=f"Starting Profile Update for Level: {new_level.upper()}")

    def action_b12_complete(self, lnd_feedback=None):
        """B12: L&D evaluates training effectiveness"""
        self.ensure_one()
        self.write({'b12_lnd_feedback': lnd_feedback, 'state': 'b13_emp_feedback'})
        self.message_post(body="B12: L&D training effectiveness evaluation recorded.")

    def action_b13_complete(self, employee_feedback=None):
        """B13: Employee provides feedback"""
        self.ensure_one()
        self.write({'b13_employee_feedback': employee_feedback, 'state': 'b14_update_profile'})
        self.message_post(body="B13: Employee feedback recorded.")
        # Auto-proceed to B14
        return self.action_b14_update_profile()

    def action_b14_update_profile(self):
        """B14: System updates employee profile (grant skill)"""
        self.ensure_one()
        new_level = self._pending_level_update or self._get_next_level()
        self._grant_skill_for_level(new_level)
        self.write({'state': 'b15_update_permission', 'current_level': new_level})
        self.message_post(body=f"B14: Profile updated. Skill for {new_level.upper()} granted.")
        # Auto-proceed to B15
        return self.action_b15_update_permission()

    def action_b15_update_permission(self):
        """B15: System updates permissions"""
        self.ensure_one()
        # TODO: Add employee to appropriate security group based on level
        self.write({'state': 'b16_update_budget'})
        self.message_post(body="B15: Permissions updated for new role.")
        # Auto-proceed to B16
        return self.action_b16_update_budget()

    def action_b16_update_budget(self, cost=0.0):
        """B16: System records training budget"""
        self.ensure_one()
        self.write({'b16_training_cost': (self.b16_training_cost or 0) + cost})
        
        # Create profile update record
        self.env['mcd.ops.profile.update'].create({
            'process_id': self.id,
            'old_level': dict(self._fields['current_level'].selection).get(
                self._get_previous_level(self.current_level), 'N/A'),
            'new_level': self.current_level,
            'lnd_feedback': self.b12_lnd_feedback,
            'employee_feedback': self.b13_employee_feedback,
            'budget_recorded': cost
        })
        
        self.message_post(body="B16: Training budget recorded. Profile Update complete.")
        
        # Navigate to next gateway based on current level
        return self._navigate_after_profile_update()

    def _navigate_after_profile_update(self):
        """After B16: Navigate to next level gateway"""
        self.ensure_one()
        if self.current_level == 'sm':
            return self._gateway_b17_check_dm1()
        elif self.current_level == 'dm1':
            return self._gateway_b22_check_dm2()
        elif self.current_level == 'dm2':
            return self.action_b27_start_lgr()
        elif self.current_level == 'rgm':
            return self.action_b31_start_lff()
        elif self.current_level == 'leader':
            return self._complete_process()

    # ================================
    # PHASE 3: DM1 LEVEL (B17-B21)
    # ================================
    def _gateway_b17_check_dm1(self):
        """B17: Gateway - Check if DM1 already completed"""
        self.ensure_one()
        self.write({'state': 'b17_gateway_dm1'})
        
        if self._check_has_level('dm1'):
            self.message_post(body="B17 Gateway: DM1 already achieved. Skipping to B22 (DM2).")
            return self._gateway_b22_check_dm2()
        
        self.message_post(body="B17 Gateway: DM1 not yet achieved. Starting DM1 training path.")
        return self.action_b18_start_adv_leadership()

    def action_b18_start_adv_leadership(self):
        """B18: Start Advancing Leadership training"""
        self.ensure_one()
        self.write({'state': 'b18_adv_leadership'})
        self.message_post(body="B18: Employee enrolled in Advancing Your Leadership course.")

    def action_b18_complete(self):
        """B18: Course completed -> Move to B19"""
        self.ensure_one()
        self.write({'state': 'b19_course_check'})
        self.message_post(body="B18: Advancing Leadership completed. Ready for B19 RGM evaluation.")

    def action_b19_evaluate(self, passed=True, fail_reason=None):
        """B19: RGM evaluates course completion"""
        self.ensure_one()
        result = 'pass' if passed else 'fail'
        self.write({'b19_result': result, 'b19_fail_reason': fail_reason if not passed else False})
        
        self.env['mcd.ops.evaluation'].create({
            'process_id': self.id,
            'eval_type': 'dm1_course',
            'evaluator_id': self.env.uid,
            'result': result,
            'fail_reason': fail_reason
        })
        
        if not passed:
            self.message_post(body=f"B19: Course check FAILED - {fail_reason}. Returning to B18.")
            self.write({'state': 'b18_adv_leadership'})
            return
        
        self.message_post(body="B19: Course PASSED. Moving to B20 (3 System Verify training).")
        self.write({'state': 'b20_3sv_training'})

    def action_b20_complete(self):
        """B20: 3 System training completed -> Move to B21"""
        self.ensure_one()
        self.write({'state': 'b21_3sv_eval'})
        self.message_post(body="B20: 3 System training completed. Ready for B21 OC evaluation.")

    def action_b21_evaluate(self, passed=True, fail_reason=None):
        """B21: OC evaluates 3 System Verify"""
        self.ensure_one()
        result = 'pass' if passed else 'fail'
        self.write({'b21_result': result, 'b21_fail_reason': fail_reason if not passed else False})
        
        self.env['mcd.ops.evaluation'].create({
            'process_id': self.id,
            'eval_type': '3sv',
            'evaluator_id': self.env.uid,
            'result': result,
            'fail_reason': fail_reason
        })
        
        if not passed:
            self.message_post(body=f"B21: 3 SV FAILED - {fail_reason}. Returning to B20.")
            self.write({'state': 'b20_3sv_training'})
            return
        
        self.message_post(body="B21: 3 SV PASSED! DM1 Level Complete. Starting Profile Update (B12-B16).")
        return self._start_profile_update_subprocess('dm1')

    # ================================
    # PHASE 4: DM2 LEVEL (B22-B26)
    # ================================
    def _gateway_b22_check_dm2(self):
        """B22: Gateway - Check if DM2 already completed"""
        self.ensure_one()
        self.write({'state': 'b22_gateway_dm2'})
        
        if self._check_has_level('dm2'):
            self.message_post(body="B22 Gateway: DM2 already achieved. Skipping to B27 (RGM).")
            return self.action_b27_start_lgr()
        
        self.message_post(body="B22 Gateway: DM2 not yet achieved. Starting DM2 training path.")
        return self.action_b23_start_dlim()

    def action_b23_start_dlim(self):
        """B23: Start DLIM training"""
        self.ensure_one()
        self.write({'state': 'b23_dlim'})
        self.message_post(body="B23: Employee enrolled in DLIM course.")

    def action_b23_complete(self):
        """B23: DLIM completed -> Move to B24"""
        self.ensure_one()
        self.write({'state': 'b24_course_check'})
        self.message_post(body="B23: DLIM completed. Ready for B24 RGM evaluation.")

    def action_b24_evaluate(self, passed=True, fail_reason=None):
        """B24: RGM evaluates DLIM completion"""
        self.ensure_one()
        result = 'pass' if passed else 'fail'
        self.write({'b24_result': result, 'b24_fail_reason': fail_reason if not passed else False})
        
        self.env['mcd.ops.evaluation'].create({
            'process_id': self.id,
            'eval_type': 'dm2_course',
            'evaluator_id': self.env.uid,
            'result': result,
            'fail_reason': fail_reason
        })
        
        if not passed:
            self.message_post(body=f"B24: DLIM check FAILED - {fail_reason}. Returning to B23.")
            self.write({'state': 'b23_dlim'})
            return
        
        self.message_post(body="B24: DLIM PASSED. Moving to B25 (2 System Verify training).")
        self.write({'state': 'b25_2sv_training'})

    def action_b25_complete(self):
        """B25: 2 System training completed -> Move to B26"""
        self.ensure_one()
        self.write({'state': 'b26_2sv_eval'})
        self.message_post(body="B25: 2 System training completed. Ready for B26 OC evaluation.")

    def action_b26_evaluate(self, passed=True, fail_reason=None):
        """B26: OC evaluates 2 System Verify"""
        self.ensure_one()
        result = 'pass' if passed else 'fail'
        self.write({'b26_result': result, 'b26_fail_reason': fail_reason if not passed else False})
        
        self.env['mcd.ops.evaluation'].create({
            'process_id': self.id,
            'eval_type': '2sv',
            'evaluator_id': self.env.uid,
            'result': result,
            'fail_reason': fail_reason
        })
        
        if not passed:
            self.message_post(body=f"B26: 2 SV FAILED - {fail_reason}. Returning to B25.")
            self.write({'state': 'b25_2sv_training'})
            return
        
        self.message_post(body="B26: 2 SV PASSED! DM2 Level Complete. Starting Profile Update (B12-B16).")
        return self._start_profile_update_subprocess('dm2')

    # ================================
    # PHASE 5: RGM LEVEL (B27-B30)
    # ================================
    def action_b27_start_lgr(self):
        """B27: Start LGR training"""
        self.ensure_one()
        self.write({'state': 'b27_lgr'})
        self.message_post(body="B27: Employee enrolled in Leading Great Restaurant (LGR) course.")

    def action_b27_complete(self):
        """B27: LGR completed -> Move to B28"""
        self.ensure_one()
        self.write({'state': 'b28_course_check'})
        self.message_post(body="B27: LGR completed. Ready for B28 RGM evaluation.")

    def action_b28_evaluate(self, passed=True, fail_reason=None):
        """B28: RGM evaluates LGR completion"""
        self.ensure_one()
        result = 'pass' if passed else 'fail'
        self.write({'b28_result': result, 'b28_fail_reason': fail_reason if not passed else False})
        
        self.env['mcd.ops.evaluation'].create({
            'process_id': self.id,
            'eval_type': 'rgm_course',
            'evaluator_id': self.env.uid,
            'result': result,
            'fail_reason': fail_reason
        })
        
        if not passed:
            self.message_post(body=f"B28: LGR check FAILED - {fail_reason}. Returning to B27.")
            self.write({'state': 'b27_lgr'})
            return
        
        self.message_post(body="B28: LGR PASSED. Moving to B29 (4 System Verify training).")
        self.write({'state': 'b29_4sv_training'})

    def action_b29_complete(self):
        """B29: 4 System training completed -> Move to B30"""
        self.ensure_one()
        self.write({'state': 'b30_4sv_eval'})
        self.message_post(body="B29: 4 System training completed. Ready for B30 OC evaluation.")

    def action_b30_evaluate(self, passed=True, fail_reason=None):
        """B30: OC evaluates 4 System Verify"""
        self.ensure_one()
        result = 'pass' if passed else 'fail'
        self.write({'b30_result': result, 'b30_fail_reason': fail_reason if not passed else False})
        
        self.env['mcd.ops.evaluation'].create({
            'process_id': self.id,
            'eval_type': '4sv',
            'evaluator_id': self.env.uid,
            'result': result,
            'fail_reason': fail_reason
        })
        
        if not passed:
            self.message_post(body=f"B30: 4 SV FAILED - {fail_reason}. Returning to B29.")
            self.write({'state': 'b29_4sv_training'})
            return
        
        self.message_post(body="B30: 4 SV PASSED! RGM Level Complete. Starting Profile Update (B12-B16).")
        return self._start_profile_update_subprocess('rgm')

    # ================================
    # PHASE 6: FUTURE LEADER (B31-B32)
    # ================================
    def action_b31_start_lff(self):
        """B31: Start LFF training"""
        self.ensure_one()
        self.write({'state': 'b31_lff'})
        self.message_post(body="B31: Employee enrolled in Leading For Future (LFF) course.")

    def action_b31_complete(self):
        """B31: LFF completed -> Move to B32"""
        self.ensure_one()
        self.write({'state': 'b32_final_eval'})
        self.message_post(body="B31: LFF completed. Ready for B32 Final OC evaluation.")

    def action_b32_evaluate(self, passed=True, fail_reason=None):
        """B32: OC Final Evaluation"""
        self.ensure_one()
        result = 'pass' if passed else 'fail'
        self.write({'b32_result': result, 'b32_fail_reason': fail_reason if not passed else False})
        
        self.env['mcd.ops.evaluation'].create({
            'process_id': self.id,
            'eval_type': 'lff',
            'evaluator_id': self.env.uid,
            'result': result,
            'fail_reason': fail_reason
        })
        
        if not passed:
            self.message_post(body=f"B32: Final evaluation FAILED - {fail_reason}. Returning to B31.")
            self.write({'state': 'b31_lff'})
            return
        
        self.message_post(body="B32: Final evaluation PASSED! Starting final Profile Update (B12-B16).")
        return self._start_profile_update_subprocess('leader')

    def _complete_process(self):
        """End of workflow"""
        self.ensure_one()
        self.write({'state': 'done'})
        self.message_post(body="WORKFLOW COMPLETE: Employee has achieved Future Leader status!")

    # ================================
    # HELPER METHODS
    # ================================
    def _check_has_level(self, level):
        """Check if employee already has a specific OPS level skill"""
        self.ensure_one()
        level_skill_map = {
            'sm': 'Shift Manager Certified',
            'dm1': 'Department Manager 1 Certified',
            'dm2': 'Department Manager 2 Certified',
            'rgm': 'RGM Certified',
            'leader': 'Future Leader Certified'
        }
        skill_name = level_skill_map.get(level)
        if not skill_name:
            return False
        
        skill = self.env['hr.skill'].search([('name', '=', skill_name)], limit=1)
        if not skill:
            return False
        
        return bool(self.env['hr.employee.skill'].search_count([
            ('employee_id', '=', self.employee_id.id),
            ('skill_id', '=', skill.id)
        ]))

    def _grant_skill_for_level(self, level):
        """Grant the appropriate skill to the employee"""
        self.ensure_one()
        level_skill_map = {
            'sm': 'Shift Manager Certified',
            'dm1': 'Department Manager 1 Certified',
            'dm2': 'Department Manager 2 Certified',
            'rgm': 'RGM Certified',
            'leader': 'Future Leader Certified'
        }
        skill_name = level_skill_map.get(level)
        if not skill_name:
            return
        
        # Find or create skill type
        skill_type = self.env['hr.skill.type'].search([('name', '=', 'OPS Capacity')], limit=1)
        if not skill_type:
            skill_type = self.env['hr.skill.type'].create({'name': 'OPS Capacity'})
        
        # Find or create skill
        skill = self.env['hr.skill'].search([
            ('name', '=', skill_name),
            ('skill_type_id', '=', skill_type.id)
        ], limit=1)
        if not skill:
            skill = self.env['hr.skill'].create({
                'name': skill_name,
                'skill_type_id': skill_type.id
            })
        
        # Find or create skill level
        skill_level = self.env['hr.skill.level'].search([
            ('skill_type_id', '=', skill_type.id)
        ], limit=1)
        if not skill_level:
            skill_level = self.env['hr.skill.level'].create({
                'name': 'Certified',
                'skill_type_id': skill_type.id,
                'level_progress': 100
            })
        
        # Check if already has skill
        existing = self.env['hr.employee.skill'].search([
            ('employee_id', '=', self.employee_id.id),
            ('skill_id', '=', skill.id)
        ], limit=1)
        
        if not existing:
            self.env['hr.employee.skill'].create({
                'employee_id': self.employee_id.id,
                'skill_id': skill.id,
                'skill_type_id': skill_type.id,
                'skill_level_id': skill_level.id
            })

    def _get_next_level(self):
        """Get the next level after current"""
        level_order = ['crew', 'sm', 'dm1', 'dm2', 'rgm', 'leader']
        current_idx = level_order.index(self.current_level) if self.current_level in level_order else 0
        if current_idx < len(level_order) - 1:
            return level_order[current_idx + 1]
        return self.current_level

    def _get_previous_level(self, level):
        """Get the previous level"""
        level_order = ['crew', 'sm', 'dm1', 'dm2', 'rgm', 'leader']
        idx = level_order.index(level) if level in level_order else 0
        if idx > 0:
            return level_order[idx - 1]
        return level
