from math import ceil
from datetime import timedelta
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from odoo.tools import float_round


class ApprovalRequest(models.Model):
    _inherit = "approval.request"

    # === Liên kết employee từ request_owner ===
    employee_id = fields.Many2one(
        'hr.employee',
        string="Employee",
        compute="_compute_employee_id",
        store=True,
        readonly=True,
    )

    # check điều kiện 
    has_detail_information = fields.Selection(related='category_id.has_detail_information')
    is_business_trip = fields.Selection(
        related='category_id.is_business_trip',
        readonly=True,
    )


    # === Detail information (READ ONLY – RELATED) ===

    employee_full_name = fields.Char(
        string="Employee Full Name",
        related="request_owner_id.name",
        readonly=True,
    )

    employee_email = fields.Char(
        string="Email",
        related="request_owner_id.email",
        readonly=True,
    )

    employee_phone = fields.Char(
        string="Phone Number",
        related="employee_id.mobile_phone",
        readonly=True,
    )

    employee_identity_id = fields.Char(
        string="Citizen ID",
        related="employee_id.identification_id",
        readonly=True,
        groups=False,
    )

    # Hotel

    travel_hotel_id = fields.Many2one(
        'travel.hotel',
        string='Hotel'
    )

    hotel_price = fields.Monetary(
        string='Hotel Price / Night',
        related='travel_hotel_id.price_per_night',
        readonly=True
    )

    currency_id = fields.Many2one(
        related='travel_hotel_id.currency_id',
        readonly=True
    )

    destination_province_id = fields.Many2one(
        'travel.province',
        string='Destination Province / City'
    )

    hotel_nights = fields.Integer(
        string="Hotel Nights",
        compute="_compute_hotel_nights",
        store=True,
        readonly=True,
    )

    estimated_hotel_cost = fields.Monetary(
        string="Estimated Hotel Cost",
    compute="_compute_estimated_hotel_cost",
    store=True,
    readonly=True,
    )

    # Flight
    airline_id = fields.Many2one(
        'approval.airline',
        string='Airline',
    )

    ticket_class_id = fields.Many2one(
        'approval.ticket.class',
        string='Ticket Class',
    )

    # === Liên kết giữa Travel Request và Advance Claim ===
    advance_request_ids = fields.One2many(
        'approval.request',
        'travel_request_id',
        string='Advance Requests',
    )

    advance_request_count = fields.Integer(
        string='Advance Request Count',
        compute='_compute_advance_request_count',
    )

    # === Budget Check Status ===
    budget_check_status = fields.Selection([
        ('draft', 'Draft'),
        ('in_budget', 'In Budget'),
        ('out_of_budget', 'Out of Budget')
    ], string='Budget Status', default='draft', tracking=True, readonly=True)


    @api.depends('request_owner_id')

    def _compute_employee_id(self):
        for request in self:
            request.employee_id = self.env['hr.employee'].search(
                [
                    ('user_id', '=', request.request_owner_id.id),
                    ('company_id', '=', request.company_id.id),
                ],
                limit=1
            )

    def _compute_advance_request_count(self):
        """Tính số lượng advance requests liên kết"""
        for request in self:
            request.advance_request_count = len(request.advance_request_ids)


    # === Validation theo Category ===
    def _check_detail_information_required(self):
        for request in self:
            if request.category_id.has_detail_information != 'required':
                continue

            missing = []

            if not request.employee_full_name:
                missing.append(_("Employee Full Name"))
            if not request.employee_email:
                missing.append(_("Email"))
            if not request.employee_phone:
                missing.append(_("Phone Number"))
            if not request.employee_identity_id:
                missing.append(_("Citizen ID"))

            if missing:
                raise ValidationError(_(
                    "This approval category requires complete employee information.\n"
                    "Please update your employee profile:\n- %s"
                ) % "\n- ".join(missing))

    def action_confirm(self):
        self._check_detail_information_required()
        return super().action_confirm()

    # === Ràng buộc 7 ngày cho yêu cầu công tác ===
    @api.constrains('date_start')
    def _check_business_trip_advance_days(self):
        """Yêu cầu công tác phải được tạo trước ít nhất 7 ngày so với ngày bắt đầu."""
        for request in self:
            if request.is_business_trip != 'yes':
                continue
            if not request.date_start:
                continue

            # Lấy ngày tạo (create_date) hoặc ngày hiện tại nếu chưa lưu
            creation_date = request.create_date.date() if request.create_date else fields.Date.context_today(request)
            start_date = request.date_start.date() if isinstance(request.date_start, fields.Datetime) else request.date_start

            # date_start là Datetime, cần lấy .date()
            if hasattr(request.date_start, 'date'):
                start_date = request.date_start.date()
            else:
                start_date = request.date_start

            diff = (start_date - creation_date).days
            if diff < 7:
                raise ValidationError(_(
                    "Yêu cầu công tác phải được tạo trước ít nhất 7 ngày so với ngày bắt đầu chuyến đi.\n"
                    "Ngày tạo: %s — Ngày bắt đầu: %s (chênh lệch: %d ngày)"
                ) % (creation_date, start_date, diff))

    # === Auto-populate ticket_purchaser_id từ category ===
    @api.onchange('category_id')
    def _onchange_category_id_ticket_purchaser(self):
        """Tự động gán người mua vé mặc định từ category."""
        if self.category_id and self.category_id.default_ticket_purchaser_id:
            self.ticket_purchaser_id = self.category_id.default_ticket_purchaser_id
        else:
            self.ticket_purchaser_id = False

    @api.onchange('destination_province_id')
    def _onchange_destination_province_id(self):
        # Reset hotel khi thay đổi province
        self.travel_hotel_id = False
    
    @api.onchange('is_business_trip')
    def _onchange_is_business_trip(self):
        if self.is_business_trip != 'yes':
            self.destination_province_id = False
            self.travel_hotel_id = False

    # Tính giá tiền
    @api.depends('date_start', 'date_end')
    def _compute_hotel_nights(self):
        for rec in self:
            rec.hotel_nights = 0

            if not rec.date_start or not rec.date_end:
                continue

            if rec.date_end <= rec.date_start:
                continue

            delta = rec.date_end - rec.date_start
            nights = ceil(delta.total_seconds() / 86400)

            rec.hotel_nights = nights

    @api.depends('hotel_nights', 'hotel_price')
    def _compute_estimated_hotel_cost(self):
        for rec in self:
            rec.estimated_hotel_cost = 0.0

            if rec.hotel_nights and rec.hotel_price:
                rec.estimated_hotel_cost = float_round(
                    rec.hotel_nights * rec.hotel_price,
                    precision_rounding=rec.currency_id.rounding
                    if rec.currency_id else 0.01
                )

    @api.constrains('date_start', 'date_end')
    def _check_date_range(self):
        for rec in self:
            if rec.date_start and rec.date_end and rec.date_end <= rec.date_start:
                raise ValidationError(_("End date must be later than start date."))

    def action_create_advance_request(self):
        self.ensure_one()

        # Tìm category có is_advance_claim = 'yes'
        advance_category = self.env['approval.category'].search([
            ('is_advance_claim', '=', 'yes')
        ], limit=1)

        return {
            'type': 'ir.actions.act_window',
            'name': _('Tạo phiếu tạm ứng'),
            'res_model': 'approval.request',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_request_owner_id': self.request_owner_id.id,
                'default_category_id': advance_category.id if advance_category else False,
                'default_amount': self.estimated_hotel_cost,
                'default_travel_request_id': self.id,
            }
        }

    def action_view_advance_requests(self):
        """Mở danh sách advance requests liên kết với travel request này"""
        self.ensure_one()
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Advance Requests'),
            'res_model': 'approval.request',
            'view_mode': 'list,form',
            'domain': [('id', 'in', self.advance_request_ids.ids)],
            'context': {
                'default_travel_request_id': self.id,
            }
        }

    # === Auto Budget Check on Create ===
    @api.model_create_multi
    def create(self, vals_list):
        """Auto check budget when creating travel request"""
        records = super().create(vals_list)
        
        for record in records:
            # Auto check budget for travel requests
            if record.category_id.has_detail_information == 'required':
                record._auto_check_budget()
        
        return records

    def _auto_check_budget(self):
        """Auto check budget and update status - placeholder returns True"""
        self.ensure_one()
        
        # Call budget check function (currently always returns True)
        if self._check_budget():
            self.budget_check_status = 'in_budget'
        else:
            self.budget_check_status = 'out_of_budget'

    # === Ticket Purchase Workflow ===
    ticket_purchaser_id = fields.Many2one(
        'res.users',
        string="Ticket Purchaser",
        tracking=True,
    )

    ticket_attachment_ids = fields.Many2many(
        'ir.attachment',
        string="Ticket Attachments",
    )

    request_status = fields.Selection(
        selection_add=[('completed', 'Completed')],
        ondelete={'completed': 'set default'}
    )

    is_ticket_purchased = fields.Boolean(
        string="Tickets Purchased",
        default=False,
        readonly=True,
        tracking=True
    )

    def action_approve(self, approver=None):
        super().action_approve(approver=approver)
        # Notify ticket purchaser if request is fully approved
        for request in self:
            if request.request_status == 'approved' and request.is_business_trip == 'yes' and request.ticket_purchaser_id:
                # Schedule a To-Do activity instead of just a message
                request.activity_schedule(
                    'mail.mail_activity_data_todo',
                    user_id=request.ticket_purchaser_id.id,
                    summary=_("Mua vé máy bay - %s") % request.name,
                    note=_("Yêu cầu đi công tác đã được duyệt. Vui lòng tiến hành mua vé máy bay."),
                )
                # Also post a message for log history
                request.message_post(
                    body=_("Đã giao việc mua vé cho %s") % request.ticket_purchaser_id.name,
                    partner_ids=[request.ticket_purchaser_id.partner_id.id],
                )

    def action_confirm_ticket_purchase(self):
        """Ticket Purchaser confirms tickets are ready"""
        for request in self:
            if not request.ticket_attachment_ids:
                raise ValidationError(_("Please attach the tickets before confirming."))
            
            request.write({'is_ticket_purchased': True})
            
            # Mark purchaser's activity as done
            request.activity_feedback(['mail.mail_activity_data_todo'])

            # Notify the requester to complete
            request.activity_schedule(
                'mail.mail_activity_data_todo',
                user_id=request.request_owner_id.id,
                summary=_("Xác nhận vé và Hoàn thành - %s") % request.name,
                note=_("Vé máy bay đã được mua. Vui lòng kiểm tra và ấn Hoàn thành."),
            )

            request.message_post(
                body=_("Đã mua vé xong. Đã gửi thông báo cho người yêu cầu xác nhận."),
                partner_ids=[request.request_owner_id.partner_id.id],
            )

    def action_complete(self):
        """Requester marks the request as completed"""
        for request in self:
            # Check permission: Owner or Manager/Admin
            # Since this is a button action, basic view visibility handles some, but model check is safer.
            # Allowing simple check here or relying on view invisibility.
            
            request.write({'request_status': 'completed'})
            
            # Mark requester's activity as done
            request.activity_feedback(['mail.mail_activity_data_todo'])
            
            request.message_post(
                body=_("Yêu cầu đã được xác nhận hoàn thành bởi %s") % self.env.user.name,
            )

    def _check_budget(self):
        """Budget check logic - placeholder always returns True"""
        return True

