# -*- coding: utf-8 -*-
from odoo import models, fields, api, exceptions, _


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

    template_scope = fields.Selection([
        ('store_staff', 'Store Staff'),
        ('store_management', 'Store Management'),
        ('legacy', 'Legacy'),
    ], string='Template Scope', default='legacy', index=True)
    template_version = fields.Char(string='Template Version')

    trial_date = fields.Date(string='Ngày thử việc')
    trial_time = fields.Char(string='Thời gian thử việc')
    restaurant_name = fields.Char(string='Nhà hàng')
    shift_schedule = fields.Char(string='OJE Dates/Shift Sched')
    operation_consultant_name = fields.Char(string='Operation Consultant')

    overall_comments = fields.Text(string='Overall Comments')
    interviewer_note = fields.Text(string='Ghi chú từ người phỏng vấn')
    manager_signature_name = fields.Char(string='Quản lý ký và ghi tên')

    # Staff-only
    staff_decision = fields.Selection([
        ('reject', 'Từ chối'),
        ('hire', 'Đề nghị tuyển'),
        ('other_position', 'Đề nghị vị trí khác'),
    ], string='Kết luận (Staff)')
    staff_ni_count = fields.Integer(string='NI Count', compute='_compute_staff_counters', store=True)
    staff_gd_count = fields.Integer(string='GD Count', compute='_compute_staff_counters', store=True)
    staff_ex_count = fields.Integer(string='EX Count', compute='_compute_staff_counters', store=True)
    staff_os_count = fields.Integer(string='OS Count', compute='_compute_staff_counters', store=True)
    has_any_ni = fields.Boolean(string='Có NI', compute='_compute_staff_counters', store=True)

    # Management-only
    management_overall_rating = fields.Integer(string='Overall Rating')
    management_final_display = fields.Selection([
        ('hire', 'HIRE'),
        ('reject', 'REJECT'),
    ], string='Applicant For', compute='_compute_management_final_display', store=True)

    pass_score_snapshot = fields.Float(string='Điểm đạt (Snapshot)', help='Snapshot của oje_pass_score từ hr.job lúc bắt đầu.')
    total_score = fields.Float(string='Tổng điểm', compute='_compute_total_score', store=True)

    result = fields.Selection([
        ('pass', 'Đạt'),
        ('fail', 'Không đạt'),
    ], string='Kết quả', compute='_compute_result', store=True)
    fail_reason = fields.Text(string='Lý do không đạt')

    submitted_at = fields.Datetime(string='Thời gian hoàn thành')

    section_ids = fields.One2many('hr.applicant.oje.evaluation.section', 'evaluation_id', string='Sections')
    line_ids = fields.One2many('hr.applicant.oje.evaluation.line', 'evaluation_id', string='Chi tiết đánh giá')

    @api.depends('template_scope', 'line_ids.staff_rating', 'line_ids.line_kind', 'line_ids.is_active')
    def _compute_staff_counters(self):
        for rec in self:
            if rec.template_scope != 'store_staff':
                rec.staff_ni_count = 0
                rec.staff_gd_count = 0
                rec.staff_ex_count = 0
                rec.staff_os_count = 0
                rec.has_any_ni = False
                continue

            staff_lines = rec.line_ids.filtered(lambda l: l.is_active and l.line_kind == 'staff_question')
            rec.staff_ni_count = len(staff_lines.filtered(lambda l: l.staff_rating == 'ni'))
            rec.staff_gd_count = len(staff_lines.filtered(lambda l: l.staff_rating == 'gd'))
            rec.staff_ex_count = len(staff_lines.filtered(lambda l: l.staff_rating == 'ex'))
            rec.staff_os_count = len(staff_lines.filtered(lambda l: l.staff_rating == 'os'))
            rec.has_any_ni = rec.staff_ni_count > 0

    @api.depends('template_scope', 'management_overall_rating')
    def _compute_management_final_display(self):
        for rec in self:
            if rec.template_scope != 'store_management':
                rec.management_final_display = False
            else:
                rec.management_final_display = 'hire' if (rec.management_overall_rating or 0) >= 3 else 'reject'

    def _validate_before_submit(self):
        for rec in self:
            if rec.template_scope == 'store_staff':
                staff_lines = rec.line_ids.filtered(lambda l: l.is_active and l.line_kind == 'staff_question')
                missing_rating = staff_lines.filtered(lambda l: not l.staff_rating)
                if missing_rating:
                    raise exceptions.UserError(_('Vui lòng chấm đủ NI/GD/EX/OS cho tất cả dòng đánh giá Staff.'))
                if not rec.staff_decision:
                    raise exceptions.UserError(_('Vui lòng chọn kết luận cuối cùng cho form Staff.'))

            elif rec.template_scope == 'store_management':
                management_lines = rec.line_ids.filtered(lambda l: l.is_active and l.line_kind == 'management_task')
                missing_management_score = management_lines.filtered(
                    lambda l: not l.management_score or l.management_score < 1 or l.management_score > 5
                )
                if missing_management_score:
                    raise exceptions.UserError(_('Vui lòng nhập điểm 1..5 cho toàn bộ task của form Management.'))

                xfactor_lines = rec.line_ids.filtered(lambda l: l.is_active and l.line_kind == 'management_xfactor')
                missing_xfactor = xfactor_lines.filtered(lambda l: not l.yes_no_answer)
                if missing_xfactor:
                    raise exceptions.UserError(_('Vui lòng chọn Y/N cho toàn bộ dòng X-Factor.'))

                if not rec.management_overall_rating or rec.management_overall_rating < 1 or rec.management_overall_rating > 5:
                    raise exceptions.UserError(_('Overall Rating phải nằm trong khoảng 1..5.'))

                dimension_sections = rec.section_ids.filtered(
                    lambda s: s.is_active and s.section_kind == 'management_dimension'
                )
                invalid_section_rating = dimension_sections.filtered(
                    lambda s: not s.section_rating or s.section_rating < 1 or s.section_rating > 5
                )
                if invalid_section_rating:
                    raise exceptions.UserError(_('Vui lòng nhập đầy đủ section rating (1..5) cho 3 dimension chính.'))

    def action_submit(self):
        for rec in self:
            if rec.state == 'done':
                continue

            rec._validate_before_submit()
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

                if rec.template_scope == 'store_staff':
                    score_display = f"NI:{rec.staff_ni_count} GD:{rec.staff_gd_count} EX:{rec.staff_ex_count} OS:{rec.staff_os_count}"
                elif rec.template_scope == 'store_management':
                    score_display = f"Overall: {rec.management_overall_rating or 0}/5"
                else:
                    score_display = f"{rec.total_score}/{rec.pass_score_snapshot}"

                result_str = 'Đạt' if rec.result == 'pass' else 'Không đạt'
                note = f"""
                    <p><b>Người đánh giá (DM):</b> {evaluator_user.name}</p>
                    <p><b>Kết quả OJE:</b> {result_str} ({score_display})</p>
                    <p>Vui lòng xem hồ sơ ứng viên và quyết định bước tiếp theo.</p>
                """

                rec.applicant_id.sudo().activity_schedule(
                    'mail.mail_activity_data_todo',
                    user_id=rgm_user.id,
                    summary=f'Xem xét kết quả OJE: {rec.applicant_id.partner_name or "Ứng viên"}',
                    note=note,
                    date_deadline=fields.Date.context_today(rec)
                )

    @api.depends(
        'template_scope',
        'line_ids.awarded_score',
        'staff_gd_count',
        'staff_ex_count',
        'staff_os_count',
        'management_overall_rating',
    )
    def _compute_total_score(self):
        for rec in self:
            if rec.template_scope == 'store_staff':
                rec.total_score = rec.staff_gd_count + (rec.staff_ex_count * 2) + (rec.staff_os_count * 3)
            elif rec.template_scope == 'store_management':
                rec.total_score = float(rec.management_overall_rating or 0)
            else:
                rec.total_score = sum(rec.line_ids.mapped('awarded_score'))

    @api.depends(
        'state',
        'template_scope',
        'total_score',
        'pass_score_snapshot',
        'staff_decision',
        'has_any_ni',
        'management_overall_rating',
    )
    def _compute_result(self):
        for rec in self:
            if rec.state != 'done':
                rec.result = False
                continue

            if rec.template_scope == 'store_staff':
                rec.result = 'pass' if (rec.staff_decision == 'hire' and not rec.has_any_ni) else 'fail'
            elif rec.template_scope == 'store_management':
                rec.result = 'pass' if (rec.management_overall_rating or 0) >= 3 else 'fail'
            else:
                rec.result = 'pass' if rec.total_score >= rec.pass_score_snapshot else 'fail'


