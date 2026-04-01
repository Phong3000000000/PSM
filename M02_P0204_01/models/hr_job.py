# -*- coding: utf-8 -*-
from odoo import models, fields, api

class HrJob(models.Model):
    _inherit = 'hr.job'
    
    recruitment_type = fields.Selection([
        ('store', 'Khối Cửa Hàng'),
        ('office', 'Khối Văn Phòng'),
    ], string='Loại Tuyển Dụng', help='Phân loại job position theo khối')
    
    def action_open_applicants(self):
        """Open applicant kanban view for this job position"""
        self.ensure_one()
        
        # Build domain with job_id
        domain = [('job_id', '=', self.id)]
        
        # Add recruitment_type to domain for proper stage filtering
        # This ensures _read_group_stage_ids filters stages correctly
        if self.recruitment_type:
            domain.append(('recruitment_type', '=', self.recruitment_type))
        
        return {
            'name': f'Ứng Viên - {self.name}',
            'type': 'ir.actions.act_window',
            'res_model': 'hr.applicant',
            'view_mode': 'kanban,list,form,pivot,graph,calendar,activity',
            'domain': domain,
            'context': {
                'default_job_id': self.id,
                'default_recruitment_type': self.recruitment_type,
            },
        }
