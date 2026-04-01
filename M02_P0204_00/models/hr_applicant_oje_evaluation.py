# -*- coding: utf-8 -*-
from odoo import models, fields, api

class HrApplicantOjeEvaluation(models.Model):
    _name = 'hr.applicant.oje.evaluation'
    _description = 'Applicant OJE Evaluation'
    _order = 'id desc'

    applicant_id = fields.Many2one('hr.applicant', string='Applicant', ondelete='cascade', required=True)
    job_id = fields.Many2one('hr.job', string='Job Position', required=True)
    
    evaluator_user_id = fields.Many2one('res.users', string='Evaluator (User)')
    evaluator_partner_id = fields.Many2one('res.partner', string='Evaluator (Partner)', related='evaluator_user_id.partner_id', store=True)
    
    state = fields.Selection([
        ('new', 'Mới'),
        ('in_progress', 'Đang thực hiện'),
        ('done', 'Đã hoàn thành'),
    ], string='Trạng thái', default='new', required=True)
    
    pass_score_snapshot = fields.Float(string='Điểm đạt (Snapshot)', help='Snapshot của oje_pass_score từ hr.job lúc bắt đầu.')
    total_score = fields.Float(string='Tổng điểm', compute='_compute_total_score', store=True)
    
    result = fields.Selection([
        ('pass', 'Đạt'),
        ('fail', 'Không đạt'),
    ], string='Kết quả', compute='_compute_result', store=True)
    
    submitted_at = fields.Datetime(string='Thời gian hoàn thành')
    
    line_ids = fields.One2many('hr.applicant.oje.evaluation.line', 'evaluation_id', string='Chi tiết đánh giá')

    def action_submit(self):
        for rec in self:
            rec.write({
                'state': 'done',
                'submitted_at': fields.Datetime.now(),
            })
            # Sync back to applicant
            rec.applicant_id.sudo().action_apply_oje_evaluation_result()
            # Thông báo cho RGM quản lý của Người đánh giá
            rec._schedule_oje_completion_activity()

    def _schedule_oje_completion_activity(self):
        for rec in self:
            if not rec.applicant_id:
                continue
                
            evaluator_user = rec.evaluator_user_id or self.env.user
            employee = self.env['hr.employee'].sudo().search([('user_id', '=', evaluator_user.id)], limit=1)
            
            if employee and employee.parent_id and employee.parent_id.user_id:
                rgm_user = employee.parent_id.user_id
                
                result_str = 'Đạt' if rec.result == 'pass' else 'Không đạt'
                note = f"""
                    <p><b>Người đánh giá (DM):</b> {evaluator_user.name}</p>
                    <p><b>Kết quả OJE:</b> {result_str} ({rec.total_score}/{rec.pass_score_snapshot})</p>
                    <p>Vui lòng xem hồ sơ ứng viên và quyết định bước tiếp theo.</p>
                """
                
                rec.applicant_id.sudo().activity_schedule(
                    'mail.mail_activity_data_todo',
                    user_id=rgm_user.id,
                    summary=f'Xem xét kết quả OJE: {rec.applicant_id.partner_name or "Ứng viên"}',
                    note=note,
                    date_deadline=fields.Date.context_today(rec)
                )

    @api.depends('line_ids.awarded_score')
    def _compute_total_score(self):
        for rec in self:
            rec.total_score = sum(rec.line_ids.mapped('awarded_score'))

    @api.depends('total_score', 'pass_score_snapshot')
    def _compute_result(self):
        for rec in self:
            if rec.state == 'done':
                rec.result = 'pass' if rec.total_score >= rec.pass_score_snapshot else 'fail'
            else:
                rec.result = False

class HrApplicantOjeEvaluationLine(models.Model):
    _name = 'hr.applicant.oje.evaluation.line'
    _description = 'Applicant OJE Evaluation Line'
    _order = 'sequence, id'

    evaluation_id = fields.Many2one('hr.applicant.oje.evaluation', string='Evaluation', ondelete='cascade', required=True)
    template_line_id = fields.Many2one('hr.job.oje.config.line', string='Template Line', ondelete='set null')
    
    sequence = fields.Integer(string='Sequence', default=10)
    name = fields.Char(string='Tiêu chí', required=True)
    field_type = fields.Selection([
        ('text', 'Text (Comment + Manual Score)'),
        ('radio', 'Radio (Select one)'),
        ('checkbox', 'Checkbox (Yes/No)'),
    ], string='Field Type', required=True)
    
    # Input values
    text_value = fields.Text(string='Nhận xét')
    text_score = fields.Float(string='Điểm (Nhập tay)')
    text_max_score = fields.Float(string='Điểm tối đa')
    
    checkbox_value = fields.Boolean(string='Checkbox Value')
    checkbox_score = fields.Float(string='Điểm (Checkbox)')
    
    selected_option_id = fields.Many2one('hr.job.oje.config.option', string='Lựa chọn')
    selected_option_score = fields.Float(string='Điểm (Radio)')
    
    awarded_score = fields.Float(string='Điểm đạt được', compute='_compute_awarded_score', store=True)

    @api.depends('field_type', 'text_score', 'checkbox_value', 'checkbox_score', 'selected_option_id', 'selected_option_id.score')
    def _compute_awarded_score(self):
        for line in self:
            if line.field_type == 'text':
                line.awarded_score = line.text_score
            elif line.field_type == 'checkbox':
                line.awarded_score = line.checkbox_score if line.checkbox_value else 0.0
            elif line.field_type == 'radio':
                line.awarded_score = line.selected_option_id.score if line.selected_option_id else 0.0
            else:
                line.awarded_score = 0.0
