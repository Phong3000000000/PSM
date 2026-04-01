# -*- coding: utf-8 -*-
from odoo import models, fields, api, _


class HrLeaveExt(models.Model):
    """
    Mở rộng hr.leave để đồng bộ với Planning khi nghỉ phép được duyệt
    Step 19-22: Nghỉ phép & Đồng bộ
    """
    _inherit = 'hr.leave'

    def _action_validate(self, mark_as_main_responsible=True):
        """
        Override: Sau khi duyệt nghỉ phép, tự động hủy các ca đã đăng ký
        trong khoảng thời gian nghỉ
        """
        result = super()._action_validate(mark_as_main_responsible=mark_as_main_responsible)
        
        for leave in self:
            leave._sync_with_planning()
        
        return result

    def _sync_with_planning(self):
        """
        Đồng bộ nghỉ phép với Planning:
        - Tìm các slot trong khoảng thời gian nghỉ
        - Gửi cảnh báo cho RGM
        - Reset slot để người khác đăng ký
        """
        self.ensure_one()
        
        if not self.employee_id or not self.employee_id.resource_id:
            return
        
        PlanningSlot = self.env['planning.slot']
        
        # Tìm các slot của nhân viên trong khoảng thời gian nghỉ
        slots = PlanningSlot.search([
            ('resource_id', '=', self.employee_id.resource_id.id),
            ('start_datetime', '>=', self.date_from),
            ('end_datetime', '<=', self.date_to),
            ('approval_state', 'in', ['to_approve', 'approved']),
        ])
        
        if not slots:
            return
        
        # Notify RGM về việc nghỉ phép ảnh hưởng đến lịch
        manager = self.employee_id.parent_id.user_id if self.employee_id.parent_id else None
        if not manager:
            manager = self.env.ref('base.user_admin', raise_if_not_found=False)
        
        for slot in slots:
            # Lưu thông tin cũ
            old_employee = slot.resource_id.name if slot.resource_id else 'N/A'
            
            # Reset slot
            slot.write({
                'resource_id': False,
                'approval_state': 'open',
                'registered_by': False,
                'registered_date': False,
            })
            
            # Post message về việc reset do nghỉ phép
            slot.message_post(
                body=_('Ca này đã được mở lại vì nhân viên %s xin nghỉ phép từ %s đến %s.') % (
                    old_employee,
                    self.date_from,
                    self.date_to
                ),
                message_type='notification'
            )
        
        # Gửi activity cho RGM
        if manager:
            activity_type = self.env.ref('mail.mail_activity_data_todo', raise_if_not_found=False)
            if activity_type:
                for slot in slots:
                    model_ref = self.env['ir.model'].sudo().search([('model', '=', 'planning.slot')], limit=1)
                    if model_ref:
                        self.env['mail.activity'].create({
                            'activity_type_id': activity_type.id,
                            'summary': 'Cần điền người cho ca %s' % slot.start_datetime.strftime('%d/%m %H:%M'),
                            'note': 'Nhân viên %s nghỉ phép. Ca này cần được phân bổ lại.' % self.employee_id.name,
                            'res_id': slot.id,
                            'res_model_id': model_ref.id,
                            'user_id': manager.id,
                        })
