from odoo import models, fields, api, exceptions
from datetime import timedelta
import json
import logging

_logger = logging.getLogger(__name__)

class HrJob(models.Model):
    _inherit = 'hr.job'
    _order = "recruitment_qty_updated_at desc nulls last, id desc"

    no_of_recruitment = fields.Integer(default=0)
    recruitment_qty_updated_at = fields.Datetime("Cập nhật số lượng lần cuối", copy=False)
    
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('no_of_recruitment', 0) > 0:
                vals['recruitment_qty_updated_at'] = fields.Datetime.now()
        return super().create(vals_list)

    def write(self, vals):
        if 'no_of_recruitment' in vals:
            changed_records = self.filtered(lambda r: r.no_of_recruitment != vals['no_of_recruitment'])
            if changed_records:
                vals['recruitment_qty_updated_at'] = fields.Datetime.now()
        return super().write(vals)

    recruitment_type = fields.Selection([
        ('store', 'Khối Cửa Hàng'),
        ('office', 'Khối Văn Phòng'),
    ], string='Loại Tuyển Dụng', help='Phân loại job position theo khối', compute='_compute_recruitment_logic', store=True, readonly=False)

    position_level = fields.Selection([
        ('management', 'Quản Lý'),
        ('staff', 'Nhân Viên'),
    ], string='Cấp Bậc', help='Cấp bậc tuyển dụng xác định pipeline sử dụng', compute='_compute_recruitment_logic', store=True, readonly=False)

    @api.depends('name', 'department_id', 'level_id')
    def _compute_recruitment_logic(self):
        for job in self:
            # Mặc định ban đầu
            rec_type = 'office'
            pos_level = 'staff'
            
            # 1. Xác định Loại tuyển dụng (Khối) dựa trên Block của Phòng ban (Module 200)
            if job.department_id and hasattr(job.department_id, 'block_id'):
                block_code = job.department_id.block_id.code or ''
                if block_code == 'OPS':
                    rec_type = 'store'
                elif block_code == 'RST':
                    rec_type = 'office'
                else:
                    # Fallback dựa trên tên
                    block_name = job.department_id.block_id.name or ''
                    if 'Vận hành' in block_name or 'Cửa hàng' in block_name:
                        rec_type = 'store'

            # 2. Xác định Cấp bậc dựa trên trường 'level_id' của Module 200 HOẶC dựa trên tên
            if hasattr(job, 'level_id') and job.level_id:
                level_code = (job.level_id.code or '').lower()
                level_name = (job.level_id.name or '').lower()
                if 'manager' in level_code or 'manager' in level_name or 'quản lý' in level_name:
                    pos_level = 'management'
                else:
                    pos_level = 'staff'
            else:
                # Dự phòng kiểm tra theo tên nếu không có trường level_id
                name_upper = (job.name or '').upper()
                if any(k in name_upper for k in ['MANAGER', 'QUẢN LÝ', 'GIÁM SÁT', 'SUPERVISOR', 'LEADER', 'TRAINEE MANAGER']):
                    pos_level = 'management'
                else:
                    pos_level = 'staff'
            
            job.recruitment_type = rec_type
            job.position_level = pos_level

    auto_evaluate_survey = fields.Boolean(
        string='Tự Động Đánh Giá Survey',
        default=False,
    )

    survey_eval_mode = fields.Selection([
        ('percentage', 'Theo % điểm'),
        ('correct_count', 'Theo số câu đúng'),
    ], string='Chế độ đánh giá', default='percentage')

    min_correct_answers = fields.Integer(
        string='Số câu đúng tối thiểu',
        default=0,
        help='Số câu trả lời đúng tối thiểu để ứng viên được coi là đạt (dùng khi chế độ = Theo số câu đúng)',
    )
    
    # Thêm computed field để hiển thị tên department thay vì user_id
    display_name_with_dept = fields.Char(
        string='Tên với Phòng ban',
        compute='_compute_display_name_with_dept',
        store=True,
    )
    
    @api.depends('name', 'department_id')
    def _compute_display_name_with_dept(self):
        for job in self:
            if job.department_id:
                job.display_name_with_dept = f"{job.name} ({job.department_id.name})"
            else:
                job.display_name_with_dept = job.name
    
    def _get_stage_filter_type(self):
        """Return the canonical pipeline filter type key.
        - store + staff       -> 'staff'
        - store + management  -> 'management'
        - office              -> 'office'
        """
        self.ensure_one()
        if self.recruitment_type == 'store':
            return self.position_level or 'store'
        return self.recruitment_type or False

    def action_open_applicants(self):
        """Open applicant kanban view for this job position.
        Passes full context so _read_group_stage_ids can resolve the correct pipeline.
        """
        self.ensure_one()
        stage_type = self._get_stage_filter_type()

        return {
            'name': f'Ứng Viên - {self.name}',
            'type': 'ir.actions.act_window',
            'res_model': 'hr.applicant',
            'view_mode': 'kanban,list,form,pivot,graph,calendar,activity',
            'domain': [('job_id', '=', self.id)],
            'context': {
                'default_job_id': self.id,
                'search_default_job_id': [self.id],
                'search_default_applicants': 1,
                'default_recruitment_type': self.recruitment_type,
                'default_position_level': self.position_level,
                'default_stage_filter_type': stage_type,
                'dialog_size': 'medium',
                'allow_search_matching_applicants': 1,
            },
        }

    # ==================== SURVEY CONFIGURATION ====================

    master_survey_id = fields.Many2one(
        'survey.survey', string='Ngân hàng câu hỏi (Master)',
        help='Bài khảo sát chứa toàn bộ câu hỏi chung để lựa chọn cho vị trí này.'
    )
    job_survey_question_ids = fields.One2many(
        'hr.job.survey.question', 'job_id',
        string='Cấu hình câu hỏi khảo sát'
    )
    generated_survey_template_id = fields.Many2one(
        'survey.survey', string='Survey Template đã tạo',
        readonly=True, help='Bài survey mẫu được sinh ra từ các câu hỏi đã chọn.'
    )

    # ==================== REFUSE CONFIGURATION ====================
    job_refuse_reason_ids = fields.One2many(
        'hr.applicant.refuse.reason', 'job_id',
        string='Cấu hình lý do từ chối'
    )

    def action_load_default_refuse_reasons(self):
        """Nạp các lý do từ chối mặc định vào cấu hình Job"""
        self.ensure_one()
        
        default_reasons = [
            'TA_KHÔNG PHÙ HỢP VỚI NHU CẦU HIỆN TẠI CỦA CỬA HÀNG',
            'TA_KHÔNG LÀM T7/CN/LỄ TẾT',
            'TA_KHÔNG ĐI SỚM/VỀ TRỄ/CA ĐÊM',
            'KINH NGHIỆM KHÔNG PHÙ HỢP',
            'FAIL PHÓNG VẤN/OJE (GHI RÕ LÍ DO FAIL)',
            'KHÔNG LIÊN HỆ ĐƯỢC',
            'LÝ DO KHÁC (VUI LÒNG GHI RÕ)',
            'CHƯA ĐỦ TUỔI',
            'KHÔNG CÒN NHU CẦU NHẬN VIỆC (NO SHOW)'
        ]
        
        existing_reasons = self.job_refuse_reason_ids.mapped('name')
        
        vals_list = []
        for reason in default_reasons:
            if reason not in existing_reasons:
                reason_type = 'text' if any(kw in reason.lower() for kw in ['fail phóng vấn/oje', 'lý do khác']) else 'checkbox'
                vals_list.append({
                    'job_id': self.id,
                    'name': reason,
                    'reason_type': reason_type,
                    'active': True,
                })
                
        if vals_list:
            self.env['hr.applicant.refuse.reason'].create(vals_list)
            
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Thành công',
                'message': f'Đã tải {len(vals_list)} lý do mặc định.',
                'type': 'success',
                'sticky': False,
            }
        }

    # ==================== EMAIL CONFIGURATION ====================
    email_rule_ids = fields.One2many(
        'hr.job.email.rule', 'job_id',
        string='Mọi cấu hình Email'
    )
    email_rule_stage_ids = fields.One2many(
        'hr.job.email.rule', 'job_id',
        string='Cấu hình Email theo Vòng',
        domain=[('rule_type', '=', 'stage')]
    )
    email_rule_event_ids = fields.One2many(
        'hr.job.email.rule', 'job_id',
        string='Cấu hình Email theo Sự kiện',
        domain=[('rule_type', '=', 'event')]
    )

    def action_load_default_email_rules(self):
        """Nạp các cấu hình email sự kiện mặc định vào Job"""
        self.ensure_one()
        # Default events fallback
        events = [
            ('survey_invite', 'M02_P0204_00.email_survey_invitation'),
            ('interview_invitation', 'M02_P0204_00.email_interview_invitation'),
            ('interview_slot_confirmed', 'M02_P0204_00.email_interview_slot_confirmed'),
            ('reject', 'M02_P0204_00.email_rejection'),
            ('oje_reject', 'M02_P0204_00.email_oje_rejection'),
            ('hired', 'hr_recruitment.email_template_data_applicant_congratulations')
        ]
        
        existing_events = self.email_rule_event_ids.mapped('event_code')
        vals_list = []
        for code, xml_id in events:
            if code not in existing_events:
                template = self.env.ref(xml_id, raise_if_not_found=False)
                if template:
                    vals_list.append({
                        'job_id': self.id,
                        'rule_type': 'event',
                        'event_code': code,
                        'template_id': template.id,
                        'active': True,
                    })
        
        if vals_list:
            self.env['hr.job.email.rule'].create(vals_list)
            
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Thành công',
                'message': f'Đã tải {len(vals_list)} cấu hình email sự kiện mặc định.',
                'type': 'success',
                'sticky': False,
            }
        }

    # ==================== OJE CONFIGURATION ====================
    oje_pass_score = fields.Float(string='Điểm đạt OJE', default=6.0)
    oje_evaluator_user_id = fields.Many2one('res.users', string='Người đánh giá OJE', help='User chịu trách nhiệm đánh giá OJE (Snapshot từ requester của Job Request)')
    oje_config_line_ids = fields.One2many('hr.job.oje.config.line', 'job_id', string='Cấu hình tiêu chí OJE')

    # ==================== APPLICATION FORM CONFIGURATION ====================

    application_field_ids = fields.One2many(
        'job.application.field', 'job_id',
        string='Mọi trường biểu mẫu'
    )
    
    application_field_basic_ids = fields.One2many(
        'job.application.field', 'job_id',
        string='Thông tin cơ bản',
        domain=[('section', '=', 'basic_info')]
    )
    
    application_field_other_ids = fields.One2many(
        'job.application.field', 'job_id',
        string='Các thông tin khác',
        domain=[('section', '=', 'other_info')]
    )
    
    application_field_supp_ids = fields.One2many(
        'job.application.field', 'job_id',
        string='Câu hỏi bổ sung',
        domain=[('section', '=', 'supplementary_question')]
    )
    
    application_field_internal_ids = fields.One2many(
        'job.application.field', 'job_id',
        string='Câu hỏi nội bộ',
        domain=[('section', '=', 'internal_question')]
    )

    def action_load_default_fields(self):
        """Load lại từ cấu hình master mặc định (Recruitment > Configuration).
        
        Logic:
        1. Đọc danh sách master active, lọc theo recruitment_scope phù hợp với job
        2. Với từng dòng master:
           - Chưa có dòng link → tạo mới
           - Đã có dòng link → cập nhật toàn bộ thuộc tính cấu trúc
        3. Dòng master đã bị tắt active → tắt is_active ở job
        4. Không xóa dòng custom
        """
        self.ensure_one()
        
        MasterField = self.env['recruitment.application.field.master']
        JobField = self.env['job.application.field'].with_context(master_reload=True)
        
        # Xác định scope lọc theo recruitment_type của job
        scope_filter = [('recruitment_scope', 'in', ['both'])]
        if self.recruitment_type == 'store':
            scope_filter = [('recruitment_scope', 'in', ['store', 'both'])]
        elif self.recruitment_type == 'office':
            scope_filter = [('recruitment_scope', 'in', ['office', 'both'])]
        
        # Lấy TẤT CẢ master (kể cả inactive) để xử lý archive
        all_masters = MasterField.with_context(active_test=False).search(scope_filter)
        active_masters = all_masters.filtered('active')
        inactive_masters = all_masters - active_masters
        
        # Lấy các dòng hiện tại của job có link về master
        existing_master_lines = self.application_field_ids.filtered('is_from_master')
        existing_map = {line.master_field_id.id: line for line in existing_master_lines if line.master_field_id}
        
        created_count = 0
        updated_count = 0
        
        for master in active_masters:
            expected_answer = master.expected_answer or ''
            field_vals = {
                'field_label': master.field_label,
                'field_name': master.field_name,
                'field_type': master.field_type,
                'section': master.section,
                'sequence': master.sequence,
                'col_size': master.col_size,
                'is_active': master.is_active_default,
                'is_required': master.is_required_default,
                'is_answer_must_match': master.is_answer_must_match_default,
                'expected_answer': '' if master.field_type in ('select', 'radio') else expected_answer,
                'is_default': True,
                'is_from_master': True,
                'master_field_id': master.id,
            }
            
            existing_line = existing_map.get(master.id)
            
            if existing_line:
                # Cập nhật dòng đã có
                existing_line.write(field_vals)
                # Sync options: xóa cũ, tạo mới
                existing_line.option_ids.unlink()
                self._sync_master_options(existing_line, master)
                if expected_answer and master.field_type in ('select', 'radio', 'checkbox'):
                    existing_line.write({'expected_answer': expected_answer})
                updated_count += 1
            else:
                # Kiểm tra trùng field_name (có thể từ dòng legacy is_default cũ)
                legacy_line = self.application_field_ids.filtered(
                    lambda f: f.field_name == master.field_name and not f.is_from_master
                )
                if legacy_line:
                    # Chuyển đổi dòng legacy thành master-linked
                    legacy_line[0].write(field_vals)
                    legacy_line[0].option_ids.unlink()
                    self._sync_master_options(legacy_line[0], master)
                    if expected_answer and master.field_type in ('select', 'radio', 'checkbox'):
                        legacy_line[0].write({'expected_answer': expected_answer})
                    updated_count += 1
                else:
                    # Tạo mới
                    field_vals['job_id'] = self.id
                    new_line = JobField.create(field_vals)
                    self._sync_master_options(new_line, master)
                    if expected_answer and master.field_type in ('select', 'radio', 'checkbox'):
                        new_line.write({'expected_answer': expected_answer})
                    created_count += 1
        
        # Xử lý master bị tắt active → tắt is_active ở dòng job tương ứng
        archived_count = 0
        for master in inactive_masters:
            existing_line = existing_map.get(master.id)
            if existing_line and existing_line.is_active:
                existing_line.write({'is_active': False})
                archived_count += 1
        
        total = created_count + updated_count
        msg_parts = []
        if created_count:
            msg_parts.append(f'tạo mới {created_count}')
        if updated_count:
            msg_parts.append(f'cập nhật {updated_count}')
        if archived_count:
            msg_parts.append(f'archive {archived_count}')
        
        message = f"Đã xử lý {total} trường từ master ({', '.join(msg_parts)})." if msg_parts else "Không có thay đổi."
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Thành công',
                'message': message,
                'type': 'success',
                'sticky': False,
            }
        }

    def _sync_master_options(self, job_field, master_field):
        """Đồng bộ options từ master field sang job field."""
        OptionModel = self.env['job.application.field.option']
        for opt in master_field.option_ids.sorted('sequence'):
            OptionModel.create({
                'field_id': job_field.id,
                'sequence': opt.sequence,
                'value': opt.value,
                'name': opt.name,
            })

    def action_load_master_questions(self):
        """Tải toàn bộ câu hỏi từ Master Survey vào bảng cấu hình"""
        self.ensure_one()
        if not self.master_survey_id:
            raise exceptions.UserError("Vui lòng chọn Ngân hàng câu hỏi trước!")
        
        # Xóa các cấu hình cũ
        self.job_survey_question_ids.unlink()
        
        vals_list = []
        for question in self.master_survey_id.question_ids:
            vals_list.append({
                'job_id': self.id,
                'master_question_id': question.id,
                'is_selected': False,
            })
        
        if vals_list:
            self.env['hr.job.survey.question'].create(vals_list)
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Thành công',
                'message': f'Đã tải {len(vals_list)} câu hỏi từ {self.master_survey_id.title}',
                'type': 'success',
                'sticky': False,
            }
        }

    def action_generate_survey_template(self):
        """Tạo Survey Template mới từ danh sách câu hỏi đã chọn"""
        self.ensure_one()
        selected_lines = self.job_survey_question_ids.filtered('is_selected')
        if not selected_lines:
            raise exceptions.UserError("Vui lòng chọn ít nhất một câu hỏi để tạo template!")

        # Tạo survey mới
        survey_vals = {
            'title': f'Khảo Sát - {self.name} ({self.department_id.name or "Không xác định"})',
            'is_pre_interview': True,
            'scoring_type': 'scoring_with_answers',
            'access_mode': 'token',
        }
        
        # Nếu đã có template cũ, cập nhật hoặc tạo mới
        if self.generated_survey_template_id:
            survey = self.generated_survey_template_id
            survey.write(survey_vals)
            # Xóa các câu hỏi cũ của template
            survey.question_ids.unlink()
        else:
            survey = self.env['survey.survey'].create(survey_vals)
            self.generated_survey_template_id = survey

        # Copy các câu hỏi đã chọn vào survey mới
        for line in selected_lines:
            # Copy câu hỏi và các lựa chọn đáp án
            new_q = line.master_question_id.copy({
                'survey_id': survey.id,
                'sequence': line.master_question_id.sequence,
            })
            new_q.write({'is_mandatory_correct': line.is_required})
            # Nếu có điểm tối thiểu riêng (tương lai có thể dùng)
            # Hiện tại Odoo Survey dùng điểm trên từng đáp án

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Thành công',
                'message': f'Đã tạo bài khảo sát mẫu: {survey.title}',
                'type': 'success',
                'sticky': False,
            }
        }


