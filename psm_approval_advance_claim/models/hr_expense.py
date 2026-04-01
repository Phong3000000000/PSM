from odoo import fields, models


class HrExpense(models.Model):
    _inherit = 'hr.expense'

    # Link to advance request
    advance_request_id = fields.Many2one(
        'approval.request',
        string='Advance Request',
        ondelete='set null',
        index=True
    )

    # Link to travel request (via advance)
    travel_request_id = fields.Many2one(
        'approval.request',
        string='Travel Request',
        related='advance_request_id.travel_request_id',
        store=True
    )
