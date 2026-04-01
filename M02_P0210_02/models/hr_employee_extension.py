from odoo import models, fields


class HrEmployeeOPSExtension(models.Model):
    """Extend hr.employee with OPS Capacity Level display"""
    _inherit = 'hr.employee'

    ops_capacity_level = fields.Selection([
        ('crew', 'Crew'),
        ('sm', 'Shift Manager'),
        ('dm1', 'Department Manager 1'),
        ('dm2', 'Department Manager 2'),
        ('rgm', 'Restaurant General Manager'),
        ('leader', 'Future Leader')
    ], string='OPS Capacity Level', compute='_compute_ops_capacity_level', store=True)

    ops_capacity_process_ids = fields.One2many(
        'mcd.ops.capacity.process',
        'employee_id',
        string='OPS Capacity Processes'
    )

    def _compute_ops_capacity_level(self):
        """Compute the highest achieved OPS Capacity level from skills"""
        level_priority = ['leader', 'rgm', 'dm2', 'dm1', 'sm', 'crew']
        level_skill_map = {
            'leader': 'Future Leader Certified',
            'rgm': 'RGM Certified',
            'dm2': 'Department Manager 2 Certified',
            'dm1': 'Department Manager 1 Certified',
            'sm': 'Shift Manager Certified'
        }
        for employee in self:
            employee.ops_capacity_level = 'crew' 
            for level in level_priority:
                skill_name = level_skill_map.get(level)
                if skill_name:
                    has_skill = self.env['hr.employee.skill'].search_count([
                        ('employee_id', '=', employee.id),
                        ('skill_id.name', '=', skill_name)
                    ])
                    if has_skill:
                        employee.ops_capacity_level = level
                        break
    
    is_part_time = fields.Boolean(string='Is Part Time', compute='_compute_is_part_time')

    def _compute_is_part_time(self):
        for employee in self:
            # Check employment_type from M02_P0206_00
            if hasattr(employee, 'employment_type') and employee.employment_type == 'part_time':
                employee.is_part_time = True
            else:
                employee.is_part_time = False

    # --- Active Manager Proposal Tracking ---
    has_active_manager_proposal = fields.Boolean(
        compute='_compute_active_manager_proposal', 
        string='Has Active Proposal'
    )
    active_manager_proposal_display = fields.Char(
        compute='_compute_active_manager_proposal', 
        string='Proposal Status'
    )
    
    def _compute_active_manager_proposal(self):
        """Check for active manager proposal (not done/cancelled)"""
        ManagerSchedule = self.env['mcd.manager.schedule']
        for employee in self:
            active_schedule = ManagerSchedule.search([
                ('employee_id', '=', employee.id),
                ('state', 'not in', ['done', 'cancelled'])
            ], limit=1)
            
            if active_schedule:
                employee.has_active_manager_proposal = True
                # Get state label
                state_label = dict(active_schedule._fields['state'].selection).get(active_schedule.state, active_schedule.state)
                employee.active_manager_proposal_display = state_label
            else:
                employee.has_active_manager_proposal = False
                employee.active_manager_proposal_display = False

    # Override can_propose_manager from M02_P0209_02 to align with new active state logic
    def _compute_can_propose_manager(self):
        super()._compute_can_propose_manager() # Run base logic first
        ManagerSchedule = self.env['mcd.manager.schedule']
        for employee in self:
            # If base logic already says False (e.g. progress < 100), keep it False
            if not employee.can_propose_manager:
                continue
                
            # If base logic says True (checks draft/confirmed only), we double check 
            # with M02_P0210_02 full active states (not done/cancelled)
            pending_schedule = ManagerSchedule.search([
                ('employee_id', '=', employee.id),
                ('state', 'not in', ['done', 'cancelled'])
            ], limit=1)
            
            if pending_schedule:
                employee.can_propose_manager = False
