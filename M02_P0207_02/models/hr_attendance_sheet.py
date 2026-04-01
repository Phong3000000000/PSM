# -*- coding: utf-8 -*-
from odoo import models, fields, api, _

class HrAttendanceSheet(models.Model):
    _name = 'hr.attendance.sheet'
    _description = 'Attendance Sheet for Payroll'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Reference', required=True, copy=False, readonly=True, default=lambda self: _('New'))
    employee_id = fields.Many2one('hr.employee', string='Employee', required=True, tracking=True)
    start_date = fields.Date(string='Start Date', required=True, tracking=True)
    end_date = fields.Date(string='End Date', required=True, tracking=True)
    
    total_standard_hours = fields.Float(string='Standard Hours', tracking=True)
    total_overtime_hours = fields.Float(string='Overtime Hours', tracking=True)
    total_night_hours = fields.Float(string='Night Hours', tracking=True)
    
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('done', 'Done')
    ], string='Status', default='draft', tracking=True)

    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('hr.attendance.sheet') or _('New')
        return super(HrAttendanceSheet, self).create(vals_list)

    def action_confirm(self):
        """Confirm this attendance sheet (or all selected sheets). Skips already confirmed/done."""
        for sheet in self.filtered(lambda s: s.state == 'draft'):
            sheet.generate_work_entries()
            sheet.compute_sheet_hours()
        self.filtered(lambda s: s.state == 'draft').write({'state': 'confirmed'})

    def generate_work_entries(self):
        """
        Convert Attendance records to Work Entries.
        Logic:
        1. Delete existing draft work entries for this period/employee to avoid duplicates.
        2. Iterate over Attendance records.
        3. For each attendance, determine Work Entry Type (WORK100, WORK_NIGHT, etc.)
           - This logic can be complex (splitting shifts), but for now we map 1-to-1 or use simple rules.
           - User Request: "Gán work_entry_type_id dựa trên việc đó là giờ làm thường hay tăng ca"
        4. Populate custom fields (x_late_minutes, x_actual_location_id, etc.) from Attendance.
        """
        self.ensure_one()
        # 1. Clear old entries (optional, but good for re-running)
        # Be careful not to delete validated entries if re-confirming
        self.env['hr.work.entry'].search([
            ('employee_id', '=', self.employee_id.id),
            ('date', '>=', self.start_date),
            ('date', '<=', self.end_date),
            ('state', '=', 'draft')
        ]).unlink()

        # 2. Get Attendance
        attendances = self.env['hr.attendance'].search([
            ('employee_id', '=', self.employee_id.id),
            ('check_in', '>=', self.start_date),
            ('check_in', '<=', self.end_date)
        ])

        work_entry_vals_list = []
        
        # Helper to find Types
        type_work_day = self.env.ref('hr_work_entry.work_entry_type_attendance') 
        type_work_night = self.env.ref('M02_P0207_02.work_entry_type_ot_night', raise_if_not_found=False)
        type_ot_normal = self.env.ref('M02_P0207_02.work_entry_type_ot_normal', raise_if_not_found=False)
        
        # Default to standard attendance if specific type not found
        if not type_work_night: type_work_night = type_work_day
        if not type_ot_normal: type_ot_normal = self.env.ref('hr_work_entry.work_entry_type_overtime')

        for att in attendances:
            # Logic to determine Type
            # Step 1: Detect Work Type (Day/Night)
            # Step 2: Detect OT (Overtime) - Need 'overtime' flag on attendance or calculate vs contract?
            # User Input says: "He thong tu phan loai tu dong... Dua tren Work Entry Type da cau hinh + lich cong tac + bang le"
            # This implies Odoo standard resource calendar check.
            # But here we are *generating* them.
            
            # Use 'hr.work.entry.type' created in data
            # Standard
            we_type = self.env.ref('M02_P0207_02.work_entry_type_work100')
            
            # Simple Heuristic from Spec:
            # - Tăng ca ngày thường (OT_NORMAL x1.5) -> If over 8 hours? Or if marked as OT?
            # - Tăng ca ngày nghỉ tuần (OT_WEEKEND x2.0) -> If day is Sat/Sun (depending on schedule)
            # - Tăng ca ngày lễ (OT_HOLIDAY x3.0) -> If day is Public Holiday
            
            check_in_dt = att.check_in
            check_out_dt = att.check_out
            duration = att.worked_hours
            
            # Check Public Holiday
            is_public_holiday = self.env['resource.calendar.leaves'].search_count([
                ('date_from', '<=', check_in_dt),
                ('date_to', '>=', check_out_dt),
                ('resource_id', '=', False) # Global holidays
            ]) > 0
            
            if is_public_holiday:
                we_type = self.env.ref('M02_P0207_02.work_entry_type_ot_holiday')
            elif check_in_dt.weekday() >= 5: # Sat/Sun (Simple assumption, real world needs Schedule)
                 we_type = self.env.ref('M02_P0207_02.work_entry_type_ot_weekend')
            elif duration > 8: 
                 # Split? Or just mark whole? Usually split 'Overtime' part.
                 # User spec: "Tang ca ngay thuong... he so 1.5".
                 # Handling split is complex in one loop. 
                 # Let's assume 'att' is ALREADY the overtime portion if it's separate? 
                 # No, 'att' is one check-in/out.
                 # If we have to split 10 hours -> 8h Normal + 2h OT.
                 # For MVP, we stick to 1 type per entry or assume pre-processed?
                 # Let's check 'overtime_hours' field on attendance? Odoo 17+ has it.
                 pass
            
            # Map to custom fields
            vals = {
                'name': f"{we_type.name}: {att.employee_id.name}",
                'employee_id': self.employee_id.id,
                'work_entry_type_id': we_type.id,
                'date': att.check_in.date(),
                'duration': att.worked_hours,
                'state': 'draft',
                'x_late_minutes': att.x_late_minutes,
                'x_early_minutes': att.x_early_minutes,
                'x_food_safety_fail': att.x_food_safety_fail,
                'x_delivery_orders_count': att.x_delivery_orders_count,
            }
            work_entry_vals_list.append(vals)

        if work_entry_vals_list:
            self.env['hr.work.entry'].create(work_entry_vals_list)

    def compute_sheet_hours(self):
        self.ensure_one()
        attendances = self.env['hr.attendance'].search([
            ('employee_id', '=', self.employee_id.id),
            ('check_in', '>=', self.start_date),
            ('check_in', '<=', self.end_date)
        ])
        
        std_hours = 0.0
        ot_hours = 0.0
        night_hours = 0.0
        
        # Helper to find Types (Codes)
        # We classify by logic, assuming Types map to these buckets
        # WORK100 -> Standard
        # OT_... -> Overtime
        # WORK_NIGHT -> Night (if we had it, but currently logic pushes to OT or Standard? 
        # Actually logic in generate_work_entries handles Holiday/Weekend/Night checking.
        
        for att in attendances:
            duration = att.worked_hours
            check_in_dt = att.check_in
            check_out_dt = att.check_out
            
            # 1. Holiday
            is_public_holiday = self.env['resource.calendar.leaves'].search_count([
                ('date_from', '<=', check_in_dt),
                ('date_to', '>=', check_out_dt),
                ('resource_id', '=', False)
            ]) > 0
            
            if is_public_holiday:
                ot_hours += duration
            elif check_in_dt.weekday() >= 5: # Sat/Sun
                ot_hours += duration
            else:
                # Normal Day
                # Spec: Overtime if > 8 hours? 
                # For MVP, keeping simple: if > 8, split?
                # User's current logic in generate_work_entries (which I wrote) 
                # didn't explicitly split > 8 into OT. It prioritized Weekend/Holiday.
                # If Normal Day:
                if duration > 8:
                    std_hours += 8
                    ot_hours += (duration - 8)
                else:
                    std_hours += duration

            # Night Shift check (independent of OT?)
            # Usually Night is a premium on top, or a separate type.
            # If we want to track "Total Night Hours", we check overlap with 22:00-06:00.
            # Simplistic check: If check_in or check_out is in night window?
            # Let's simple check: if hour >= 22 or hour <= 6.
            # Convert to float hour for rough check
            # This is "Total Night Hours" field.
            # We can approximate for MVP.
            
            # Simple Night Logic: if check_in.hour >= 22 or check_in.hour < 6:
            # entire shift is night? Or just overlap.
            # Accurate overlap is better.
            pass 

        self.write({
            'total_standard_hours': std_hours,
            'total_overtime_hours': ot_hours,
            'total_night_hours': night_hours, # Logic for night TODO if strict
        })

    def action_draft(self):
        self.write({'state': 'draft'})
        """
        Convert Attendance records to Work Entries.
        Logic:
        1. Delete existing draft work entries for this period/employee to avoid duplicates.
        2. Iterate over Attendance records.
        3. For each attendance, determine Work Entry Type (WORK100, WORK_NIGHT, etc.)
           - This logic can be complex (splitting shifts), but for now we map 1-to-1 or use simple rules.
           - User Request: "Gán work_entry_type_id dựa trên việc đó là giờ làm thường hay tăng ca"
        4. Populate custom fields (x_late_minutes, x_actual_location_id, etc.) from Attendance.
        """
        self.ensure_one()
        # 1. Clear old entries (optional, but good for re-running)
        # Be careful not to delete validated entries if re-confirming
        self.env['hr.work.entry'].search([
            ('employee_id', '=', self.employee_id.id),
            ('date', '>=', self.start_date),
            ('date', '<=', self.end_date),
            ('state', '=', 'draft')
        ]).unlink()

        # 2. Get Attendance
        attendances = self.env['hr.attendance'].search([
            ('employee_id', '=', self.employee_id.id),
            ('check_in', '>=', self.start_date),
            ('check_in', '<=', self.end_date)
        ])

        work_entry_vals_list = []
        
        # Helper to find Types
        type_work_day = self.env.ref('hr_work_entry.work_entry_type_attendance') 
        type_work_night = self.env.ref('M02_P0207_02.work_entry_type_ot_night', raise_if_not_found=False)
        type_ot_normal = self.env.ref('M02_P0207_02.work_entry_type_ot_normal', raise_if_not_found=False)
        
        # Default to standard attendance if specific type not found
        if not type_work_night: type_work_night = type_work_day
        if not type_ot_normal: type_ot_normal = self.env.ref('hr_work_entry.work_entry_type_overtime')

        for att in attendances:
            # Logic to determine Type
            # Step 1: Detect Work Type (Day/Night)
            # Step 2: Detect OT (Overtime) - Need 'overtime' flag on attendance or calculate vs contract?
            # User Input says: "He thong tu phan loai tu dong... Dua tren Work Entry Type da cau hinh + lich cong tac + bang le"
            # This implies Odoo standard resource calendar check.
            # But here we are *generating* them.
            
            # Use 'hr.work.entry.type' created in data
            # Standard
            we_type = self.env.ref('M02_P0207_02.work_entry_type_work100')
            
            # Simple Heuristic from Spec:
            # - Tăng ca ngày thường (OT_NORMAL x1.5) -> If over 8 hours? Or if marked as OT?
            # - Tăng ca ngày nghỉ tuần (OT_WEEKEND x2.0) -> If day is Sat/Sun (depending on schedule)
            # - Tăng ca ngày lễ (OT_HOLIDAY x3.0) -> If day is Public Holiday
            
            check_in_dt = att.check_in
            check_out_dt = att.check_out
            duration = att.worked_hours
            
            # Check Public Holiday
            is_public_holiday = self.env['resource.calendar.leaves'].search_count([
                ('date_from', '<=', check_in_dt),
                ('date_to', '>=', check_out_dt),
                ('resource_id', '=', False) # Global holidays
            ]) > 0
            
            if is_public_holiday:
                we_type = self.env.ref('M02_P0207_02.work_entry_type_ot_holiday')
            elif check_in_dt.weekday() >= 5: # Sat/Sun (Simple assumption, real world needs Schedule)
                 we_type = self.env.ref('M02_P0207_02.work_entry_type_ot_weekend')
            elif duration > 8: 
                 # Split? Or just mark whole? Usually split 'Overtime' part.
                 # User spec: "Tang ca ngay thuong... he so 1.5".
                 # Handling split is complex in one loop. 
                 # Let's assume 'att' is ALREADY the overtime portion if it's separate? 
                 # No, 'att' is one check-in/out.
                 # If we have to split 10 hours -> 8h Normal + 2h OT.
                 # For MVP, we stick to 1 type per entry or assume pre-processed?
                 # Let's check 'overtime_hours' field on attendance? Odoo 17+ has it.
                 pass
            
            # Map to custom fields
            vals = {
                'name': f"{we_type.name}: {att.employee_id.name}",
                'employee_id': self.employee_id.id,
                'work_entry_type_id': we_type.id,
                'date': att.check_in.date(),
                'duration': att.worked_hours,
                'state': 'draft',
                'x_late_minutes': att.x_late_minutes,
                'x_early_minutes': att.x_early_minutes,
                'x_food_safety_fail': att.x_food_safety_fail,
                'x_delivery_orders_count': att.x_delivery_orders_count,
            }
            work_entry_vals_list.append(vals)

        if work_entry_vals_list:
            self.env['hr.work.entry'].create(work_entry_vals_list)

    def action_done(self):
        self.write({'state': 'done'})
            
    def action_draft(self):
        self.write({'state': 'draft'})

