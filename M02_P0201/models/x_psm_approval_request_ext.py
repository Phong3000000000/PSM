from odoo import models, fields, api

class ApprovalRequest(models.Model):
    _inherit = 'approval.request'

    @api.depends('approver_ids.status', 'approver_ids.required')
    def _compute_request_status(self):
        super(ApprovalRequest, self)._compute_request_status()
        for rec in self:
            # We use sudo() to ensure the status update happens even if the approver 
            # doesn't have write access to the travel request.
            travel_req = self.env['x_psm_travel_request'].sudo().search([('x_psm_approval_request_id', '=', rec.id)], limit=1)
            if travel_req:
                if rec.request_status == 'approved':
                    travel_req.x_psm_state = 'approved'
                    travel_req.x_psm_date_start = rec.date_start
                    travel_req.x_psm_date_end = rec.date_end
                    travel_req._notify_admin_for_booking()
                elif rec.request_status == 'refused':
                    travel_req.x_psm_state = 'refused'
                elif rec.request_status == 'pending':
                    travel_req.x_psm_state = 'submitted'
