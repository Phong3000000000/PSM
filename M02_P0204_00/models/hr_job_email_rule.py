# -*- coding: utf-8 -*-
from odoo import models, fields, api, exceptions, _

class HrJobEmailRule(models.Model):
    _name = 'hr.job.email.rule'
    _description = 'Cấu hình Email theo Sự kiện/Vòng của Job'
    _order = 'sequence, id'

    job_id = fields.Many2one('hr.job', string='Vị trí tuyển dụng', ondelete='cascade', required=True)
    active = fields.Boolean(string='Active', default=True)
    sequence = fields.Integer(string='Sequence', default=10)
    
    rule_type = fields.Selection([
        ('stage', 'Theo Vòng (Stage)'),
        ('event', 'Theo Sự kiện (Event)')
    ], string='Loại cấu hình', required=True, default='event')

    stage_id = fields.Many2one('hr.recruitment.stage', string='Vòng / Trạng thái')
    event_code = fields.Selection([
        ('survey_invite', 'Mời làm bài khảo sát'),
        ('interview_invitation', 'Mời phỏng vấn'),
        ('interview_slot_confirmed', 'Xác nhận lịch phỏng vấn'),
        ('reject', 'Từ chối (Tiêu chuẩn)'),
        ('oje_reject', 'Từ chối (Cần ghi rõ lý do)'),
        ('hired', 'Tuyển dụng / Chúc mừng')
    ], string='Sự kiện')

    template_id = fields.Many2one('mail.template', string='Email Template', domain=[('model', '=', 'hr.applicant')], required=True)

    @api.onchange('rule_type')
    def _onchange_rule_type(self):
        if self.rule_type == 'stage':
            self.event_code = False
        else:
            self.stage_id = False

    def action_open_template(self):
        self.ensure_one()
        if not self.template_id:
            raise exceptions.UserError(_('Chưa có email template nào được chọn.'))
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'mail.template',
            'res_id': self.template_id.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_clone_default_template(self):
        self.ensure_one()
        if not self.template_id:
            raise exceptions.UserError(_('Vui lòng chọn một Template có sẵn để clone.'))
        
        trigger_name = dict(self._fields['event_code'].selection).get(self.event_code) if self.rule_type == 'event' else self.stage_id.name
        new_name = f"[{self.job_id.name}][{trigger_name}] {self.template_id.name}"
        
        new_template = self.template_id.copy(default={'name': new_name})
        self.template_id = new_template.id

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Thành công',
                'message': f'Đã tạo bản sao template: {new_name}',
                'type': 'success',
                'sticky': False,
            }
        }
