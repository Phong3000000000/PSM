from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

class TravelRequest(models.Model):
    _name = 'x_psm_travel_request'
    _description = 'Travel Request'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'x_psm_name'

    x_psm_name = fields.Char(string='Request Number', required=True, copy=False, readonly=True, default=lambda self: _('New'))
    x_psm_employee_id = fields.Many2one('hr.employee', string='Requester', required=True, default=lambda self: self.env.user.employee_id)
    x_psm_department_id = fields.Many2one('hr.department', string='Department', required=True, default=lambda self: self.env.user.employee_id.department_id)
    x_psm_purpose = fields.Text(string='Purpose', required=True)
    x_psm_location = fields.Text(string='Location')
    x_psm_date_start = fields.Date(string='Start Date', required=True)
    x_psm_date_end = fields.Date(string='End Date', required=True)
    x_psm_duration_days = fields.Integer(string='Duration (Days)', compute='_compute_duration', store=True)
    x_psm_overnight_count = fields.Integer(string='Overnights', compute='_compute_duration', store=True)
    
    x_psm_is_urgent = fields.Boolean(string='Urgent (< 1 week)', default=False)
    x_psm_urgent_reason = fields.Text(string='Urgent Reason')
    
    x_psm_destination_id = fields.Many2one('x_psm_travel_destination', string='Destination', required=True)
    x_psm_is_international = fields.Boolean(string='Is International', related='x_psm_destination_id.x_psm_is_international')
    x_psm_hotel_id = fields.Many2one('x_psm_travel_hotel', string='Proposed Hotel')
    
    x_psm_traveler_ids = fields.One2many('x_psm_travel_request_line', 'x_psm_request_id', string='Travelers')
    x_psm_schedule_ids = fields.One2many('x_psm_travel_schedule', 'x_psm_request_id', string='Schedule')
    x_psm_itinerary_ids = fields.One2many('x_psm_travel_itinerary', 'x_psm_request_id', string='Itinerary')
    x_psm_accommodation_ids = fields.One2many('x_psm_travel_accommodation', 'x_psm_request_id', string='Accommodation')
    
    x_psm_budget_hotel = fields.Float(string='Hotel Budget (Reference)', compute='_compute_budget', store=True)
    x_psm_budget_allowance = fields.Float(string='Allowance Budget', compute='_compute_budget', store=True)
    x_psm_budget_transport = fields.Float(string='Transport Budget', compute='_compute_budget', store=True)
    x_psm_budget_laundry = fields.Float(string='Laundry Budget', compute='_compute_budget', store=True)
    
    x_psm_actual_total = fields.Float(string='Actual Total Cost', compute='_compute_budget', store=True)
    x_psm_actual_transport = fields.Float(string='Actual Transport Cost', compute='_compute_budget', store=True)
    x_psm_actual_hotel = fields.Float(string='Actual Hotel Cost', compute='_compute_budget', store=True)
    x_psm_actual_allowance = fields.Float(string='Actual Allowance Cost', compute='_compute_budget', store=True)
    
    x_psm_budget_total = fields.Float(string='Budget Total (All)', compute='_compute_budget', store=True)
    
    x_psm_approval_request_id = fields.Many2one('approval.request', string='Approval Request', copy=False, readonly=True)
    x_psm_approval_state = fields.Selection(related='x_psm_approval_request_id.request_status', string='Approval State')
    
    x_psm_flight_ticket_ids = fields.Many2many('ir.attachment', 'travel_request_flight_ticket_rel', 'request_id', 'attachment_id', string='Flight Tickets')
    x_psm_hotel_ticket_ids = fields.Many2many('ir.attachment', 'travel_request_hotel_ticket_rel', 'request_id', 'attachment_id', string='Hotel Tickets')
    
    x_psm_description = fields.Html(string='Description')
    
    x_psm_is_travel_admin = fields.Boolean(compute='_compute_is_travel_admin')
    
    x_psm_state = fields.Selection([
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('approved', 'Approved'),
        ('in_progress', 'In Progress'),
        ('done', 'Done'),
        ('refused', 'Refused')
    ], string='Status', default='draft', readonly=True, copy=False, tracking=True)

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        # Default Requester
        if 'x_psm_employee_id' in fields_list and not res.get('x_psm_employee_id'):
            res['x_psm_employee_id'] = self.env.user.employee_id.id
            
        employee = self.env['hr.employee'].browse(res.get('x_psm_employee_id')) or self.env.user.employee_id
        if employee and 'x_psm_traveler_ids' in fields_list and not res.get('x_psm_traveler_ids'):
            res['x_psm_traveler_ids'] = [(0, 0, {
                'x_psm_employee_id': employee.id,
                'x_psm_job_id': employee.job_id.id,
            })]
        return res

    @api.onchange('x_psm_employee_id')
    def _onchange_employee_id_requester(self):
        if self.x_psm_employee_id:
            self.x_psm_department_id = self.x_psm_employee_id.department_id
    
    x_psm_expense_count = fields.Integer(string='Expenses', compute='_compute_expense_count')
    
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('x_psm_name', _('New')) == _('New'):
                vals['x_psm_name'] = self.env['ir.sequence'].next_by_code('travel.request.seq') or _('New')
        return super().create(vals_list)
        
    @api.depends('x_psm_date_start', 'x_psm_date_end')
    def _compute_duration(self):
        for rec in self:
            if rec.x_psm_date_start and rec.x_psm_date_end:
                duration = (rec.x_psm_date_end - rec.x_psm_date_start).days + 1
                rec.x_psm_duration_days = max(1, duration)
                rec.x_psm_overnight_count = max(0, duration - 1)
            else:
                rec.x_psm_duration_days = 0
                rec.x_psm_overnight_count = 0

    @api.onchange('x_psm_destination_id')
    def _onchange_destination_id(self):
        pass

    @api.depends('x_psm_destination_id', 'x_psm_hotel_id', 'x_psm_traveler_ids.x_psm_allowance_total', 
                 'x_psm_traveler_ids.x_psm_hotel_cost_share', 'x_psm_traveler_ids.x_psm_laundry_cost',
                 'x_psm_overnight_count', 'x_psm_itinerary_ids.x_psm_proposed_total', 'x_psm_itinerary_ids.x_psm_actual_total',
                 'x_psm_accommodation_ids.x_psm_actual_total')
    def _compute_budget(self):
        for rec in self:
            # 1. Allowance
            rec.x_psm_budget_allowance = sum(rec.x_psm_traveler_ids.mapped('x_psm_allowance_total'))
            
            # 2. Hotel
            rec.x_psm_budget_hotel = sum(rec.x_psm_traveler_ids.mapped('x_psm_hotel_cost_share'))

            # 3. Transport
            rec.x_psm_budget_transport = sum(rec.x_psm_itinerary_ids.mapped('x_psm_proposed_total'))

            # 4. Laundry
            rec.x_psm_budget_laundry = sum(rec.x_psm_traveler_ids.mapped('x_psm_laundry_cost'))
            
            # 5. Proposed & Actual Breakdown
            itinerary_actual = sum(rec.x_psm_itinerary_ids.mapped('x_psm_actual_total'))
            accommodation_actual = sum(rec.x_psm_accommodation_ids.mapped('x_psm_actual_total'))

            rec.x_psm_actual_transport = itinerary_actual
            rec.x_psm_actual_hotel = accommodation_actual
            rec.x_psm_actual_allowance = rec.x_psm_budget_allowance
            
            rec.x_psm_actual_total = itinerary_actual + accommodation_actual + rec.x_psm_actual_allowance + rec.x_psm_budget_laundry
            
            # Total Budget (Proposed)
            rec.x_psm_budget_total = rec.x_psm_budget_allowance + rec.x_psm_budget_hotel + rec.x_psm_budget_transport + rec.x_psm_budget_laundry
            
    def _compute_expense_count(self):
        for rec in self:
            rec.x_psm_expense_count = self.env['hr.expense'].search_count([('x_psm_0201_travel_request_id', '=', rec.id)])
            
    def action_psm_view_approval(self):
        self.ensure_one()
        if self.x_psm_approval_request_id:
            return {
                'type': 'ir.actions.act_window',
                'name': 'Approval Request',
                'res_model': 'approval.request',
                'view_mode': 'form',
                'res_id': self.x_psm_approval_request_id.id,
                'target': 'current',
            }
        return False

    @api.constrains('x_psm_duration_days')
    def _check_duration(self):
        for rec in self:
            if rec.x_psm_duration_days > 15:
                raise ValidationError(_("Duration cannot exceed 15 days."))

    @api.constrains('x_psm_is_urgent', 'x_psm_urgent_reason')
    def _check_urgent(self):
        for rec in self:
            if rec.x_psm_is_urgent and not rec.x_psm_urgent_reason:
                raise ValidationError(_("Urgent reason is required for urgent trips."))
                
    @api.constrains('x_psm_traveler_ids')
    def _check_travelers(self):
        for rec in self:
            employees = rec.x_psm_traveler_ids.mapped('x_psm_employee_id')
            if len(employees) < len(rec.x_psm_traveler_ids):
                raise ValidationError(_("Each employee can only appear once in travelers list."))
                
    def _validate_before_submit(self):
        self.ensure_one()
        if self.x_psm_date_start:
            days_diff = (self.x_psm_date_start - fields.Date.today()).days
            if not self.x_psm_is_urgent and days_diff < 7:
                raise ValidationError(_("Departures within 7 days must be marked as Urgent. Please set is_urgent to True."))

        if not self.x_psm_traveler_ids:
            raise ValidationError(_("At least one traveler must be added before submitting."))
        
        for line in self.x_psm_traveler_ids:
            missing = []
            if not line.x_psm_identification_id:
                missing.append(_("ID/CCCD"))
            if not line.x_psm_phone:
                missing.append(_("Phone"))
            if not line.x_psm_email:
                missing.append(_("Email"))
            if not line.x_psm_job_id:
                missing.append(_("Job Position"))
            
            if missing:
                raise ValidationError(_(
                    "Missing mandatory information for traveler %s: %s"
                ) % (line.x_psm_employee_id.name, ", ".join(missing)))
        
        # Ensure all travelers have itinerary coverage (At least 1 line per traveler)
        traveler_ids_in_itinerary = self.x_psm_itinerary_ids.mapped('x_psm_traveler_line_id').ids
        for traveler in self.x_psm_traveler_ids:
            if traveler.id not in traveler_ids_in_itinerary:
                raise ValidationError(_("Traveler %s must be included in the itinerary.") % traveler.x_psm_employee_id.name)

    def action_psm_submit(self):
        # First validate all records
        for rec in self:
            rec._validate_before_submit()

        category = self.env.ref("M02_P0201.approval_category_travel", raise_if_not_found=False)
        if not category:
            raise ValidationError(_("Approval category for travel requests not found!"))
        
        for rec in self:
            # 1. Budget Summary Section
            budget_html = f"""
                <div style="margin-top: 20px; background-color: #fff; border: 1px solid #dee2e6; border-radius: 6px; padding: 15px;">
                    <h4 style="margin-top: 0; color: #5f6368; border-bottom: 2px solid #edeff2; padding-bottom: 5px;">TỔNG HỢP CHI PHÍ DỰ KIẾN</h4>
                    <table style="width: 100%; border-collapse: collapse; margin-top: 10px;">
                        <tr style="border-bottom: 1px solid #f0f0f0;">
                            <td style="padding: 8px 0; color: #666;">Tổng Công tác phí:</td>
                            <td style="padding: 8px 0; text-align: right; font-weight: bold;">{rec.x_psm_budget_allowance:,.0f} VND</td>
                        </tr>
                        <tr style="border-bottom: 1px solid #f0f0f0;">
                            <td style="padding: 8px 0; color: #666;">Tổng Chi phí Khách sạn:</td>
                            <td style="padding: 8px 0; text-align: right; font-weight: bold;">{rec.x_psm_budget_hotel:,.0f} VND</td>
                        </tr>
                        <tr style="border-bottom: 1px solid #f0f0f0;">
                            <td style="padding: 8px 0; color: #666;">Tổng Chi phí Di chuyển:</td>
                            <td style="padding: 8px 0; text-align: right; font-weight: bold;">{rec.x_psm_budget_transport:,.0f} VND</td>
                        </tr>
                        <tr style="border-bottom: 1px solid #f0f0f0; display: {'table-row' if rec.x_psm_budget_laundry > 0 else 'none'};">
                            <td style="padding: 8px 0; color: #666;">Tổng Chi phí Giặt ủi:</td>
                            <td style="padding: 8px 0; text-align: right; font-weight: bold;">{rec.x_psm_budget_laundry:,.0f} VND</td>
                        </tr>
                        <tr style="font-size: 1.1em;">
                            <td style="padding: 12px 0; color: #d93025; font-weight: bold;">TỔNG CỘNG:</td>
                            <td style="padding: 12px 0; text-align: right; color: #d93025; font-weight: bold;">{rec.x_psm_budget_total:,.0f} VND</td>
                        </tr>
                    </table>
                </div>
            """

            # 2. Travelers Table
            travelers_rows = ""
            for t in rec.x_psm_traveler_ids:
                travelers_rows += f"""
                    <tr style="border-bottom: 1px solid #eee;">
                        <td style="padding: 10px; font-weight: 500;">{t.x_psm_employee_id.name}</td>
                        <td style="padding: 10px; color: #666;">{t.x_psm_job_id.name or '-'}</td>
                        <td style="padding: 10px; text-align: right;">{t.x_psm_allowance_total:,.0f}</td>
                        <td style="padding: 10px; text-align: right;">{t.x_psm_hotel_cost_share:,.0f}</td>
                        <td style="padding: 10px; text-align: right; color: #666;">{t.x_psm_laundry_cost:,.0f}</td>
                    </tr>
                """
            
            travelers_html = f"""
                <div style="margin-top: 25px;">
                    <h4 style="color: #1a73e8; border-left: 4px solid #1a73e8; padding-left: 10px; margin-bottom: 12px;">1. DANH SÁCH NHÂN SỰ ({len(rec.x_psm_traveler_ids)})</h4>
                    <table style="width: 100%; border-collapse: collapse; font-size: 13px; background-color: #fff; border: 1px solid #eee;">
                        <thead>
                            <tr style="background-color: #f8f9fa; text-align: left;">
                                <th style="padding: 10px; border-bottom: 2px solid #dee2e6;">Họ và Tên</th>
                                <th style="padding: 10px; border-bottom: 2px solid #dee2e6;">Chức vụ</th>
                                <th style="padding: 10px; border-bottom: 2px solid #dee2e6; text-align: right;">Công tác phí</th>
                                <th style="padding: 10px; border-bottom: 2px solid #dee2e6; text-align: right;">Phòng ở</th>
                                <th style="padding: 10px; border-bottom: 2px solid #dee2e6; text-align: right;">Giặt ủi</th>
                            </tr>
                        </thead>
                        <tbody>{travelers_rows}</tbody>
                    </table>
                </div>
            """

            # 3. Itinerary Table
            itinerary_rows = ""
            for i in rec.x_psm_itinerary_ids:
                dep_time = i.x_psm_departure_datetime.strftime('%d/%m/%Y %H:%M') if i.x_psm_departure_datetime else '-'
                itinerary_rows += f"""
                    <tr style="border-bottom: 1px solid #eee;">
                        <td style="padding: 10px;">{i.x_psm_traveler_line_id.x_psm_employee_id.name}</td>
                        <td style="padding: 10px;">{i.x_psm_from_city_id.x_psm_name} &rarr; {i.x_psm_to_city_id.x_psm_name}</td>
                        <td style="padding: 10px; color: #666;">{dep_time}</td>
                        <td style="padding: 10px; text-align: center;"><span style="background: #e3f2fd; color: #1565c0; padding: 2px 8px; border-radius: 4px; font-size: 11px;">{i.x_psm_transport_mode_id.name or '-'}</span></td>
                        <td style="padding: 10px; text-align: right; font-weight: bold;">{i.x_psm_proposed_total:,.0f}</td>
                    </tr>
                """
            
            itinerary_html = f"""
                <div style="margin-top: 25px;">
                    <h4 style="color: #1a73e8; border-left: 4px solid #1a73e8; padding-left: 10px; margin-bottom: 12px;">2. LỊCH TRÌNH DI CHUYỂN</h4>
                    <table style="width: 100%; border-collapse: collapse; font-size: 13px; background-color: #fff; border: 1px solid #eee;">
                        <thead>
                            <tr style="background-color: #f8f9fa; text-align: left;">
                                <th style="padding: 10px; border-bottom: 2px solid #dee2e6;">Nhân sự</th>
                                <th style="padding: 10px; border-bottom: 2px solid #dee2e6;">Lộ trình</th>
                                <th style="padding: 10px; border-bottom: 2px solid #dee2e6;">Khởi hành</th>
                                <th style="padding: 10px; border-bottom: 2px solid #dee2e6; text-align: center;">Phương tiện</th>
                                <th style="padding: 10px; border-bottom: 2px solid #dee2e6; text-align: right;">Dự kiến</th>
                            </tr>
                        </thead>
                        <tbody>{itinerary_rows or '<tr><td colspan="4" style="padding: 10px; text-align: center; color: #999;">Không có dữ liệu di chuyển</td></tr>'}</tbody>
                    </table>
                </div>
            """

            # 4. Business Schedule Table
            schedule_rows = ""
            # Sort by date then traveler
            sorted_schedules = sorted(rec.x_psm_schedule_ids, key=lambda s: (s.x_psm_date or fields.Date.today(), s.x_psm_employee_id.name or ""))
            for s in sorted_schedules:
                date_str = s.x_psm_date.strftime('%d/%m/%Y') if s.x_psm_date else '-'
                type_color = "#28a745" if s.x_psm_type == 'on' else "#dc3545"
                schedule_rows += f"""
                    <tr style="border-bottom: 1px solid #eee;">
                        <td style="padding: 10px; white-space: nowrap;">{date_str}</td>
                        <td style="padding: 10px;"><strong>{s.x_psm_employee_id.name}</strong></td>
                        <td style="padding: 10px; color: {type_color}; font-weight: bold; text-align: center;">{s.x_psm_type.upper()}</td>
                        <td style="padding: 10px; color: #555; font-size: 12px;">{s.x_psm_content or '-'}</td>
                        <td style="padding: 10px; text-align: right; font-weight: bold;">{s.x_psm_allowance:,.0f}</td>
                    </tr>
                """

            schedule_html = f"""
                <div style="margin-top: 25px;">
                    <h4 style="color: #1a73e8; border-left: 4px solid #1a73e8; padding-left: 10px; margin-bottom: 12px;">3. CHI TIẾT LỊCH TRÌNH CÔNG TÁC</h4>
                    <table style="width: 100%; border-collapse: collapse; font-size: 13px; background-color: #fff; border: 1px solid #eee;">
                        <thead>
                            <tr style="background-color: #f8f9fa; text-align: left;">
                                <th style="padding: 10px; border-bottom: 2px solid #dee2e6;">Ngày</th>
                                <th style="padding: 10px; border-bottom: 2px solid #dee2e6;">Nhân sự</th>
                                <th style="padding: 10px; border-bottom: 2px solid #dee2e6; text-align: center;">Status</th>
                                <th style="padding: 10px; border-bottom: 2px solid #dee2e6;">Nội dung công việc</th>
                                <th style="padding: 10px; border-bottom: 2px solid #dee2e6; text-align: right;">Phụ cấp</th>
                            </tr>
                        </thead>
                        <tbody>{schedule_rows or '<tr><td colspan="4" style="padding: 10px; text-align: center; color: #999;">Không có lịch trình công tác chi tiết</td></tr>'}</tbody>
                    </table>
                </div>
            """

            # 5. Accommodation Table
            accommodation_rows = ""
            for a in rec.x_psm_accommodation_ids:
                in_str = a.x_psm_check_in.strftime('%d/%m/%Y %H:%M') if a.x_psm_check_in else '-'
                out_str = a.x_psm_check_out.strftime('%d/%m/%Y %H:%M') if a.x_psm_check_out else '-'
                accommodation_rows += f"""
                    <tr style="border-bottom: 1px solid #eee;">
                        <td style="padding: 10px;">{a.x_psm_traveler_line_id.x_psm_employee_id.name}</td>
                        <td style="padding: 10px;"><strong>{a.x_psm_hotel_id.x_psm_name or 'Chưa xác định'}</strong></td>
                        <td style="padding: 10px; color: #666; font-size: 11px;">{in_str} <br/> {out_str}</td>
                        <td style="padding: 10px; text-align: center;">{a.x_psm_night_count}</td>
                        <td style="padding: 10px; text-align: right; font-weight: bold;">{a.x_psm_hotel_cost:,.0f}</td>
                    </tr>
                """

            accommodation_html = f"""
                <div style="margin-top: 25px;">
                    <h4 style="color: #1a73e8; border-left: 4px solid #1a73e8; padding-left: 10px; margin-bottom: 12px;">4. THÔNG TIN LƯU TRÚ</h4>
                    <table style="width: 100%; border-collapse: collapse; font-size: 13px; background-color: #fff; border: 1px solid #eee;">
                        <thead>
                            <tr style="background-color: #f8f9fa; text-align: left;">
                                <th style="padding: 10px; border-bottom: 2px solid #dee2e6;">Nhân sự</th>
                                <th style="padding: 10px; border-bottom: 2px solid #dee2e6;">Khách sạn</th>
                                <th style="padding: 10px; border-bottom: 2px solid #dee2e6;">Thời gian</th>
                                <th style="padding: 10px; border-bottom: 2px solid #dee2e6; text-align: center;">Đêm</th>
                                <th style="padding: 10px; border-bottom: 2px solid #dee2e6; text-align: right;">Chi phí</th>
                            </tr>
                        </thead>
                        <tbody>{accommodation_rows or '<tr><td colspan="5" style="padding: 10px; text-align: center; color: #999;">Không có thông tin lưu trú</td></tr>'}</tbody>
                    </table>
                </div>
            """

            reason = f"""
                <div style="font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; max-width: 900px; margin: auto; color: #333; line-height: 1.5;">
                    <div style="background-color: #ffffff; border-radius: 12px; padding: 30px; border: 1px solid #e0e0e0; box-shadow: 0 4px 6px rgba(0,0,0,0.05);">
                        <div style="text-align: center; margin-bottom: 30px; border-bottom: 3px solid #1a73e8; padding-bottom: 15px;">
                            <h2 style="color: #1a73e8; margin: 0; text-transform: uppercase; letter-spacing: 1px;">Phiếu Đề Nghị Công Tác</h2>
                            <p style="color: #666; margin: 5px 0 0 0;">Mã số: {rec.x_psm_name}</p>
                        </div>
                        
                        <div style="display: table; width: 100%; margin-bottom: 25px;">
                            <div style="display: table-cell; width: 50%; padding-right: 20px;">
                                <p style="margin: 5px 0;"><strong style="color: #555;">Người yêu cầu:</strong> {rec.x_psm_employee_id.name}</p>
                                <p style="margin: 5px 0;"><strong style="color: #555;">Bộ phận:</strong> {rec.x_psm_department_id.name}</p>
                                <p style="margin: 5px 0;"><strong style="color: #555;">Mục đích:</strong> {rec.x_psm_purpose}</p>
                            </div>
                            <div style="display: table-cell; width: 50%; border-left: 1px solid #eee; padding-left: 20px;">
                                <p style="margin: 5px 0;"><strong style="color: #555;">Điểm đến:</strong> {rec.x_psm_destination_id.x_psm_name}</p>
                                <p style="margin: 5px 0;"><strong style="color: #555;">Thời gian:</strong> {rec.x_psm_date_start} &rarr; {rec.x_psm_date_end} ({rec.x_psm_duration_days} ngày)</p>
                                <p style="margin: 5px 0;"><strong style="color: #555;">Địa điểm cụ thể:</strong> {rec.x_psm_location or '-'}</p>
                            </div>
                        </div>

                        {budget_html}
                        {travelers_html}
                        {itinerary_html}
                        {schedule_html}
                        {accommodation_html}

                        <div style="margin-top: 30px; padding-top: 20px; border-top: 1px solid #eee; font-style: italic; color: #888; font-size: 12px; text-align: center;">
                            Đây là thông báo tự động từ hệ thống quản lý công tác. Vui lòng xem xét các chi tiết trên trước khi phê duyệt.
                        </div>
                    </div>
                </div>
            """

            approval_vals = {
                'name': f"Travel Approval: {rec.x_psm_employee_id.name} - {rec.x_psm_destination_id.x_psm_name}",
                'category_id': category.id,
                'request_owner_id': rec.x_psm_employee_id.user_id.id or self.env.user.id,
                'amount': rec.x_psm_budget_total,
                'date_start': rec.x_psm_date_start,
                'date_end': rec.x_psm_date_end,
                'reason': reason,
            }
            approval = self.env['approval.request'].create(approval_vals)
            approval.action_confirm()
            
            rec.x_psm_approval_request_id = approval.id
            rec.x_psm_state = 'submitted'
            
    def _compute_is_travel_admin(self):
        admin_users = self.env['x_psm_travel_admin_config'].search([('x_psm_active', '=', True)]).mapped('x_psm_user_id')
        for rec in self:
            is_group_admin = self.env.user.has_group('M02_P0200.GDH_RST_HR_ADMIN_S')
            rec.x_psm_is_travel_admin = is_group_admin or self.env.user in admin_users or self.env.user.has_group('base.group_system')

    def _notify_admin_for_booking(self):
        self.ensure_one()
        admins = self.env['x_psm_travel_admin_config'].search([('x_psm_active', '=', True)])
        if admins:
            for admin in admins:
                self.activity_schedule(
                    'mail.mail_activity_data_todo',
                    user_id=admin.x_psm_user_id.id,
                    note=_('Please handle booking for travel request %s') % self.x_psm_name
                )

    def action_psm_confirm_booking(self):
        for rec in self:
            # Complete booking activity
            activity = self.env['mail.activity'].search([
                ('res_model', '=', 'x_psm_travel_request'),
                ('res_id', '=', rec.id),
                ('activity_type_id', '=', self.env.ref('mail.mail_activity_data_todo').id),
                ('note', 'ilike', 'Please handle booking')
            ], limit=1)
            if activity:
                activity.action_feedback(feedback=_("Booking confirmed and tickets attached."))
            rec.x_psm_state = 'in_progress'
            
            # Notify requester via chatter
            rec.message_post(
                body=_("Your travel booking for request %s has been confirmed. Please check the attached tickets.") % rec.x_psm_name,
                partner_ids=[rec.x_psm_employee_id.user_id.partner_id.id] if rec.x_psm_employee_id.user_id else []
            )

    def action_psm_done(self):
        self.write({'x_psm_state': 'done'})
