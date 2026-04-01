# -*- coding: utf-8 -*-
from odoo import models, fields, api, _

class MailActivity(models.Model):
    _inherit = 'mail.activity'

    active = fields.Boolean(default=True, string="Active")

    # RST Specific display state
    rst_display_state = fields.Selection([
        ('pending', 'Pending'),
        ('overdue', 'Overdue'),
        ('done', 'Done'),
    ], string='Trạng thái RST', compute='_compute_rst_display_state')

    @api.depends('active', 'date_deadline', 'state')
    def _compute_rst_display_state(self):
        """Logic: active=False => Done, trễ hạn => Overdue, còn lại => Pending"""
        today = fields.Date.today()
        for activity in self:
            if not activity.active:
                activity.rst_display_state = 'done'
            elif activity.date_deadline and activity.date_deadline < today:
                activity.rst_display_state = 'overdue'
            else:
                activity.rst_display_state = 'pending'

    def unlink(self):
        """
        Ngăn việc xóa các hoạt động liên quan đến quy trình RST Offboarding.
        Thay vào đó, chỉ ẩn đi (active=False) để giữ lại lịch sử.
        """
        rst_activities = self.filtered(lambda a: a.res_model in ['hr.employee', 'approval.request'])
        others = self - rst_activities
        
        if others:
            super(MailActivity, others).unlink()
        
        for activity in rst_activities:
            # Chuyển sang active=False thay vì xóa
            # Sử dụng write trực tiếp trên record để đảm bảo bypass logic cache nếu cần
            if activity.active:
                activity.sudo().write({'active': False})
                # Tìm approval request liên quan để trigger recompute list
                if activity.res_model == 'approval.request':
                    req = self.env['approval.request'].sudo().browse(activity.res_id)
                    if req.exists():
                        req.modified(['rst_checklist_activity_ids'])
                elif activity.res_model == 'hr.employee':
                    # Search đơn tương ứng với nhân viên
                    rst_cat = self.env.ref('M02_P0214_00.approval_category_resignation', raise_if_not_found=False)
                    if rst_cat:
                        reqs = self.env['approval.request'].sudo().search([
                            ('employee_id', '=', activity.res_id),
                            ('category_id', '=', rst_cat.id)
                        ])
                        reqs.modified(['rst_checklist_activity_ids'])
                
        return True

    def _action_done(self, feedback=False, attachment_ids=False):
        """
        Override to check if all offboarding activities are completed after marking one as done.
        """
        # 1. Perform standard done action (which might delete or archive the activity)
        res = super(MailActivity, self)._action_done(feedback=feedback, attachment_ids=attachment_ids)

        # 2. Check for related Resignation Process
        # Since 'self' might be deleted/archived, we rely on the context or pre-fetched data if needed.
        # However, _action_done usually returns the messages created.
        
        # We need to look at what we just processed. 
        # But 'self' is the recordset. If it's unlinked, we can't read it?
        # Standard Odoo _action_done typically marks active=False or unlinks.
        
        # Strategy: Iterate self BEFORE super to get IDs/res_ids, 
        # but the check must happen AFTER to see if remaining count is 0.
        
        # Actually, self in the method body still holds the IDs even if deleted in DB (cache).
        # We care about the res_id (Employee) and res_model.
        
        for activity in self.sudo():
            # Kiểm tra cho cả hr.employee (cũ) và approval.request (mới)
            is_rst_model = (activity.res_model == 'hr.employee') or (activity.res_model == 'approval.request')
            if is_rst_model and activity.res_id:
                res_id = activity.res_id
                res_model = activity.res_model
                
                # Tìm đơn nghỉ việc RST tương ứng
                rst_cat = self.env.ref('M02_P0214_00.approval_category_resignation', raise_if_not_found=False)
                if not rst_cat:
                    continue

                domain = [
                    ('request_status', '=', 'approved'),
                    ('category_id', '=', rst_cat.id)
                ]
                if res_model == 'hr.employee':
                    domain.append(('employee_id', '=', res_id))
                else:
                    domain.append(('id', '=', res_id))
                
                requests = self.env['approval.request'].sudo().search(domain)
                
                for req in requests:
                    # Kiểm tra xem còn bất kỳ activity nào CÒN HOẠT ĐỘNG (chưa xong) không
                    # Lưu ý: Thêm điều kiện active=True vì ta đã chặn unlink ở trên
                    pending_count = self.env['mail.activity'].sudo().search_count([
                        ('active', '=', True),
                        '|',
                        '&', ('res_model', '=', 'approval.request'), ('res_id', '=', req.id),
                        '&', ('res_model', '=', 'hr.employee'), ('res_id', '=', req.employee_id.id if req.employee_id else 0),
                    ])
                    
                    # ONLY mark as completed if:
                    # 1. No pending activities remain (pending_count == 0)
                    # 2. AND offboarding plan has actually been launched (is_plan_launched=True)
                    # This prevents premature completion when approve is first clicked
                    if pending_count == 0 and req.is_plan_launched:
                        # Tất cả đã xong! 
                        req.sudo().all_activities_completed = True
                        if hasattr(req, 'action_checklist_completed'):
                            req.action_checklist_completed()
                        else:
                            req.message_post(body=_("Hệ thống: Tất cả các công việc trong checklist đã được hoàn thành."))
                    
                    # Buộc Odoo xóa cache của field rst_checklist_activity_ids trên record này
                    # để đảm bảo view được làm mới với cả các record inactive mới cập nhật
                    req.sudo().modified(['rst_checklist_activity_ids'])

        return res
