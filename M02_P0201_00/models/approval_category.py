from odoo import fields, models

CATEGORY_SELECTION = [
    ('required', 'Required'),
    ('optional', 'Optional'),
    ('no', 'None')]

class ApprovalCategory(models.Model):
    _inherit = "approval.category"

    has_detail_information = fields.Selection(
        CATEGORY_SELECTION,
        string="Has Detail Information",
        default="no",
        required=True,
        help="Require employee detailed personal information on approval request."
    )

    is_business_trip = fields.Selection(
        [('yes', 'YES'), ('no', 'NO')],
        string="Is Business Trip",
        default="no",
        required=True,
        help="Require employee detailed personal information on approval request.",
    )

    default_ticket_purchaser_id = fields.Many2one(
        'res.users',
        string="Default Ticket Purchaser",
        help="Người mua vé mặc định. Khi tạo yêu cầu công tác, giá trị này sẽ tự động gán vào phiếu.",
    )