class HrApplicantOjeEvaluationSection(models.Model):
    _name = 'hr.applicant.oje.evaluation.section'
    _description = 'Applicant OJE Evaluation Section'
    _order = 'sequence, id'

    evaluation_id = fields.Many2one('hr.applicant.oje.evaluation', string='Evaluation', ondelete='cascade', required=True)
    source_config_section_id = fields.Many2one('hr.job.oje.config.section', string='Source Job Section', ondelete='set null')

    sequence = fields.Integer(string='Sequence', default=10)
    name = fields.Char(string='Section Title', required=True)
    section_kind = fields.Selection([
        ('staff_block', 'Staff Block'),
        ('management_dimension', 'Management Dimension'),
        ('management_xfactor', 'Management X-Factor'),
        ('legacy', 'Legacy'),
    ], string='Section Kind', default='legacy', required=True)

    scope = fields.Selection([
        ('store_staff', 'Store Staff'),
        ('store_management', 'Store Management'),
    ], string='Scope')
    rating_mode = fields.Selection([
        ('staff_matrix', 'Staff Matrix NI/GD/EX/OS'),
        ('management_1_5', 'Management Score 1..5'),
        ('xfactor_yes_no', 'X-Factor Yes/No'),
        ('legacy_generic', 'Legacy Generic'),
    ], string='Rating Mode', default='legacy_generic')

    objective_text = fields.Text(string='Objective')
    hint_html = fields.Html(string='Hints')
    behavior_html = fields.Html(string='Behavior Checklist')
    is_active = fields.Boolean(default=True)

    section_rating = fields.Integer(string='Section Rating (1..5)')

    line_ids = fields.One2many('hr.applicant.oje.evaluation.line', 'section_id', string='Lines')


