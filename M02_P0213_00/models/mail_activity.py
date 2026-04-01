# -*- coding: utf-8 -*-
from odoo import models, fields, api, _


class MailActivity(models.Model):
    _inherit = 'mail.activity'

    # Ensure active field is visible (may already exist in 0214 if installed together)
    active = fields.Boolean(default=True, string="Active")

    # OPS specific display state (parallel to rst_display_state in 0214)
    ops_display_state = fields.Selection([
        ('pending', 'Pending'),
        ('overdue', 'Overdue'),
        ('done', 'Done'),
    ], string='Trạng thái', compute='_compute_ops_display_state')

    @api.depends('active', 'date_deadline', 'state')
    def _compute_ops_display_state(self):
        """active=False => Done, trễ hạn => Overdue, còn lại => Pending"""
        today = fields.Date.today()
        for activity in self:
            if not activity.active:
                activity.ops_display_state = 'done'
            elif activity.date_deadline and activity.date_deadline < today:
                activity.ops_display_state = 'overdue'
            else:
                activity.ops_display_state = 'pending'

    def unlink(self):
        """
        Ngăn xóa activities của OPS Offboarding.
        Thay vào đó archive (active=False) để giữ lại lịch sử checklist.
        """
        ops_cat = self.env.ref('M02_P0213_00.approval_category_resignation', raise_if_not_found=False)

        if not ops_cat:
            return super().unlink()

        ops_activities = self.filtered(
            lambda a: a.res_model in ['hr.employee', 'approval.request']
            and self._is_ops_offboarding_activity(a, ops_cat)
        )
        others = self - ops_activities

        if others:
            super(MailActivity, others).unlink()

        for activity in ops_activities:
            if activity.active:
                activity.sudo().write({'active': False})
                # Trigger recompute trên approval.request liên quan
                self._trigger_ops_recompute(activity, ops_cat)

        return True

    def _is_ops_offboarding_activity(self, activity, ops_cat):
        """Check if activity belongs to an OPS offboarding request"""
        if activity.res_model == 'approval.request':
            req = self.env['approval.request'].sudo().browse(activity.res_id)
            return req.exists() and req.category_id == ops_cat
        elif activity.res_model == 'hr.employee':
            req = self.env['approval.request'].sudo().search([
                ('employee_id', '=', activity.res_id),
                ('category_id', '=', ops_cat.id),
            ], limit=1)
            return bool(req)
        return False

    def _trigger_ops_recompute(self, activity, ops_cat):
        """Trigger recompute on OPS approval.request after activity archive"""
        if activity.res_model == 'approval.request':
            req = self.env['approval.request'].sudo().browse(activity.res_id)
            if req.exists():
                req.modified(['employee_activity_ids'])
        elif activity.res_model == 'hr.employee':
            reqs = self.env['approval.request'].sudo().search([
                ('employee_id', '=', activity.res_id),
                ('category_id', '=', ops_cat.id),
            ])
            reqs.modified(['employee_activity_ids'])

    def _action_done(self, feedback=False, attachment_ids=False):
        """
        Override để trigger recompute checklist sau khi Mark Done.
        """
        ops_cat = self.env.ref('M02_P0213_00.approval_category_resignation', raise_if_not_found=False)

        res = super()._action_done(feedback=feedback, attachment_ids=attachment_ids)

        if not ops_cat:
            return res

        for activity in self.sudo():
            is_ops_model = activity.res_model in ['hr.employee', 'approval.request']
            if not is_ops_model or not activity.res_id:
                continue

            domain = [
                ('request_status', '=', 'approved'),
                ('category_id', '=', ops_cat.id),
            ]
            if activity.res_model == 'hr.employee':
                domain.append(('employee_id', '=', activity.res_id))
            else:
                domain.append(('id', '=', activity.res_id))

            requests = self.env['approval.request'].sudo().search(domain)

            for req in requests:
                pending_count = self.env['mail.activity'].sudo().search_count([
                    ('active', '=', True),
                    '|',
                    '&', ('res_model', '=', 'approval.request'), ('res_id', '=', req.id),
                    '&', ('res_model', '=', 'hr.employee'), ('res_id', '=', req.employee_id.id if req.employee_id else 0),
                ])

                if pending_count == 0 and req.is_plan_launched:
                    req.message_post(body=_("Hệ thống: Tất cả các công việc trong checklist đã được hoàn thành."))

                req.sudo().modified(['employee_activity_ids'])

        return res
