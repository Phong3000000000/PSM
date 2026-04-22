from odoo import models, fields

class HrExpense(models.Model):
    _inherit = 'hr.expense'

    x_psm_0201_travel_request_id = fields.Many2one(
        'x_psm_travel_request', 
        string='Travel Request', 
        domain="[('x_psm_state', 'in', ['in_progress', 'done']), ('x_psm_traveler_ids.x_psm_employee_id', '=', employee_id)]"
    )