class HrApplicantOjeEvaluationLine(models.Model):
    _name = 'hr.applicant.oje.evaluation.line'
    _description = 'Applicant OJE Evaluation Line'
    _order = 'sequence, id'

    evaluation_id = fields.Many2one('hr.applicant.oje.evaluation', string='Evaluation', ondelete='cascade', required=True)
    section_id = fields.Many2one('hr.applicant.oje.evaluation.section', string='Section', ondelete='cascade')
    template_line_id = fields.Many2one('hr.job.oje.config.line', string='Template Line', ondelete='set null')

    sequence = fields.Integer(string='Sequence', default=10)
    name = fields.Char(string='Tiêu chí', required=True)
    question_text = fields.Text(string='Question / Task')
    is_required = fields.Boolean(string='Required', default=True)
    is_active = fields.Boolean(string='Active', default=True)

    line_kind = fields.Selection([
        ('legacy', 'Legacy'),
        ('staff_question', 'Staff Question'),
        ('management_task', 'Management Task'),
        ('management_xfactor', 'Management X-Factor'),
    ], string='Line Kind', default='legacy', required=True)

    scope = fields.Selection([
        ('store_staff', 'Store Staff'),
        ('store_management', 'Store Management'),
    ], string='Scope')

    rating_mode = fields.Selection([
        ('staff_matrix', 'Staff Matrix NI/GD/EX/OS'),
        ('management_1_5', 'Management Score 1..5'),
        ('xfactor_yes_no', 'X-Factor Yes/No'),
        ('legacy_generic', 'Legacy Generic'),
    ], string='Rating Mode', default='legacy_generic')

    field_type = fields.Selection([
        ('text', 'Text (Comment + Manual Score)'),
        ('radio', 'Radio (Select one)'),
        ('checkbox', 'Checkbox (Yes/No)'),
    ], string='Field Type', required=True, default='text')

    # Legacy input values
    text_value = fields.Text(string='Nhận xét')
    text_score = fields.Float(string='Điểm (Nhập tay)')
    text_max_score = fields.Float(string='Điểm tối đa')

    checkbox_value = fields.Boolean(string='Checkbox Value')
    checkbox_score = fields.Float(string='Điểm (Checkbox)')

    selected_option_id = fields.Many2one('hr.job.oje.config.option', string='Lựa chọn')
    selected_option_score = fields.Float(string='Điểm (Radio)', compute='_compute_selected_option_score', store=True)

    # New dynamic template answers
    staff_rating = fields.Selection([
        ('ni', 'NI'),
        ('gd', 'GD'),
        ('ex', 'EX'),
        ('os', 'OS'),
    ], string='Staff Rating')

    management_score = fields.Integer(string='Management Score (1..5)')
    yes_no_answer = fields.Selection([
        ('y', 'Y'),
        ('n', 'N'),
    ], string='Y/N')
    line_comment = fields.Text(string='Comment')

    awarded_score = fields.Float(string='Điểm đạt được', compute='_compute_awarded_score', store=True)

    @api.depends('selected_option_id', 'selected_option_id.score')
    def _compute_selected_option_score(self):
        for rec in self:
            rec.selected_option_score = rec.selected_option_id.score if rec.selected_option_id else 0.0

    @api.depends(
        'line_kind',
        'staff_rating',
        'management_score',
        'yes_no_answer',
        'field_type',
        'text_score',
        'checkbox_value',
        'checkbox_score',
        'selected_option_id',
        'selected_option_id.score',
    )
    def _compute_awarded_score(self):
        for line in self:
            if line.line_kind == 'staff_question':
                line.awarded_score = {
                    'ni': 0.0,
                    'gd': 1.0,
                    'ex': 2.0,
                    'os': 3.0,
                }.get(line.staff_rating, 0.0)
            elif line.line_kind == 'management_task':
                line.awarded_score = float(line.management_score or 0)
            elif line.line_kind == 'management_xfactor':
                line.awarded_score = 1.0 if line.yes_no_answer == 'y' else 0.0
            else:
                if line.field_type == 'text':
                    line.awarded_score = line.text_score
                elif line.field_type == 'checkbox':
                    line.awarded_score = line.checkbox_score if line.checkbox_value else 0.0
                elif line.field_type == 'radio':
                    line.awarded_score = line.selected_option_id.score if line.selected_option_id else 0.0
                else:
                    line.awarded_score = 0.0
