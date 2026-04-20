import logging
import secrets
from datetime import timedelta, timezone
from zoneinfo import ZoneInfo
from odoo import models, fields, api, exceptions, _, Command
from .interview_round import INTERVIEW_ROUND_SELECTION, INTERVIEW_STAGE_XML_TO_ROUND

_logger = logging.getLogger(__name__)

class HrApplicant(models.Model):
    _inherit = 'hr.applicant'

    INTERVIEW_ROUNDS_BY_LEVEL_CODE = {
        'employee': 2,
        'assistant': 2,
        'coordinator': 2,
        'specialist': 3,
        'consultant': 3,
        'manager': 4,
        'head_of_department': 4,
    }
    stage_id = fields.Many2one(
        domain=(
            "['|', ('job_ids', '=', False), ('job_ids', '=', job_id), "
            "('recruitment_type', '=', stage_filter_type), "
            "'|', ('office_pipeline_visible', '=', True), ('recruitment_type', '!=', 'office')]"
        )
    )

    # Tang so sao danh gia len 5 (can 6 muc lua chon)
    priority = fields.Selection([
        ('0', 'Normal'),
        ('1', 'Good'),
        ('2', 'Very Good'),
        ('3', 'Excellent'),
        ('4', 'Outstanding'),
        ('5', 'Exceptional'),
    ], string='Evaluation', default='0')

    x_psm_0205_recruitment_type = fields.Selection(
        related="job_id.recruitment_type",
        string="Loại Tuyển Dụng",
        store=True,
        readonly=True,
        help="Kế thừa từ Job Position để lọc pipeline và hiển thị UI theo khối.",
    )

    # Step 9-11: Survey
    x_psm_0205_survey_sent = fields.Boolean(string='Survey sent', default=False, tracking=True)
    x_psm_0205_survey_result_url = fields.Char(string='Survey result URL', help='Link to candidate survey result')
    # survey_url is now a simple Char field owned by M02_P0204
    # No compute needed here — 0204's controller writes the personalized URL.

    def _handle_office_pre_interview_survey_done(self, user_input):
        """
        Called by 0204's _dispatch_recruitment_survey_done when x_psm_0205_recruitment_type == 'office'.
        Office no longer rejects by score. Candidates always move to Screening.
        Only checks mandatory questions.
        """
        from markupsafe import Markup
        from werkzeug.urls import url_encode

        survey = user_input.survey_id.sudo()
        if not survey.access_token:
            survey.write({'access_token': survey._get_default_access_token()})
        survey_print_url = survey.get_print_url()
        query_string = url_encode({'answer_token': user_input.access_token, 'review': True})
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url') or ''
        base_url = base_url.rstrip('/')
        review_url = f"{survey_print_url}?{query_string}"
        if base_url:
            review_url = f"{base_url}{review_url}"

        # Kiểm tra câu bắt buộc
        has_mandatory_fail, failed_questions = user_input._check_mandatory_questions_failed(user_input)
        
        target_stage = self.env.ref('M02_P0205.stage_office_screening', raise_if_not_found=False)

        if has_mandatory_fail:
            status_label = "CÓ SAI SÓT (Vẫn vào Screening)"
            color = "#ffc107"
            q_list = ", ".join(f"<i>{q}</i>" for q in failed_questions)
            note = f"Ứng viên đã trả lời sai các câu hỏi bắt buộc: {q_list}."
        else:
            status_label = "HOÀN THÀNH"
            color = "#28a745"
            note = "Ứng viên đã hoàn thành khảo sát và không sai câu hỏi bắt buộc nào."

        survey_link = f"{survey_print_url}?{query_string}"
        msg = f"""
            <div style="border-left: 5px solid {color}; padding: 10px; background-color: #f8f9fa;">
                <h4 style="margin: 0; color: {color};">🎯 Kết quả khảo sát tự động: {status_label}</h4>
                <p style="margin-top: 10px; margin-bottom: 5px;">{note}</p>
                <a href="{survey_link}" target="_blank" style="color: #007bff; text-decoration: underline;">Xem chi tiết câu trả lời</a>
            </div>
        """
        applicant_vals = {
            'x_psm_0205_survey_result_url': review_url,
            'x_psm_0205_survey_sent': True,
        }
        if target_stage and self.stage_id != target_stage:
            applicant_vals['stage_id'] = target_stage.id
            
        self.message_post(body=Markup(msg))
        
        if applicant_vals:
            self.write(applicant_vals)

        # Tạo activity follow-up khi applicant vào Screening từ survey.
        if target_stage:
            manager_user = self._find_office_applicant_manager_user()
            responsible_user = manager_user or self.user_id or self.job_id.user_id
            if responsible_user:
                summary = "Kiểm tra CV ứng viên sau khi hoàn thành khảo sát"
                note_body = f"Vui lòng review CV chuyên môn của {self.partner_name or self.name} và đánh giá."
                if has_mandatory_fail:
                    note_body += "\nLưu ý: Ứng viên này đã trả lời sai một số câu hỏi bắt buộc trong bài Test."
                self._schedule_round_activity_for_users(responsible_user, summary, note_body)

    def _find_office_applicant_manager_user(self):
        """Find the responsible manager user for office applicant activities."""
        self.ensure_one()
        job = self.job_id
        department = job.department_id if job else self.department_id
        user = self._manager_user_from_department(department)
        if user:
            return user
        department = self.department_id
        user = self._manager_user_from_department(department)
        if user:
            return user
        if job:
            line = self.env['x_psm_recruitment_request_line'].search(
                [('job_id', '=', job.id)],
                order='id desc',
                limit=1,
            )
            if line:
                return self._manager_user_from_department(line.department_id)
        return False

    def _manager_user_from_department(self, department):
        if not department:
            return False
        manager = department.manager_id
        return manager.user_id if manager and manager.user_id else False

    def _get_store_activity_department(self):
        self.ensure_one()
        return self.department_id or self.job_id.department_id

    def _get_store_hr_recruitment_users(self, department=False):
        self.ensure_one()
        target_department = department or self._get_store_activity_department()
        hr_group = self.env.ref('M02_P0200.GDH_RST_HR_RECRUITMENT_M', raise_if_not_found=False)
        if not hr_group or not target_department:
            return self.env['res.users']
        return hr_group.user_ids.filtered(
            lambda user: (
                user.active
                and not user.share
                and user.employee_id
                and user.employee_id.department_id == target_department
            )
        ).sorted('id')

    def _warn_missing_store_hr_recipients(self, activity_label, department=False):
        self.ensure_one()
        target_department = department or self._get_store_activity_department()
        department_name = target_department.display_name if target_department else _('Chưa xác định phòng ban')
        warning_msg = _(
            "Không tìm thấy HR Recruitment cùng phòng ban (%(department)s) để nhận activity '%(activity)s'. "
            "Vui lòng cấu hình user thuộc group HR Recruitment và gán đúng phòng ban trên hồ sơ nhân viên."
        ) % {
            'department': department_name,
            'activity': activity_label,
        }
        _logger.warning(
            "Store applicant %s missing HR recipients for activity '%s' (department_id=%s)",
            self.id,
            activity_label,
            target_department.id if target_department else False,
        )
        self.message_post(body=warning_msg)

    def _schedule_store_hr_activity(self, summary, note, activity_label):
        self.ensure_one()
        users = self._get_store_hr_recruitment_users()
        if not users:
            self._warn_missing_store_hr_recipients(activity_label)
            return
        self._schedule_round_activity_for_users(users, summary, note)

    def _x_psm_get_stage_scope_type(self, applicant):
        if hasattr(applicant, '_get_pipeline_stage_type'):
            return applicant._get_pipeline_stage_type()
        fallback_type = applicant.x_psm_0205_recruitment_type or False
        if fallback_type == 'store':
            return applicant.position_level if applicant.position_level in ('staff', 'management') else False
        return fallback_type if fallback_type in ('office', 'staff', 'management') else False

    def _x_psm_get_stage_job_scope_domain(self, applicant):
        if applicant.job_id:
            return [
                '|',
                ('job_ids', '=', False),
                ('job_ids', '=', applicant.job_id.id),
            ]
        return [('job_ids', '=', False)]

    def _get_stage_search_domain(self, applicant):
        search_domain = list(self._x_psm_get_stage_job_scope_domain(applicant))
        stage_type = self._x_psm_get_stage_scope_type(applicant)
        if not stage_type:
            search_domain.append(('id', '=', 0))
            return search_domain

        search_domain.append(('recruitment_type', '=', stage_type))
        if stage_type == 'office':
            search_domain.extend([
                '|',
                ('office_pipeline_visible', '=', True),
                ('recruitment_type', '!=', 'office'),
            ])
        return search_domain

    @api.depends('job_id', 'department_id')
    def _compute_stage(self):
        for applicant in self:
            if applicant.job_id:
                if not applicant.stage_id:
                    stage = self.env['hr.recruitment.stage'].search(
                        self._get_stage_search_domain(applicant) + [('fold', '=', False)],
                        order='sequence asc',
                        limit=1,
                    )
                    applicant.stage_id = stage.id or False
            else:
                applicant.stage_id = False



    def action_send_survey(self):
        """Step 9: Gửi email khảo sát cho ứng viên"""
        self.ensure_one()
        if not self.email_from:
            raise exceptions.UserError("Ứng viên chưa có địa chỉ email!")
        
        # Ưu tiên: survey trên applicant → survey của job → tìm survey mặc định
        if not self.survey_id:
            if self.job_id.survey_id:
                # Lấy survey được cấu hình cho vị trí tuyển dụng này
                self.survey_id = self.job_id.survey_id
            else:
                # Fallback: tìm survey pre-interview bất kỳ
                default_survey = self.env['survey.survey'].search([('x_psm_0205_is_pre_interview', '=', True)], limit=1)
                if default_survey:
                    self.survey_id = default_survey
                else:
                    raise exceptions.UserError(
                        "Vị trí '%s' chưa cấu hình bài khảo sát! "
                        "Vui lòng vào Job Position → tab 'Nội dung Website' để chọn khảo sát." % (self.job_id.name or '')
                    )

        template = self.env.ref('M02_P0205.email_candidate_survey_office', raise_if_not_found=False)
            
        if template:
            template.send_mail(self.id, force_send=True)
            self.write({'x_psm_0205_survey_sent': True})
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Thành công',
                    'message': 'Đã gửi khảo sát cho ứng viên.',
                    'type': 'success',
                    'next': {
                        'type': 'ir.actions.client',
                        'tag': 'reload',
                    },
                }
            }
        else:
            raise exceptions.UserError("Không tìm thấy mẫu email gửi khảo sát!")

    def action_view_survey_result(self):
        """Mở link kết quả khảo sát"""
        self.ensure_one()
        if self.x_psm_0205_survey_result_url:
            return {
                'type': 'ir.actions.act_url',
                'url': self.x_psm_0205_survey_result_url,
                'target': 'new',
            }
        return False

    def _get_0205_company_for_config(self):
        self.ensure_one()
        return self.company_id or self.job_id.company_id or self.env.company

    def _get_0205_default_email_from(self, prefer_user=False, noreply=False, user=False):
        self.ensure_one()
        target_user = user or self.user_id
        company = self._get_0205_company_for_config()
        if prefer_user and target_user and target_user.email_formatted:
            return target_user.email_formatted
        if company:
            if noreply and company.x_psm_0205_default_recruitment_noreply_email:
                return company.x_psm_0205_default_recruitment_noreply_email
            if company.x_psm_0205_default_recruitment_email_from:
                return company.x_psm_0205_default_recruitment_email_from
            if company.email_formatted:
                return company.email_formatted
        return 'noreply@recruitment.com' if noreply else 'recruitment@example.com'

    def _get_0205_default_interview_location(self, fallback_partner=False):
        self.ensure_one()
        company = self._get_0205_company_for_config()
        if company and company.x_psm_0205_default_interview_location:
            return company.x_psm_0205_default_interview_location
        if fallback_partner and fallback_partner.contact_address:
            return fallback_partner.contact_address
        if company and company.partner_id.contact_address:
            return company.partner_id.contact_address
        return 'Văn phòng công ty'

    def _get_0205_default_interview_owner_name(self):
        self.ensure_one()
        company = self._get_0205_company_for_config()
        if company and company.x_psm_0205_ceo_id:
            return company.x_psm_0205_ceo_id.name
        return 'Bộ phận Tuyển dụng'

    def _get_0205_bod_group(self):
        self.ensure_one()
        company = self._get_0205_company_for_config()
        return company._x_psm_0205_get_bod_interviewer_group() if company else self.env['res.groups']

    def _get_0205_abu_group(self):
        self.ensure_one()
        company = self._get_0205_company_for_config()
        return company._x_psm_0205_get_abu_interviewer_group() if company else self.env['res.groups']

    def _get_job_default_interviewer_users(self):
        self.ensure_one()
        return self.job_id.interviewer_ids.filtered(lambda user: not user.share)

    def _vals_include_applicant_skills(self, vals):
        return 'current_applicant_skill_ids' in vals or 'applicant_skill_ids' in vals

    def _prepare_applicant_skill_commands_from_job(self, job):
        commands = []
        if not job:
            return commands

        for job_skill in job.current_job_skill_ids:
            if not job_skill.skill_id or not job_skill.skill_level_id or not job_skill.skill_type_id:
                continue
            commands.append(Command.create({
                'skill_type_id': job_skill.skill_type_id.id,
                'skill_id': job_skill.skill_id.id,
                'skill_level_id': job_skill.skill_level_id.id,
                'valid_from': job_skill.valid_from or fields.Date.today(),
                'valid_to': job_skill.valid_to,
            }))
        return commands

    def _sync_missing_skills_from_job(self):
        for rec in self.filtered(lambda applicant: applicant.job_id and not applicant.applicant_skill_ids):
            commands = rec._prepare_applicant_skill_commands_from_job(rec.job_id)
            if commands:
                rec.with_context(skip_job_skill_sync=True).write({
                    'current_applicant_skill_ids': commands,
                })

    def _replace_skills_from_job(self):
        for rec in self.filtered(lambda applicant: applicant.job_id):
            commands = [Command.delete(skill.id) for skill in rec.applicant_skill_ids]
            commands.extend(rec._prepare_applicant_skill_commands_from_job(rec.job_id))
            if commands:
                rec.with_context(skip_job_skill_sync=True).write({
                    'applicant_skill_ids': commands,
                })

    @api.onchange('job_id')
    def _onchange_job_default_interviewers(self):
        for rec in self:
            if not rec.job_id or rec.interviewer_ids:
                continue
            rec.interviewer_ids = rec._get_job_default_interviewer_users()

    @api.onchange('job_id')
    def _onchange_job_default_skills(self):
        for rec in self:
            if not rec.job_id or rec.current_applicant_skill_ids or rec.applicant_skill_ids:
                continue
            commands = rec._prepare_applicant_skill_commands_from_job(rec.job_id)
            if commands:
                rec.current_applicant_skill_ids = commands

    # Step 12-14: Interview 1 (Manager)
    x_psm_0205_interview_date_1 = fields.Datetime(string='Lịch PV L1 (Manager)', tracking=True)
    x_psm_0205_interview_result_1 = fields.Selection([
        ('0', '0'),
        ('1', '1'),
        ('2', '2'),
        ('3', '3'),
        ('4', '4'),
        ('5', '5'),
    ], string='Kết quả PV L1', compute='_compute_eval_round_metrics', store=True)
    
    # Step 18-21: Interview 2 (CEO)
    x_psm_0205_interview_date_2 = fields.Datetime(string='Lịch PV L2 (CEO)', tracking=True)
    x_psm_0205_interview_result_2 = fields.Selection([
        ('0', '0'),
        ('1', '1'),
        ('2', '2'),
        ('3', '3'),
        ('4', '4'),
        ('5', '5'),
    ], string='Kết quả PV L2', compute='_compute_eval_round_metrics', store=True)

    # Step 22-26: Interview 3 (BOD)
    x_psm_0205_interview_date_3 = fields.Datetime(string='Lịch PV L3 (BOD)', tracking=True)
    x_psm_0205_interview_result_3 = fields.Selection([
        ('0', '0'),
        ('1', '1'),
        ('2', '2'),
        ('3', '3'),
        ('4', '4'),
        ('5', '5'),
    ], string='Kết quả PV L3', compute='_compute_eval_round_metrics', store=True)

    # Step 27: Interview 4 (ABU)
    x_psm_0205_interview_date_4 = fields.Datetime(string='Lịch PV L4 (ABU)', tracking=True)
    x_psm_0205_interview_result_4 = fields.Selection([
        ('0', '0'),
        ('1', '1'),
        ('2', '2'),
        ('3', '3'),
        ('4', '4'),
        ('5', '5'),
    ], string='Kết quả PV L4', compute='_compute_eval_round_metrics', store=True)

    x_psm_0205_interview_slot_token = fields.Char(string='Mã chọn lịch PV', copy=False)
    x_psm_0205_interview_slot_event_id = fields.Many2one('calendar.event', string='Lịch PV đã chọn', copy=False)
    x_psm_0205_next_interview_round = fields.Selection(
        INTERVIEW_ROUND_SELECTION,
        string='Vòng phỏng vấn tiếp theo',
        compute='_compute_next_interview_round',
        store=True,
    )
    x_psm_0205_job_level_code = fields.Char(
        string='Mã level job',
        compute='_compute_job_level_meta',
    )
    x_psm_0205_max_interview_round = fields.Integer(
        string='Số vòng phỏng vấn tối đa',
        compute='_compute_job_level_meta',
    )
    x_psm_0205_office_stage_statusbar_ids = fields.Many2many(
        'hr.recruitment.stage',
        compute='_compute_office_stage_statusbar_ids',
        string='Các stage office hiển thị trên statusbar',
    )
    x_psm_0205_next_round_event_id = fields.Many2one(
        'calendar.event',
        string='Lịch vòng kế tiếp',
        compute='_compute_next_round_event',
    )
    x_psm_0205_next_round_event_needs_notification = fields.Boolean(
        string='Cần gửi thông báo vòng kế tiếp',
        compute='_compute_next_round_event',
    )
    x_psm_0205_can_schedule_next_round = fields.Boolean(
        string='Có thể lập lịch vòng kế',
        compute='_compute_office_stage_ui_flags',
    )
    x_psm_0205_next_round_date_missing = fields.Boolean(
        string='Thiếu ngày phỏng vấn vòng kế',
        compute='_compute_office_stage_ui_flags',
    )
    x_psm_0205_can_ready_for_offer = fields.Boolean(
        string='Có thể chuyển Offer',
        compute='_compute_office_stage_ui_flags',
    )
    x_psm_0205_is_offer_stage = fields.Boolean(
        string='Đang ở stage Offer',
        compute='_compute_office_stage_ui_flags',
    )
    x_psm_0205_show_offer_result_block = fields.Boolean(
        string='Hiện block Kết quả và Offer',
        compute='_compute_office_stage_ui_flags',
    )
    ROUND_NOTIFICATION_TEMPLATES = {
        '2': 'M02_P0205.email_interview_round2_notification',
        '3': 'M02_P0205.email_interview_round3_notification',
        '4': 'M02_P0205.email_interview_round4_notification',
    }
    x_psm_0205_cv_checked = fields.Boolean(string='Đã kiểm tra CV', default=False, tracking=True)

    # Step 29-31: Offer
    x_psm_0205_offer_status = fields.Selection([
        ('proposed', 'Đã đề xuất'),
        ('accepted', 'Đã chấp nhận'),
        ('refused', 'Đã từ chối')
    ], string='Trạng thái Offer', tracking=True)

    def _format_local_datetime_for_display(self, dt_value, tz=None, fmt='%Y-%m-%d %H:%M'):
        self.ensure_one()
        if not dt_value:
            return ''
        dt_value = fields.Datetime.to_datetime(dt_value)
        tz = tz or self.env.context.get('tz') or self.env.user.tz or 'Asia/Ho_Chi_Minh'
        if dt_value.tzinfo is None:
            dt_value = dt_value.replace(tzinfo=timezone.utc)
        try:
            local_dt = dt_value.astimezone(ZoneInfo(tz))
        except Exception:
            local_dt = dt_value.astimezone(ZoneInfo('Asia/Ho_Chi_Minh'))
        return local_dt.strftime(fmt)

    def action_invite_interview(self, level=1):
        """Action to invite for interview at specific level"""
        self.ensure_one()
        self._ensure_round_enabled(level)
        if level > 1:
            self._ensure_previous_round_completed(level)
        
        # Mapping level to stage and fields
        level_map = {
            1: {'stage_ref': 'M02_P0205.stage_office_interview_1', 'date_field': 'x_psm_0205_interview_date_1', 'label': 'Vòng 1 (Manager)'},
            2: {'stage_ref': 'M02_P0205.stage_office_interview_2', 'date_field': 'x_psm_0205_interview_date_2', 'label': 'Vòng 2 (CEO)'},
            3: {'stage_ref': 'M02_P0205.stage_office_interview_3', 'date_field': 'x_psm_0205_interview_date_3', 'label': 'Vòng 3 (BOD)'},
            4: {'stage_ref': 'M02_P0205.stage_office_interview_4', 'date_field': 'x_psm_0205_interview_date_4', 'label': 'Vòng 4 (ABU)'},
        }
        
        config = level_map.get(level)
        if not config:
             return False

        # 1. Check if date is set
        interview_date = getattr(self, config['date_field'])
        if not interview_date:
            raise exceptions.UserError(f"Vui lòng nhập ngày phỏng vấn {config['label']} trước khi gửi thư mời!")

        # 2. Update Stage
        stage = self.env.ref(config['stage_ref'], raise_if_not_found=False)
        if stage:
            self.stage_id = stage.id

        # 3. Send Email
        template = self.env.ref('M02_P0205.email_interview_invitation_office', raise_if_not_found=False)
        if template:
            # Prepare context for template
            tz = self.env.context.get('tz') or self.env.user.tz or 'Asia/Ho_Chi_Minh'
            interview_date_display = self._format_local_datetime_for_display(interview_date, tz=tz)
            interviewer_name = self.user_id.name or 'Hội đồng Tuyển dụng'
            ctx = {
                'interview_label': config['label'],
                'interview_date': interview_date_display,
                'interviewer_name': interviewer_name,
            }
            body_html = self._build_interview_invitation_email_body(
                config['label'],
                interview_date_display,
                interviewer_name,
            )
            subject = f"Thư mời phỏng vấn - {config['label']} - {self.job_id.name or ''}".strip()
            email_from = self._get_0205_default_email_from(prefer_user=True, noreply=True)
            email_to = self.email_from or self.partner_id.email
            template.with_context(**ctx).send_mail(
                self.id,
                force_send=True,
                email_values={
                    'subject': subject,
                    'email_from': email_from,
                    'email_to': email_to,
                    'body_html': body_html,
                },
            )
            self._log_interview_email_to_chatter(subject, body_html)

            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Thành công',
                    'message': f'Đã gửi thư mời phỏng vấn {config["label"]}.',
                    'type': 'success',
                    'next': {
                        'type': 'ir.actions.client',
                        'tag': 'reload',
                    },
                }
            }
        else:
            raise exceptions.UserError("Không tìm thấy mẫu email mời phỏng vấn!")

    def action_invite_interview_l1(self): return self.action_invite_interview(1)
    def action_invite_interview_l2(self): return self.action_invite_interview(2)
    def action_invite_interview_l3(self): return self.action_invite_interview(3)
    def action_invite_interview_l4(self): return self.action_invite_interview(4)

    def _ensure_interview_slot_token(self):
        if not self.x_psm_0205_interview_slot_token:
            self.x_psm_0205_interview_slot_token = secrets.token_urlsafe(16)

    def get_interview_slot_url(self, event):
        self.ensure_one()
        base_url = self.get_base_url()
        return f"{base_url}/interview/choose/{self.x_psm_0205_interview_slot_token}/{event.id}"

    def _get_stage_round_map(self):
        stage_map = {}
        for stage_xml, round_value in INTERVIEW_STAGE_XML_TO_ROUND.items():
            stage = self.env.ref(stage_xml, raise_if_not_found=False)
            if stage:
                stage_map[stage.id] = round_value
        return stage_map

    def _get_job_level_code(self):
        self.ensure_one()
        level = self.job_id.level_id
        if not level:
            return False
        return (level.code or '').strip().lower() or False

    def _get_max_interview_round(self):
        self.ensure_one()
        job = self.job_id
        if job and getattr(job, 'x_psm_0205_max_interview_round', 0):
            return int(job.x_psm_0205_max_interview_round)
        level_code = self._get_job_level_code()
        return self.INTERVIEW_ROUNDS_BY_LEVEL_CODE.get(level_code, 4)

    def _is_round_enabled(self, round_no):
        self.ensure_one()
        return int(round_no) <= self._get_max_interview_round()

    def _ensure_round_enabled(self, round_no):
        self.ensure_one()
        round_no = int(round_no)
        max_round = self._get_max_interview_round()
        if round_no > max_round:
            raise exceptions.UserError(
                _("Vị trí này chỉ áp dụng tối đa %(max_round)s vòng phỏng vấn theo level hiện tại.") % {
                    'max_round': max_round,
                }
            )

    @api.depends('job_id', 'job_id.level_id', 'job_id.level_id.code', 'job_id.x_psm_0205_max_interview_round')
    def _compute_job_level_meta(self):
        for rec in self:
            rec.x_psm_0205_job_level_code = rec._get_job_level_code()
            rec.x_psm_0205_max_interview_round = rec._get_max_interview_round()

    @api.depends('x_psm_0205_recruitment_type', 'job_id', 'job_id.level_id', 'job_id.level_id.code', 'job_id.x_psm_0205_max_interview_round')
    def _compute_office_stage_statusbar_ids(self):
        stage_xmlids = [
            'M02_P0205.stage_office_new',
            'M02_P0205.stage_office_screening',
            'M02_P0205.stage_office_interview_1',
            'M02_P0205.stage_office_interview_2',
        ]
        for rec in self:
            if rec.x_psm_0205_recruitment_type != 'office':
                rec.x_psm_0205_office_stage_statusbar_ids = False
                continue
            max_round = rec._get_max_interview_round()
            xmlids = list(stage_xmlids)
            if max_round >= 3:
                xmlids.append('M02_P0205.stage_office_interview_3')
            if max_round >= 4:
                xmlids.append('M02_P0205.stage_office_interview_4')
            xmlids.extend([
                'M02_P0205.stage_office_proposal',
                'M02_P0205.stage_office_hired',
                'M02_P0205.stage_office_reject',
            ])
            stages = self.env['hr.recruitment.stage']
            for xmlid in xmlids:
                stage = self.env.ref(xmlid, raise_if_not_found=False)
                if stage:
                    stages |= stage

            if rec.job_id:
                stages = stages.filtered(lambda st: not st.job_ids or rec.job_id in st.job_ids)

            rec.x_psm_0205_office_stage_statusbar_ids = stages

    @api.depends('stage_id', 'job_id', 'job_id.level_id', 'job_id.level_id.code', 'job_id.x_psm_0205_max_interview_round')
    def _compute_next_interview_round(self):
        stage_map = self._get_stage_round_map()
        for rec in self:
            round_value = stage_map.get(rec.stage_id.id)
            if not round_value and not rec.stage_id:
                round_value = '1'
            if round_value and not rec._is_round_enabled(round_value):
                round_value = False
            rec.x_psm_0205_next_interview_round = round_value

    @api.depends('meeting_ids.x_psm_0205_interview_round', 'meeting_ids.start', 'x_psm_0205_next_interview_round')
    def _compute_next_round_event(self):
        for rec in self:
            rec.x_psm_0205_next_round_event_id = False
            rec.x_psm_0205_next_round_event_needs_notification = False
            if not rec.x_psm_0205_next_interview_round:
                continue
            events = rec.meeting_ids.filtered(lambda ev: ev.x_psm_0205_interview_round == rec.x_psm_0205_next_interview_round)
            if not events:
                continue
            events = events.sorted(key=lambda ev: ev.start or ev.start_date or fields.Datetime.now())
            event = events[0]
            rec.x_psm_0205_next_round_event_id = event
            notification_field = f'x_psm_0205_round{rec.x_psm_0205_next_interview_round}_notification_sent'
            rec.x_psm_0205_next_round_event_needs_notification = not bool(getattr(event, notification_field, False))

    @api.depends(
        'x_psm_0205_recruitment_type',
        'x_psm_0205_next_interview_round',
        'x_psm_0205_interview_date_1',
        'x_psm_0205_interview_date_2',
        'x_psm_0205_interview_date_3',
        'x_psm_0205_interview_date_4',
        'x_psm_0205_max_interview_round',
        'x_psm_0205_eval_round_1_toggle',
        'x_psm_0205_eval_round_2_toggle',
        'x_psm_0205_eval_round_3_toggle',
        'x_psm_0205_eval_round_4_toggle',
        'stage_id',
    )
    def _compute_office_stage_ui_flags(self):
        proposal_stage = self.env.ref('M02_P0205.stage_office_proposal', raise_if_not_found=False)
        hired_stage = self.env.ref('M02_P0205.stage_office_hired', raise_if_not_found=False)

        schedule_stage_ids = set()
        for xmlid in (
            'M02_P0205.stage_office_screening',
            'M02_P0205.stage_office_interview_1',
            'M02_P0205.stage_office_interview_2',
            'M02_P0205.stage_office_interview_3',
        ):
            stage = self.env.ref(xmlid, raise_if_not_found=False)
            if stage:
                schedule_stage_ids.add(stage.id)

        final_stage_xml_by_round = {
            2: 'M02_P0205.stage_office_interview_2',
            3: 'M02_P0205.stage_office_interview_3',
            4: 'M02_P0205.stage_office_interview_4',
        }

        for rec in self:
            rec.x_psm_0205_can_schedule_next_round = False
            rec.x_psm_0205_next_round_date_missing = False
            rec.x_psm_0205_can_ready_for_offer = False
            rec.x_psm_0205_is_offer_stage = False
            rec.x_psm_0205_show_offer_result_block = False

            if rec.x_psm_0205_recruitment_type != 'office':
                continue

            in_schedule_stage = bool(rec.stage_id and rec.stage_id.id in schedule_stage_ids)
            rec.x_psm_0205_can_schedule_next_round = bool(in_schedule_stage and rec.x_psm_0205_next_interview_round)

            if rec.x_psm_0205_can_schedule_next_round:
                date_field = f'x_psm_0205_interview_date_{rec.x_psm_0205_next_interview_round}'
                rec.x_psm_0205_next_round_date_missing = not bool(getattr(rec, date_field, False))

            max_round = max(2, min(int(rec._get_max_interview_round() or 2), 4))
            final_stage = self.env.ref(final_stage_xml_by_round[max_round], raise_if_not_found=False)
            final_stage_ok = bool(final_stage and rec.stage_id == final_stage)
            final_toggle_ok = bool(getattr(rec, f'x_psm_0205_eval_round_{max_round}_toggle', False))
            rec.x_psm_0205_can_ready_for_offer = bool(final_stage_ok and final_toggle_ok)

            is_offer_stage = bool(proposal_stage and rec.stage_id == proposal_stage)
            rec.x_psm_0205_is_offer_stage = is_offer_stage
            rec.x_psm_0205_show_offer_result_block = bool(
                is_offer_stage
                or (hired_stage and rec.stage_id == hired_stage)
            )

    def action_send_interview_slot_survey(self):
        """Gui email de ung vien chon lich phong van vong 1"""
        self.ensure_one()
        if not self.email_from:
            raise exceptions.UserError("Ung vien chua co dia chi email!")
        if self.x_psm_0205_next_interview_round != '1':
            raise exceptions.UserError(_("Chỉ gửi email chọn lịch cho vòng 1."))
        if not self.meeting_ids:
            raise exceptions.UserError("Chua co lich phong van nao de gui lua chon.")

        self._ensure_interview_slot_token()

        template = self.env.ref("M02_P0205.email_interview_slot_survey", raise_if_not_found=False)
        if not template:
            raise exceptions.UserError("Khong tim thay mau email gui lua chon lich phong van!")

        slots = []
        tz = self.env.context.get('tz') or self.env.user.tz or 'Asia/Ho_Chi_Minh'
        for event in self.meeting_ids.sorted(key=lambda ev: ev.start or ev.start_date or fields.Datetime.now()):
            slot_dt = event.start or event.start_date
            if slot_dt:
                slot_time = self._format_local_datetime_for_display(slot_dt, tz=tz)
            else:
                slot_time = "Đang cập nhật"
            slots.append({
                'time': slot_time,
                'url': self.get_interview_slot_url(event),
            })
        ctx = {
            'meeting_slots': slots or [{'time': 'Đang cập nhật', 'url': '#'}],
        }
        body_html = self._build_interview_slot_email_body(ctx['meeting_slots'])
        template.with_context(**ctx).send_mail(
            self.id,
            force_send=True,
            email_values={'body_html': body_html},
        )

        # Tao activity cho HR va Manager de tham gia phong van lan 1
        partner_name = self.partner_name or self.name or "ung vien"
        summary = "Tham gia phong van lan 1"
        note_body = f"Vui long tham gia phong van lan 1 cua {partner_name}."
        users = self.env['res.users']
        if self.user_id:
            users |= self.user_id
        manager_user = self._find_applicant_manager_user()
        if manager_user:
            users |= manager_user
        self._schedule_round_activity_for_users(users, summary, note_body)
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": "Thanh cong",
                "message": "Da gui email lua chon lich phong van cho ung vien.",
                "type": "success",
            }
        }

    def _build_interview_slot_email_body(self, meeting_slots):
        self.ensure_one()
        lines = []
        for slot in meeting_slots or []:
            slot_time = slot.get('time') or 'Đang cập nhật'
            slot_url = slot.get('url') or '#'
            lines.append(
                '<tr>'
                '<td style="padding: 14px 18px; border-bottom: 1px solid #e5e7eb; '
                'font-family: Arial, sans-serif; font-size: 15px; font-weight: 700; color: #111827;">'
                f'{slot_time}'
                '</td>'
                '<td style="padding: 14px 18px; border-bottom: 1px solid #e5e7eb; text-align: right;">'
                '<table role="presentation" cellpadding="0" cellspacing="0" border="0" align="right">'
                '<tr>'
                '<td style="background-color: #1f4e79; border-radius: 4px; text-align: center;">'
                f'<a href="{slot_url}" '
                'style="display: inline-block; padding: 10px 16px; font-family: Arial, sans-serif; '
                'font-size: 14px; font-weight: 700; color: #ffffff; text-decoration: none;">'
                'Chọn lịch này</a>'
                '</td>'
                '</tr>'
                '</table>'
                '</td>'
                '</tr>'
            )
        slot_rows = ''.join(lines) if lines else (
            '<tr><td style="padding: 14px 18px; font-family: Arial, sans-serif; font-size: 14px; '
            'color: #6b7280;">Đang cập nhật</td></tr>'
        )
        applicant_name = self.partner_name or self.display_name or 'ứng viên'
        job_name = self.job_id.name or 'vị trí ứng tuyển'
        return (
            '<table role="presentation" cellpadding="0" cellspacing="0" border="0" width="100%" '
            'style="width:100%; border-collapse:collapse; background-color:#f3f4f6; margin:0; padding:0;">'
            '<tr>'
            '<td align="center" style="padding:24px 12px;">'
            '<table role="presentation" cellpadding="0" cellspacing="0" border="0" width="680" '
            'style="width:680px; max-width:680px; border-collapse:collapse; background-color:#ffffff; border:1px solid #e5e7eb;">'
            '<tr>'
            '<td style="padding:20px 24px; border-bottom:4px solid #f6c343; font-family:Arial, sans-serif; '
            'font-size:30px; font-weight:700; line-height:1.2; color:#111827;">'
            'Chọn lịch phỏng vấn'
            '</td>'
            '</tr>'
            '<tr>'
            '<td style="padding:24px; font-family:Arial, sans-serif; font-size:16px; line-height:1.7; color:#111827;">'
            f'<p style="margin:0 0 14px; font-family:Arial, sans-serif; font-size:16px; line-height:1.7; color:#111827;">'
            f'Chào <strong>{applicant_name}</strong>,</p>'
            f'<p style="margin:0 0 22px; font-family:Arial, sans-serif; font-size:16px; line-height:1.7; color:#111827;">'
            f'Cảm ơn bạn đã ứng tuyển vị trí <strong>{job_name}</strong>. '
            'Vui lòng chọn một khung giờ phù hợp dưới đây để tham gia phỏng vấn vòng 1.'
            '</p>'
            '<table role="presentation" cellpadding="0" cellspacing="0" border="0" width="100%" '
            'style="width:100%; border-collapse:collapse; border:1px solid #e5e7eb; background-color:#ffffff;">'
            '<tr>'
            '<td style="padding:14px 18px; background-color:#fff8e1; border-bottom:1px solid #e5e7eb; '
            'font-family:Arial, sans-serif; font-size:14px; color:#6b7280;">'
            'Khung giờ được hiển thị theo giờ địa phương của lịch hẹn.'
            '</td>'
            '</tr>'
            f'{slot_rows}'
            '</table>'
            '<p style="margin:24px 0 8px; font-family:Arial, sans-serif; font-size:15px; line-height:1.7; color:#111827;">'
            'Sau khi bạn chọn lịch, hệ thống sẽ ghi nhận ngay và đội ngũ tuyển dụng sẽ liên hệ lại sớm nhất.'
            '</p>'
            '<p style="margin:0; font-family:Arial, sans-serif; font-size:15px; line-height:1.7; color:#111827;">'
            'Trân trọng,<br/><strong>Bộ phận Tuyển dụng</strong></p>'
            '</td>'
            '</tr>'
            '</table>'
            '</td>'
            '</tr>'
            '</table>'
        )

    def _build_round_notification_email_body(self, event, round_no):
        self.ensure_one()
        round_titles = {
            2: 'Thông báo lịch phỏng vấn vòng 2',
            3: 'Thông báo lịch phỏng vấn vòng 3',
            4: 'Thông báo lịch phỏng vấn vòng 4',
        }
        intro_map = {
            2: 'Chúc mừng bạn đã vượt qua vòng 1. Chúng tôi xin gửi đến bạn lịch phỏng vấn vòng 2 với thông tin như sau.',
            3: 'Chúc mừng bạn đã vượt qua vòng 2. Chúng tôi xin gửi đến bạn lịch phỏng vấn vòng 3 với thông tin như sau.',
            4: 'Chúc mừng bạn đã vượt qua vòng 3. Chúng tôi xin gửi đến bạn lịch phỏng vấn vòng 4 với thông tin như sau.',
        }
        title = round_titles.get(round_no, f'Thông báo lịch phỏng vấn vòng {round_no}')
        applicant_name = self.partner_name or self.display_name or 'ứng viên'
        job_name = self.job_id.name or 'vị trí ứng tuyển'
        company_partner = event.user_id.company_id.partner_id if event.user_id and event.user_id.company_id else False
        event_time = self._format_local_datetime_for_display(event.start) if event.start else 'Đang cập nhật'
        event_location = event.location or self._get_0205_default_interview_location(company_partner)
        organizer_name = event.user_id.name or self._get_0205_default_interview_owner_name()
        intro_text = intro_map.get(round_no, 'Chúng tôi xin gửi đến bạn lịch phỏng vấn với thông tin như sau.')
        return (
            '<table role="presentation" cellpadding="0" cellspacing="0" border="0" width="100%" '
            'style="width:100%;border-collapse:collapse;background-color:#f4f4f4;margin:0;padding:0;">'
            '<tr>'
            '<td align="center" style="padding:24px 12px;">'
            '<table role="presentation" cellpadding="0" cellspacing="0" border="0" width="680" '
            'style="width:680px;max-width:680px;border-collapse:collapse;background-color:#FFFFFF;border:1px solid #e5e5e5;">'
            '<tr>'
            '<td style="padding:0;background-color:#FFFFFF;">'
            '<table role="presentation" cellpadding="0" cellspacing="0" border="0" width="100%" style="width:100%;border-collapse:collapse;">'
            '<tr>'
            '<td style="height:14px;width:25%;background-color:#FFC72C;"></td>'
            '<td style="height:14px;width:25%;background-color:#DA291C;"></td>'
            '<td style="height:14px;width:25%;background-color:#000000;"></td>'
            '<td style="height:14px;width:25%;background-color:#FFFFFF;"></td>'
            '</tr>'
            '</table>'
            '</td>'
            '</tr>'
            '<tr>'
            '<td style="padding:28px 32px 24px 32px;font-family:Arial, sans-serif;color:#000000;">'
            f'<div style="font-family:Arial, sans-serif;font-size:32px;line-height:1.15;font-weight:700;color:#000000;margin-bottom:10px;">{title}</div>'
            f'<div style="font-family:Arial, sans-serif;font-size:16px;line-height:1.7;color:#4b5563;">Vị trí ứng tuyển: <strong>{job_name}</strong></div>'
            '</td>'
            '</tr>'
            '<tr>'
            '<td style="padding:0 32px 28px 32px;font-family:Arial, sans-serif;color:#111111;">'
            f'<p style="margin:0 0 16px 0;font-family:Arial, sans-serif;font-size:16px;line-height:1.7;color:#111111;">Thân gửi <strong>{applicant_name}</strong>,</p>'
            f'<p style="margin:0 0 18px 0;font-family:Arial, sans-serif;font-size:16px;line-height:1.8;color:#111111;">{intro_text}</p>'
            '<table role="presentation" cellpadding="0" cellspacing="0" border="0" width="100%" '
            'style="width:100%;border-collapse:collapse;margin:24px 0;background-color:#fffdf8;border:1px solid #ece7df;">'
            '<tr>'
            '<td colspan="2" style="padding:16px 20px;background-color:#FFF4CC;border-bottom:1px solid #ece7df;'
            'font-family:Arial, sans-serif;font-size:14px;font-weight:700;color:#000000;letter-spacing:0.04em;text-transform:uppercase;">'
            'Thông tin phỏng vấn'
            '</td>'
            '</tr>'
            '<tr>'
            '<td style="padding:16px 20px;width:160px;font-family:Arial, sans-serif;font-size:15px;font-weight:700;color:#DA291C;border-bottom:1px solid #ece7df;">'
            'Thời gian'
            '</td>'
            f'<td style="padding:16px 20px;font-family:Arial, sans-serif;font-size:15px;color:#111111;border-bottom:1px solid #ece7df;">{event_time}</td>'
            '</tr>'
            '<tr>'
            '<td style="padding:16px 20px;width:160px;font-family:Arial, sans-serif;font-size:15px;font-weight:700;color:#DA291C;border-bottom:1px solid #ece7df;">'
            'Địa điểm'
            '</td>'
            f'<td style="padding:16px 20px;font-family:Arial, sans-serif;font-size:15px;color:#111111;border-bottom:1px solid #ece7df;">{event_location}</td>'
            '</tr>'
            '<tr>'
            '<td style="padding:16px 20px;width:160px;font-family:Arial, sans-serif;font-size:15px;font-weight:700;color:#DA291C;">'
            'Người tổ chức'
            '</td>'
            f'<td style="padding:16px 20px;font-family:Arial, sans-serif;font-size:15px;color:#111111;">{organizer_name}</td>'
            '</tr>'
            '</table>'
            '<p style="margin:0 0 16px 0;font-family:Arial, sans-serif;font-size:16px;line-height:1.8;color:#111111;">'
            'Vui lòng phản hồi email này để xác nhận tham gia hoặc đề xuất lịch khác nếu thời gian trên chưa phù hợp.'
            '</p>'
            '<p style="margin:0;font-family:Arial, sans-serif;font-size:16px;line-height:1.8;color:#111111;">'
            'Trân trọng,<br/><strong>Bộ phận Tuyển dụng (MCD)</strong></p>'
            '</td>'
            '</tr>'
            '</table>'
            '</td>'
            '</tr>'
            '</table>'
        )

    def _build_interview_invitation_email_body(self, interview_label, interview_date, interviewer_name):
        self.ensure_one()
        applicant_name = self.partner_name or self.display_name or 'ứng viên'
        job_name = self.job_id.name or 'vị trí ứng tuyển'
        location = self._get_0205_default_interview_location()
        return (
            '<table role="presentation" cellpadding="0" cellspacing="0" border="0" width="100%" '
            'style="width:100%;border-collapse:collapse;background-color:#f4f4f4;margin:0;padding:0;">'
            '<tr>'
            '<td align="center" style="padding:24px 12px;">'
            '<table role="presentation" cellpadding="0" cellspacing="0" border="0" width="680" '
            'style="width:680px;max-width:680px;border-collapse:collapse;background-color:#FFFFFF;border:1px solid #e5e5e5;">'
            '<tr>'
            '<td style="padding:0;background-color:#FFFFFF;">'
            '<table role="presentation" cellpadding="0" cellspacing="0" border="0" width="100%" style="width:100%;border-collapse:collapse;">'
            '<tr>'
            '<td style="height:14px;width:25%;background-color:#FFC72C;"></td>'
            '<td style="height:14px;width:25%;background-color:#DA291C;"></td>'
            '<td style="height:14px;width:25%;background-color:#000000;"></td>'
            '<td style="height:14px;width:25%;background-color:#FFFFFF;"></td>'
            '</tr>'
            '</table>'
            '</td>'
            '</tr>'
            '<tr>'
            '<td style="padding:28px 32px 24px 32px;font-family:Arial, sans-serif;color:#000000;">'
            '<div style="font-family:Arial, sans-serif;font-size:34px;line-height:1.15;font-weight:700;color:#000000;margin-bottom:10px;">'
            'Thư mời phỏng vấn'
            '</div>'
            f'<div style="font-family:Arial, sans-serif;font-size:16px;line-height:1.7;color:#4b5563;">{interview_label} - <strong>{job_name}</strong></div>'
            '</td>'
            '</tr>'
            '<tr>'
            '<td style="padding:0 32px 28px 32px;font-family:Arial, sans-serif;color:#111111;">'
            f'<p style="margin:0 0 16px 0;font-family:Arial, sans-serif;font-size:16px;line-height:1.7;color:#111111;">Thân gửi <strong>{applicant_name}</strong>,</p>'
            '<p style="margin:0 0 18px 0;font-family:Arial, sans-serif;font-size:16px;line-height:1.8;color:#111111;">'
            'Cảm ơn bạn đã quan tâm đến cơ hội nghề nghiệp tại công ty. Sau khi xem xét hồ sơ và các bước đánh giá trước đó, '
            'chúng tôi trân trọng mời bạn tham gia buổi phỏng vấn theo thông tin dưới đây.'
            '</p>'
            '<table role="presentation" cellpadding="0" cellspacing="0" border="0" width="100%" '
            'style="width:100%;border-collapse:collapse;margin:24px 0;background-color:#fffdf8;border:1px solid #ece7df;">'
            '<tr>'
            '<td colspan="2" style="padding:16px 20px;background-color:#FFF4CC;border-bottom:1px solid #ece7df;'
            'font-family:Arial, sans-serif;font-size:14px;font-weight:700;color:#000000;letter-spacing:0.04em;text-transform:uppercase;">'
            'Thông tin phỏng vấn'
            '</td>'
            '</tr>'
            '<tr>'
            '<td style="padding:16px 20px;width:160px;font-family:Arial, sans-serif;font-size:15px;font-weight:700;color:#DA291C;border-bottom:1px solid #ece7df;">'
            'Thời gian'
            '</td>'
            f'<td style="padding:16px 20px;font-family:Arial, sans-serif;font-size:15px;color:#111111;border-bottom:1px solid #ece7df;">{interview_date or "Sẽ thông báo sau"}</td>'
            '</tr>'
            '<tr>'
            '<td style="padding:16px 20px;width:160px;font-family:Arial, sans-serif;font-size:15px;font-weight:700;color:#DA291C;border-bottom:1px solid #ece7df;">'
            'Địa điểm'
            '</td>'
            f'<td style="padding:16px 20px;font-family:Arial, sans-serif;font-size:15px;color:#111111;border-bottom:1px solid #ece7df;">{location}</td>'
            '</tr>'
            '<tr>'
            '<td style="padding:16px 20px;width:160px;font-family:Arial, sans-serif;font-size:15px;font-weight:700;color:#DA291C;">'
            'Người phỏng vấn'
            '</td>'
            f'<td style="padding:16px 20px;font-family:Arial, sans-serif;font-size:15px;color:#111111;">{interviewer_name or "Hội đồng Tuyển dụng"}</td>'
            '</tr>'
            '</table>'
            '<p style="margin:0 0 16px 0;font-family:Arial, sans-serif;font-size:16px;line-height:1.8;color:#111111;">'
            'Vui lòng phản hồi email này để xác nhận tham gia hoặc đề xuất lịch khác nếu thời gian trên chưa phù hợp.'
            '</p>'
            '<p style="margin:0;font-family:Arial, sans-serif;font-size:16px;line-height:1.8;color:#111111;">'
            'Trân trọng,<br/><strong>Bộ phận Tuyển dụng (MCD)</strong></p>'
            '</td>'
            '</tr>'
            '</table>'
            '</td>'
            '</tr>'
            '</table>'
        )

    def _log_interview_email_to_chatter(self, subject, body_html):
        """Keep a copy of interview-related outbound emails on the applicant chatter."""
        self.ensure_one()
        from markupsafe import Markup

        chatter_body = "<p><strong>Subject:</strong> %s</p>%s" % (subject or '', body_html or '')
        self.message_post(
            body=Markup(chatter_body),
            message_type='comment',
            subtype_xmlid='mail.mt_note',
        )

    def action_create_meeting(self):
        res = super().action_create_meeting()
        context = dict(res.get('context') or {})
        default_partner_ids = list(context.get('default_partner_ids') or [])
        if self.partner_id:
            default_partner_ids = [partner_id for partner_id in default_partner_ids if partner_id != self.partner_id.id]
        context['default_partner_ids'] = default_partner_ids
        # Recruitment emails are sent explicitly; avoid automatic calendar attendee invitations.
        context['no_mail_to_attendees'] = True
        if self.x_psm_0205_next_interview_round:
            context['default_x_psm_0205_interview_round'] = self.x_psm_0205_next_interview_round
        elif 'default_x_psm_0205_interview_round' in context:
            context.pop('default_x_psm_0205_interview_round')
        res['context'] = context
        return res

    def _get_round_event(self, round_no):
        events = self.meeting_ids.filtered(lambda ev: ev.x_psm_0205_interview_round == str(round_no))
        if not events:
            return False
        return events.sorted(key=lambda ev: ev.start or ev.start_date or fields.Datetime.now())[0]

    def _ensure_previous_round_completed(self, round_no):
        self.ensure_one()
        self._ensure_round_enabled(round_no)
        if round_no <= 1:
            return
        previous_toggle = getattr(self, f'x_psm_0205_eval_round_{round_no-1}_toggle', False)
        if not previous_toggle:
            warning_message = getattr(self, f'x_psm_0205_eval_round_{round_no-1}_primary_warning', False)
            if warning_message:
                raise exceptions.UserError(warning_message)
            raise exceptions.UserError(
                _("Ứng viên chưa hoàn thành vòng %(round)s, không thể gửi lịch tiếp theo.") % {'round': round_no-1}
            )

    def _ensure_round_passed(self, round_no):
        self.ensure_one()
        self._ensure_round_enabled(round_no)
        if getattr(self, f'x_psm_0205_eval_round_{round_no}_toggle', False):
            return
        warning_message = getattr(self, f'x_psm_0205_eval_round_{round_no}_primary_warning', False)
        if warning_message:
            raise exceptions.UserError(warning_message)
        raise exceptions.UserError(
            _("Ứng viên chưa đạt vòng %(round)s theo kết luận của người phỏng vấn chính.") % {'round': round_no}
        )

    def _ensure_round_notification_allowed(self, round_no):
        self.ensure_one()
        round_no = int(round_no)
        max_round = self._get_max_interview_round()
        if round_no > max_round:
            raise exceptions.UserError(
                _("Vị trí này chỉ áp dụng tối đa %(max_round)s vòng phỏng vấn, nên không thể gửi thông báo cho vòng %(round)s.") % {
                    'max_round': max_round,
                    'round': round_no,
                }
            )

    def _build_round_context(self, event, round_no):
        company_partner = event.user_id.company_id.partner_id if event.user_id and event.user_id.company_id else False
        return {
            'interview_datetime': self._format_local_datetime_for_display(event.start) if event.start else '',
            'interview_location': event.location or self._get_0205_default_interview_location(company_partner),
            'interview_owner': event.user_id.name or self._get_0205_default_interview_owner_name(),
            'interview_label': f'Vòng {round_no}',
        }

    def _send_interview_round_notification(self, round_no):
        self.ensure_one()
        self._ensure_round_notification_allowed(round_no)
        self._ensure_previous_round_completed(round_no)
        event = self._get_round_event(round_no)
        if not event:
            raise exceptions.UserError(_("Chưa có lịch phỏng vấn vòng %(round)s do CEO tạo.") % {'round': round_no})
        notification_field = f'x_psm_0205_round{round_no}_notification_sent'
        if getattr(event, notification_field, False):
            raise exceptions.UserError(_("Thông báo vòng %(round)s đã được gửi.") % {'round': round_no})
        template_ref = self.ROUND_NOTIFICATION_TEMPLATES.get(str(round_no))
        template = self.env.ref(template_ref, raise_if_not_found=False) if template_ref else False
        if not template:
            raise exceptions.UserError(_("Không tìm thấy mẫu thư mời vòng %(round)s.") % {'round': round_no})
        email_from = self._get_0205_default_email_from(
            prefer_user=True,
            user=event.user_id,
        )
        email_to = self.email_from or self.partner_id.email
        subject = f"Thông báo lịch phỏng vấn vòng {round_no} - {self.job_id.name or ''}".strip()
        body_html = self._build_round_notification_email_body(event, round_no)
        template.with_context(**self._build_round_context(event, round_no)).send_mail(
            event.id,
            force_send=True,
            email_values={
                'subject': subject,
                'email_from': email_from,
                'email_to': email_to,
                'body_html': body_html,
            },
        )
        self._log_interview_email_to_chatter(subject, body_html)
        setattr(event, notification_field, True)
        date_field = f'x_psm_0205_interview_date_{round_no}'
        if hasattr(self, date_field):
            setattr(self, date_field, event.start)
        self.x_psm_0205_interview_slot_event_id = event
        return _("Đã gửi email mời ứng viên tham gia phỏng vấn vòng %(round)s theo lịch CEO cung cấp.") % {'round': round_no}

    def _notify_round_sent(self, message):
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Đã gửi"),
                "message": message,
                "type": "success",
            },
        }

    def action_send_interview_round2_notification(self):
        return self._notify_round_sent(self._send_interview_round_notification(2))

    def action_send_interview_round3_notification(self):
        return self._notify_round_sent(self._send_interview_round_notification(3))

    def action_send_interview_round4_notification(self):
        return self._notify_round_sent(self._send_interview_round_notification(4))

    def _manager_user_from_department(self, department):
        if not department:
            return False
        manager = department.manager_id
        return manager.user_id if manager and manager.user_id else False

    def _find_applicant_manager_user(self):
        self.ensure_one()
        job = self.job_id
        department = job.department_id if job else self.department_id
        user = self._manager_user_from_department(department)
        if user:
            return user
        department = self.department_id
        user = self._manager_user_from_department(department)
        if user:
            return user
        if job:
            line = self.env['x_psm_recruitment_request_line'].search(
                [('job_id', '=', job.id)],
                order='id desc',
                limit=1,
            )
            if line:
                return self._manager_user_from_department(line.department_id)
        return False

    def _get_recruitment_responsible_user(self):
        self.ensure_one()
        return self.user_id or self.job_id.user_id

    def _schedule_offer_handoff_activity(self):
        self.ensure_one()
        responsible_user = self._get_recruitment_responsible_user()
        if not responsible_user:
            return
        final_round = self._get_max_interview_round()
        summary = _("Chuẩn bị Offer")
        note = _("Ứng viên %(name)s đã đạt vòng phỏng vấn cuối (%(round)s) theo level hiện tại. Vui lòng chuẩn bị bước Offer và chuyển hồ sơ sang đề xuất chính thức.") % {
            'name': self.partner_name or self.display_name,
            'round': final_round,
        }
        self._schedule_round_activity_for_users(responsible_user, summary, note)

    def _schedule_offer_followup_activity(self):
        self.ensure_one()
        responsible_user = self._get_recruitment_responsible_user()
        if not responsible_user:
            return
        summary = _("Theo dõi phản hồi Offer")
        note = _("Offer đã được gửi cho ứng viên %(name)s. Vui lòng theo dõi phản hồi và xác nhận khi ứng viên đã ký.") % {
            'name': self.partner_name or self.display_name
        }
        self._schedule_round_activity_for_users(responsible_user, summary, note)

    def action_ready_for_offer(self):
        """Transition to Proposal stage"""
        # Sau khi ứng viên hoàn tất các vòng phỏng vấn, nút này chuyển hồ sơ
        # sang stage Offer để HR bắt đầu gửi đề nghị chính thức.
        self.ensure_one()
        self._ensure_round_passed(self._get_max_interview_round())
        stage = self.env.ref('M02_P0205.stage_office_proposal', raise_if_not_found=False)
        if stage:
            self.stage_id = stage.id
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Thành công',
                    'message': 'Đã chuyển hồ sơ sang trạng thái Đề xuất chính thức.',
                    'type': 'success',
                    'next': {
                        'type': 'ir.actions.client',
                        'tag': 'reload',
                    },
                }
            }
        return False

    def action_send_offer(self):
        """Action to send Offer Letter"""
        self.ensure_one()
        if not self.salary_proposed:
            raise exceptions.UserError("Vui lòng nhập Lương đề nghị (Proposed Salary) trước khi gửi Offer!")
            
        template = self.env.ref('M02_P0205.email_offer_letter_office', raise_if_not_found=False)
        if template:
            template.send_mail(self.id, force_send=True)
            self.x_psm_0205_offer_status = 'proposed'
            self._schedule_offer_followup_activity()
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Thành công',
                    'message': 'Đã gửi Thư mời nhận việc (Offer Letter) cho ứng viên.',
                    'type': 'success',
                    'next': {
                        'type': 'ir.actions.client',
                        'tag': 'reload',
                    },
                }
            }
        else:
            raise exceptions.UserError("Không tìm thấy mẫu email Offer Letter!")

    def action_confirm_signed(self):
        """Confirm contract is signed and move directly to Hired stage"""
        # Khi ứng viên xác nhận nhận offer, hồ sơ được đẩy thẳng sang giai đoạn
        # đã tuyển để kích hoạt onboarding ngay, không đi qua bước Probation nữa.
        self.ensure_one()
        stage = self.env.ref('M02_P0205.stage_office_hired', raise_if_not_found=False)
        if stage:
            self.write({
                'stage_id': stage.id,
                'x_psm_0205_offer_status': 'accepted',
            })
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Chúc mừng!',
                    'message': 'Ứng viên đã chấp nhận Offer. Đã chuyển sang trạng thái Đã Tuyển.',
                    'type': 'success',
                    'next': {
                        'type': 'ir.actions.client',
                        'tag': 'reload',
                    },
                }
            }
        return False

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('interviewer_ids') or not vals.get('job_id'):
                job = self.env['hr.job'].browse(vals['job_id']) if vals.get('job_id') else False
            else:
                job = self.env['hr.job'].browse(vals['job_id'])
                default_users = job.interviewer_ids.filtered(lambda user: not user.share)
                if default_users:
                    vals['interviewer_ids'] = [(6, 0, default_users.ids)]

            if job and not self._vals_include_applicant_skills(vals):
                commands = self._prepare_applicant_skill_commands_from_job(job)
                if commands:
                    vals['applicant_skill_ids'] = commands
        applicants = super().create(vals_list)
        applicants._sync_missing_skills_from_job()
        creator = self.env.user
        scheduled = False
        if creator._is_public() or creator.has_group('base.group_portal'):
            self._schedule_portal_activity(applicants)
            scheduled = True

        if self._context.get('from_website') and not scheduled:
            self._schedule_portal_activity(applicants)
        return applicants

    def _schedule_portal_activity(self, applicants):
        for applicant in applicants:
            summary = _('ứng viên mới: %s') % (applicant.partner_name or applicant.display_name)
            note = _(
                'ứng viên <b>%s</b> vừa nộp đơn ứng tuyển vị trí <b>%s</b>. Vui lòng xem xét hồ sơ.'
            ) % (applicant.partner_name or applicant.display_name, applicant.job_id.name or '')

            if applicant.x_psm_0205_recruitment_type == 'store':
                applicant._schedule_store_hr_activity(
                    summary=summary,
                    note=note,
                    activity_label='website_apply_submit',
                )
                continue

            responsible = applicant.user_id or applicant.job_id.user_id
            if responsible:
                applicant.activity_schedule(
                    'mail.mail_activity_data_todo',
                    user_id=responsible.id,
                    summary=summary,
                    note=note,
                )

    # Step 32: Onboarding Trigger
    def write(self, vals):
        # Check if moved to "Signed" stage
        if 'stage_id' in vals:
            stage = self.env['hr.recruitment.stage'].browse(vals['stage_id'])
            if stage.hired_stage:
                 for rec in self:
                    rec.message_post(body="🎉 <b>Chúc mừng!</b> Hồ sơ đã được chuyển sang trạng thái <b>Đã Tuyển & Tiếp Nhận</b>. Quy trình Onboarding bắt đầu.")
        skip_job_interviewers_sync = self.env.context.get('skip_job_interviewers_sync')
        skip_job_skill_sync = self.env.context.get('skip_job_skill_sync')
        res = super(HrApplicant, self).write(vals)

        if not skip_job_interviewers_sync and 'job_id' in vals and 'interviewer_ids' not in vals:
            for rec in self.filtered(lambda applicant: applicant.job_id and not applicant.interviewer_ids):
                default_users = rec._get_job_default_interviewer_users()
                if default_users:
                    rec.with_context(skip_job_interviewers_sync=True).write({
                        'interviewer_ids': [(6, 0, default_users.ids)],
                    })

        if not skip_job_skill_sync and 'job_id' in vals and not self._vals_include_applicant_skills(vals):
            self._sync_missing_skills_from_job()

        if 'x_psm_0205_interview_date_1' in vals and vals.get('x_psm_0205_interview_date_1'):
            activity_type = self.env.ref('mail.mail_activity_data_todo')
            for rec in self:
                if not rec.x_psm_0205_interview_date_1:
                    continue
                summary = 'Can moi PV L1'
                note = 'Ung vien da chon lich phong van Vong 1. Vui long nhan nut Moi PV L1.'

                if rec.x_psm_0205_recruitment_type == 'store':
                    rec._schedule_store_hr_activity(
                        summary=summary,
                        note=note,
                        activity_label='can_moi_pv_l1',
                    )
                    continue

                user = rec.user_id or rec.job_id.user_id
                if not user:
                    continue
                exists = self.env['mail.activity'].search_count([
                    ('res_model', '=', 'hr.applicant'),
                    ('res_id', '=', rec.id),
                    ('activity_type_id', '=', activity_type.id),
                    ('user_id', '=', user.id),
                    ('summary', '=', summary),
                ])
                if exists:
                    continue
                rec.activity_schedule(
                    'mail.mail_activity_data_todo',
                    user_id=user.id,
                    summary=summary,
                    note=note,
                )

        return res

    # Evaluation Forms for Rounds 1-4
    x_psm_0205_eval_l1_id = fields.Many2one(
        'x_psm_applicant_evaluation', string='Đánh giá Vòng 1',
        compute='_compute_eval_round_metrics', store=True, copy=False)
    x_psm_0205_eval_l2_id = fields.Many2one(
        'x_psm_applicant_evaluation', string='Đánh giá Vòng 2',
        compute='_compute_eval_round_metrics', store=True, copy=False)
    x_psm_0205_eval_l3_id = fields.Many2one(
        'x_psm_applicant_evaluation', string='Đánh giá Vòng 3',
        compute='_compute_eval_round_metrics', store=True, copy=False)
    x_psm_0205_eval_l4_id = fields.Many2one(
        'x_psm_applicant_evaluation', string='Đánh giá Vòng 4',
        compute='_compute_eval_round_metrics', store=True, copy=False)
    x_psm_0205_primary_interviewer_l1_user_id = fields.Many2one(
        'res.users',
        string='Người phỏng vấn chính Vòng 1',
        copy=False,
        tracking=True,
        domain="[('share', '=', False)]",
    )
    x_psm_0205_primary_interviewer_l2_user_id = fields.Many2one(
        'res.users',
        string='Người phỏng vấn chính Vòng 2',
        copy=False,
        tracking=True,
        domain="[('share', '=', False)]",
    )
    x_psm_0205_primary_interviewer_l3_user_id = fields.Many2one(
        'res.users',
        string='Người phỏng vấn chính Vòng 3',
        copy=False,
        tracking=True,
        domain="[('id', 'in', x_psm_0205_allowed_primary_interviewer_l3_ids)]",
    )
    x_psm_0205_primary_interviewer_l4_user_id = fields.Many2one(
        'res.users',
        string='Người phỏng vấn chính Vòng 4',
        copy=False,
        tracking=True,
        domain="[('id', 'in', x_psm_0205_allowed_primary_interviewer_l4_ids)]",
    )
    x_psm_0205_allowed_primary_interviewer_l3_ids = fields.Many2many(
        'res.users',
        compute='_compute_allowed_primary_interviewer_users',
        string='Danh sách BOD khả dụng',
    )
    x_psm_0205_allowed_primary_interviewer_l4_ids = fields.Many2many(
        'res.users',
        compute='_compute_allowed_primary_interviewer_users',
        string='Danh sách ABU khả dụng',
    )
    x_psm_0205_evaluation_line_ids = fields.One2many(
        'x_psm_applicant_evaluation', 'applicant_id', string='Danh sách đánh giá')

    x_psm_0205_eval_round_1_score = fields.Float(string='Điểm vòng 1', compute='_compute_eval_round_metrics', store=True, digits=(16, 2))
    x_psm_0205_eval_round_2_score = fields.Float(string='Điểm vòng 2', compute='_compute_eval_round_metrics', store=True, digits=(16, 2))
    x_psm_0205_eval_round_3_score = fields.Float(string='Điểm vòng 3', compute='_compute_eval_round_metrics', store=True, digits=(16, 2))
    x_psm_0205_eval_round_4_score = fields.Float(string='Điểm vòng 4', compute='_compute_eval_round_metrics', store=True, digits=(16, 2))
    ROUND_STATUS = [('pass', 'Pass'), ('fail', 'Fail')]
    x_psm_0205_eval_round_1_pass = fields.Selection(ROUND_STATUS, string='Kết quả vòng 1', compute='_compute_eval_round_metrics', store=True)
    x_psm_0205_eval_round_2_pass = fields.Selection(ROUND_STATUS, string='Kết quả vòng 2', compute='_compute_eval_round_metrics', store=True)
    x_psm_0205_eval_round_3_pass = fields.Selection(ROUND_STATUS, string='Kết quả vòng 3', compute='_compute_eval_round_metrics', store=True)
    x_psm_0205_eval_round_4_pass = fields.Selection(ROUND_STATUS, string='Kết quả vòng 4', compute='_compute_eval_round_metrics', store=True)
    x_psm_0205_eval_round_1_toggle = fields.Boolean(string='Vòng 1 đạt', compute='_compute_eval_round_metrics', store=True)
    x_psm_0205_eval_round_2_toggle = fields.Boolean(string='Vòng 2 đạt', compute='_compute_eval_round_metrics', store=True)
    x_psm_0205_eval_round_3_toggle = fields.Boolean(string='Vòng 3 đạt', compute='_compute_eval_round_metrics', store=True)
    x_psm_0205_eval_round_4_toggle = fields.Boolean(string='Vòng 4 đạt', compute='_compute_eval_round_metrics', store=True)
    x_psm_0205_eval_round_1_primary_pending = fields.Boolean(
        string='Vòng 1 chờ kết luận người chính',
        compute='_compute_primary_interviewer_warnings',
    )
    x_psm_0205_eval_round_2_primary_pending = fields.Boolean(
        string='Vòng 2 chờ kết luận người chính',
        compute='_compute_primary_interviewer_warnings',
    )
    x_psm_0205_eval_round_3_primary_pending = fields.Boolean(
        string='Vòng 3 chờ kết luận người chính',
        compute='_compute_primary_interviewer_warnings',
    )
    x_psm_0205_eval_round_4_primary_pending = fields.Boolean(
        string='Vòng 4 chờ kết luận người chính',
        compute='_compute_primary_interviewer_warnings',
    )
    x_psm_0205_eval_round_1_primary_warning = fields.Char(
        string='Cảnh báo người chính vòng 1',
        compute='_compute_primary_interviewer_warnings',
    )
    x_psm_0205_eval_round_2_primary_warning = fields.Char(
        string='Cảnh báo người chính vòng 2',
        compute='_compute_primary_interviewer_warnings',
    )
    x_psm_0205_eval_round_3_primary_warning = fields.Char(
        string='Cảnh báo người chính vòng 3',
        compute='_compute_primary_interviewer_warnings',
    )
    x_psm_0205_eval_round_4_primary_warning = fields.Char(
        string='Cảnh báo người chính vòng 4',
        compute='_compute_primary_interviewer_warnings',
    )
    x_psm_0205_needs_primary_interviewer_review = fields.Boolean(
        string='Cần rà người phỏng vấn chính',
        compute='_compute_primary_interviewer_review',
        store=True,
    )
    x_psm_0205_primary_interviewer_review_note = fields.Char(
        string='Ghi chú rà người phỏng vấn chính',
        compute='_compute_primary_interviewer_review',
    )

    def _recommendation_score(self, recommendation):
        return {'pass': 1, 'fail': -1}.get(recommendation, 0)

    def _get_primary_interviewer_user(self, round_no):
        self.ensure_one()
        field_name = f'x_psm_0205_primary_interviewer_l{round_no}_user_id'
        return getattr(self, field_name, False)

    def _get_primary_evaluation_for_round(self, round_no):
        self.ensure_one()
        primary_user = self._get_primary_interviewer_user(round_no)
        if not primary_user:
            return self.env['x_psm_applicant_evaluation']
        return self.x_psm_0205_evaluation_line_ids.filtered(
            lambda line: line.interview_round == str(round_no) and line.interviewer_id == primary_user
        )[:1]

    def _get_primary_round_decision(self, round_no):
        self.ensure_one()
        primary_user = self._get_primary_interviewer_user(round_no)
        primary_eval = self._get_primary_evaluation_for_round(round_no)
        recommendation = primary_eval.recommendation if primary_eval else False
        return {
            'primary_user': primary_user,
            'primary_eval': primary_eval,
            'recommendation': recommendation,
        }

    def _get_max_reached_interview_round(self):
        self.ensure_one()
        max_round = self._get_max_interview_round()
        stage_round = 0
        stage_map = {
            'M02_P0205.stage_office_interview_1': 1,
            'M02_P0205.stage_office_interview_2': 2,
            'M02_P0205.stage_office_interview_3': 3,
            'M02_P0205.stage_office_interview_4': 4,
        }
        for xmlid, round_no in stage_map.items():
            stage = self.env.ref(xmlid, raise_if_not_found=False)
            if stage and self.stage_id == stage:
                stage_round = round_no
                break
        if not stage_round:
            for xmlid in ('M02_P0205.stage_office_proposal', 'M02_P0205.stage_office_hired'):
                stage = self.env.ref(xmlid, raise_if_not_found=False)
                if stage and self.stage_id == stage:
                    stage_round = max_round
                    break
        date_round = 0
        for round_no in range(1, min(4, max_round) + 1):
            if getattr(self, f'x_psm_0205_interview_date_{round_no}', False):
                date_round = round_no
        eval_round = 0
        for line in self.x_psm_0205_evaluation_line_ids:
            if line.interview_round and line.interview_round.isdigit():
                eval_round = max(eval_round, int(line.interview_round))
        eval_round = min(eval_round, max_round)
        return min(max(stage_round, date_round, eval_round), max_round)

    def _schedule_round_activity_for_users(self, users, summary, note):
        self.ensure_one()
        activity_type = self.env.ref('mail.mail_activity_data_todo', raise_if_not_found=False)
        if not activity_type or not users:
            return
        valid_users = users.filtered(lambda user: not user.share)
        for user in valid_users:
            exists = self.env['mail.activity'].search_count([
                ('res_model', '=', 'hr.applicant'),
                ('res_id', '=', self.id),
                ('user_id', '=', user.id),
                ('activity_type_id', '=', activity_type.id),
                ('summary', '=', summary),
            ])
            if exists:
                continue
            self.activity_schedule(
                'mail.mail_activity_data_todo',
                user_id=user.id,
                summary=summary,
                note=note,
            )

    def _schedule_round_activity_for_group(self, group_xmlid, summary, note):
        self.ensure_one()
        users = self._get_group_users(group_xmlid)
        self._schedule_round_activity_for_users(users, summary, note)

    def _get_group_users(self, xmlid):
        self.ensure_one()
        if xmlid == 'M02_P0205.group_gdh_rst_office_recruitment_mgr_bod':
            group = self._get_0205_bod_group()
            return group.user_ids if group else self.env['res.users']
        if xmlid == 'M02_P0205.group_gdh_rst_office_recruitment_mgr_abu':
            group = self._get_0205_abu_group()
            return group.user_ids if group else self.env['res.users']
        group = self.env.ref(xmlid, raise_if_not_found=False)
        return group.user_ids if group else self.env['res.users']

    @api.depends('job_id', 'department_id', 'company_id')
    def _compute_allowed_primary_interviewer_users(self):
        for rec in self:
            bod_users = rec._get_group_users('M02_P0205.group_gdh_rst_office_recruitment_mgr_bod')
            abu_users = rec._get_group_users('M02_P0205.group_gdh_rst_office_recruitment_mgr_abu')
            rec.x_psm_0205_allowed_primary_interviewer_l3_ids = bod_users
            rec.x_psm_0205_allowed_primary_interviewer_l4_ids = abu_users

    @api.onchange('job_id', 'department_id')
    def _onchange_primary_interviewer_round1(self):
        for rec in self:
            if not rec.x_psm_0205_primary_interviewer_l1_user_id:
                rec.x_psm_0205_primary_interviewer_l1_user_id = rec._find_applicant_manager_user()

    @api.onchange('company_id')
    def _onchange_primary_interviewer_round2(self):
        for rec in self:
            if rec.x_psm_0205_primary_interviewer_l2_user_id:
                continue
            ceo_employee = rec.company_id.x_psm_0205_ceo_id
            rec.x_psm_0205_primary_interviewer_l2_user_id = ceo_employee.user_id if ceo_employee and ceo_employee.user_id else False

    @api.constrains(
        'x_psm_0205_primary_interviewer_l1_user_id',
        'x_psm_0205_primary_interviewer_l2_user_id',
        'x_psm_0205_primary_interviewer_l3_user_id',
        'x_psm_0205_primary_interviewer_l4_user_id',
    )
    def _check_primary_interviewer_users(self):
        for rec in self:
            primary_fields = [
                ('Vòng 1', rec.x_psm_0205_primary_interviewer_l1_user_id),
                ('Vòng 2', rec.x_psm_0205_primary_interviewer_l2_user_id),
                ('Vòng 3', rec.x_psm_0205_primary_interviewer_l3_user_id),
                ('Vòng 4', rec.x_psm_0205_primary_interviewer_l4_user_id),
            ]
            for label, user in primary_fields:
                if user and user.share:
                    raise exceptions.ValidationError(
                        _("Người phỏng vấn chính của %(round)s phải là người dùng nội bộ.", round=label)
                    )
            bod_users = rec._get_group_users('M02_P0205.group_gdh_rst_office_recruitment_mgr_bod')
            abu_users = rec._get_group_users('M02_P0205.group_gdh_rst_office_recruitment_mgr_abu')
            if rec.x_psm_0205_primary_interviewer_l3_user_id and rec.x_psm_0205_primary_interviewer_l3_user_id not in bod_users:
                raise exceptions.ValidationError(
                    _("Người phỏng vấn chính Vòng 3 phải thuộc group BOD Recruitment.")
                )
            if rec.x_psm_0205_primary_interviewer_l4_user_id and rec.x_psm_0205_primary_interviewer_l4_user_id not in abu_users:
                raise exceptions.ValidationError(
                    _("Người phỏng vấn chính Vòng 4 phải thuộc group ABU Recruitment.")
                )

    def action_start_evaluation(self, round_num):
        """Open a new evaluation form for the selected round."""
        self.ensure_one()
        self._ensure_round_enabled(round_num)
        form_view = self.env.ref('M02_P0205.view_psm_applicant_evaluation_form', raise_if_not_found=False)
        return {
            'type': 'ir.actions.act_window',
            'name': _('Thêm đánh giá Vòng %(round)s', round=round_num),
            'res_model': 'x_psm_applicant_evaluation',
            'view_mode': 'form',
            'view_id': form_view.id if form_view else False,
            'target': 'new',
            'context': {
                'default_applicant_id': self.id,
                'default_interview_round': str(round_num),
                'default_interviewer_id': self.env.user.id,
                'form_view_initial_mode': 'edit',
            },
        }

    def action_start_eval_l1(self): return self.action_start_evaluation(1)
    def action_start_eval_l2(self): return self.action_start_evaluation(2)
    def action_start_eval_l3(self): return self.action_start_evaluation(3)
    def action_start_eval_l4(self): return self.action_start_evaluation(4)

    def _update_interview_round_outcome(self, interview_round):
        if not interview_round:
            return
        round_no = int(interview_round)
        max_round = self._get_max_interview_round()
        if round_no > max_round:
            return
        decision = self._get_primary_round_decision(round_no)
        recommendation = decision['recommendation']

        if not decision['primary_user'] or not decision['primary_eval']:
            return

        if recommendation == 'pass':
            if round_no >= max_round:
                self._schedule_offer_handoff_activity()
            elif round_no == 1:
                self._notify_ceo_round2()
            elif round_no == 2:
                self._notify_bod_round3()
            elif round_no == 3:
                self._notify_abu_round4()
            return

        if recommendation != 'fail':
            return

        reject_stage = self.env.ref('M02_P0205.stage_office_reject', raise_if_not_found=False)
        if reject_stage and self.stage_id != reject_stage.id:
            self.stage_id = reject_stage.id
            self.message_post(body=_(
                "Ứng viên đã bị loại sau vòng %(round)s theo kết luận của người phỏng vấn chính %(user)s.",
                round=interview_round,
                user=decision['primary_user'].display_name,
            ))

    def _notify_ceo_round2(self):
        self._ensure_round_enabled(2)
        ceo_employee = self.company_id.x_psm_0205_ceo_id
        if not ceo_employee or not ceo_employee.user_id:
            return
        summary = _("Lên lịch PV vòng 2")
        note = _("Ứng viên %(name)s đã đạt vòng 1. Vui lòng thiết lập lịch phỏng vấn vòng 2.") % {
            'name': self.partner_name or self.display_name
        }
        self._schedule_round_activity_for_users(ceo_employee.user_id, summary, note)

    def _notify_bod_round3(self):
        self._ensure_round_enabled(3)
        summary = _("Lên lịch PV vòng 3")
        note = _("Ứng viên %(name)s đã đạt vòng 2. Vui lòng tạo lịch và gửi lịch phỏng vấn vòng 3.") % {
            'name': self.partner_name or self.display_name
        }
        self._schedule_round_activity_for_group(
            'M02_P0205.group_gdh_rst_office_recruitment_mgr_bod',
            summary,
            note,
        )

    def _notify_abu_round4(self):
        self._ensure_round_enabled(4)
        summary = _("Lên lịch PV vòng 4")
        note = _("Ứng viên %(name)s đã đạt vòng 3. Vui lòng tạo lịch và gửi lịch phỏng vấn vòng 4.") % {
            'name': self.partner_name or self.display_name
        }
        self._schedule_round_activity_for_group(
            'M02_P0205.group_gdh_rst_office_recruitment_mgr_abu',
            summary,
            note,
        )

    def action_psm_0205_backfill_round_handoff_activity(self):
        for rec in self:
            rec._backfill_passed_round_handoff_activities()
        return True

    def _backfill_passed_round_handoff_activities(self):
        self.ensure_one()
        max_round = self._get_max_interview_round()
        for round_no in range(1, max_round + 1):
            decision = self._get_primary_round_decision(round_no)
            if decision['recommendation'] != 'pass' or not decision['primary_user'] or not decision['primary_eval']:
                continue
            if round_no >= max_round:
                self._schedule_offer_handoff_activity()
            elif round_no == 1:
                self._notify_ceo_round2()
            elif round_no == 2:
                self._notify_bod_round3()
            elif round_no == 3:
                self._notify_abu_round4()

    @api.depends(
        'x_psm_0205_primary_interviewer_l1_user_id',
        'x_psm_0205_primary_interviewer_l2_user_id',
        'x_psm_0205_primary_interviewer_l3_user_id',
        'x_psm_0205_primary_interviewer_l4_user_id',
        'x_psm_0205_evaluation_line_ids.interview_round',
        'x_psm_0205_evaluation_line_ids.interviewer_id',
        'x_psm_0205_evaluation_line_ids.recommendation',
    )
    def _compute_primary_interviewer_warnings(self):
        round_labels = {
            1: 'Vòng 1',
            2: 'Vòng 2',
            3: 'Vòng 3',
            4: 'Vòng 4',
        }
        for rec in self:
            for round_no in range(1, 5):
                primary_user = rec._get_primary_interviewer_user(round_no)
                warning_field = f'x_psm_0205_eval_round_{round_no}_primary_warning'
                pending_field = f'x_psm_0205_eval_round_{round_no}_primary_pending'
                warning_message = False
                pending = False
                if not rec._is_round_enabled(round_no):
                    setattr(rec, pending_field, False)
                    setattr(rec, warning_field, False)
                    continue
                if not primary_user:
                    pending = True
                    warning_message = _('%(round)s chưa có người phỏng vấn chính.', round=round_labels[round_no])
                else:
                    primary_eval = rec._get_primary_evaluation_for_round(round_no)
                    if not primary_eval:
                        pending = True
                        warning_message = _(
                            '%(round)s đang chờ đánh giá từ người phỏng vấn chính: %(user)s.',
                            round=round_labels[round_no],
                            user=primary_user.display_name,
                        )
                setattr(rec, pending_field, pending)
                setattr(rec, warning_field, warning_message)

    @api.depends(
        'x_psm_0205_recruitment_type',
        'stage_id',
        'x_psm_0205_interview_date_1',
        'x_psm_0205_interview_date_2',
        'x_psm_0205_interview_date_3',
        'x_psm_0205_interview_date_4',
        'x_psm_0205_evaluation_line_ids.interview_round',
        'x_psm_0205_primary_interviewer_l1_user_id',
        'x_psm_0205_primary_interviewer_l2_user_id',
        'x_psm_0205_primary_interviewer_l3_user_id',
        'x_psm_0205_primary_interviewer_l4_user_id',
    )
    def _compute_primary_interviewer_review(self):
        for rec in self:
            rec.x_psm_0205_needs_primary_interviewer_review = False
            rec.x_psm_0205_primary_interviewer_review_note = False
            if rec.x_psm_0205_recruitment_type != 'office':
                continue
            max_round = min(rec._get_max_reached_interview_round(), rec._get_max_interview_round())
            if not max_round:
                continue
            missing_rounds = []
            for round_no in range(1, max_round + 1):
                if not rec._get_primary_interviewer_user(round_no):
                    missing_rounds.append(str(round_no))
            if missing_rounds:
                rec.x_psm_0205_needs_primary_interviewer_review = True
                rec.x_psm_0205_primary_interviewer_review_note = _(
                    "Thiếu người phỏng vấn chính ở các vòng: %(rounds)s.",
                    rounds=', '.join(missing_rounds),
                )

    @api.depends(
        'x_psm_0205_primary_interviewer_l1_user_id',
        'x_psm_0205_primary_interviewer_l2_user_id',
        'x_psm_0205_primary_interviewer_l3_user_id',
        'x_psm_0205_primary_interviewer_l4_user_id',
        'x_psm_0205_evaluation_line_ids.recommendation',
        'x_psm_0205_evaluation_line_ids.interview_round',
        'x_psm_0205_evaluation_line_ids.interviewer_id',
        'x_psm_0205_evaluation_line_ids.average_score',
    )
    def _compute_eval_round_metrics(self):
        for rec in self:
            for idx in range(1, 5):
                decision = rec._get_primary_round_decision(idx)
                primary_eval = decision['primary_eval']
                recommendation = decision['recommendation']
                setattr(
                    rec,
                    f'x_psm_0205_eval_l{idx}_id',
                    primary_eval.id if primary_eval else False,
                )
                average_score = primary_eval.average_score if primary_eval else 0.0
                setattr(rec, f'x_psm_0205_eval_round_{idx}_score', average_score)
                rounded_score = False
                if primary_eval and average_score:
                    rounded_score = str(min(max(int(average_score + 0.5), 0), 5))
                setattr(rec, f'x_psm_0205_interview_result_{idx}', rounded_score)
                status = False
                rec_toggle = False
                if recommendation == 'pass':
                    status = 'pass'
                    rec_toggle = True
                elif recommendation == 'fail':
                    status = 'fail'
                setattr(rec, f'x_psm_0205_eval_round_{idx}_pass', status)
                setattr(rec, f'x_psm_0205_eval_round_{idx}_toggle', rec_toggle)

class HrApplicantEvaluation(models.Model):
    _name = 'x_psm_applicant_evaluation'
    _description = 'Đánh giá phỏng vấn'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'id desc'

    EVALUATION_LINE_TYPE_SELECTION = [
        ('score', 'Scored Line'),
        ('text', 'Text Line'),
    ]
    EVALUATION_SECTION_SELECTION = [
        ('functional_skills', 'Functional Skills'),
        ('best_leadership', 'Best Leadership'),
        ('character_traits', 'Character Traits'),
    ]
    EVALUATION_SCORE_SELECTION = [
        ('1', '1'),
        ('2', '2'),
        ('3', '3'),
        ('4', '4'),
        ('5', '5'),
    ]
    EVALUATION_TEMPLATE_LINES = [
        ('functional_skills', 'functional_skills', 'candidate_fit_1', 'Candidate Fit Point 1', 'score', True),
        ('functional_skills', 'functional_skills', 'candidate_fit_2', 'Candidate Fit Point 2', 'score', True),
        ('functional_skills', 'functional_skills', 'candidate_fit_3', 'Candidate Fit Point 3', 'score', True),
        ('functional_skills', 'functional_skills', 'technical_skill_1', 'Technical/Hard Skill #1', 'score', True),
        ('functional_skills', 'functional_skills', 'technical_skill_2', 'Technical/Hard Skill #2', 'score', True),
        ('functional_skills', 'functional_skills', 'role_specific_skill_1', 'Role-specific Skill #1', 'score', True),
        ('functional_skills', 'functional_skills', 'role_specific_skill_2', 'Role-specific Skill #2', 'score', True),
        ('functional_skills', 'functional_skills', 'soft_skill_1', 'Soft Skill #1', 'score', True),
        ('functional_skills', 'functional_skills', 'soft_skill_2', 'Soft Skill #2', 'score', True),
        ('best_leadership', 'best_leadership', 'background_values', 'Background & Values (Culture Fit)', 'score', True),
        ('best_leadership', 'best_leadership', 'building_block', 'Building Block', 'score', True),
        ('best_leadership', 'best_leadership', 'execution', 'Execution', 'score', True),
        ('best_leadership', 'best_leadership', 'strategy', 'Strategy', 'score', True),
        ('best_leadership', 'best_leadership', 'talent', 'Talent', 'score', True),
        ('best_leadership', 'best_leadership', 'brand_love', 'Brand Love', 'score', True),
        ('character_traits', 'character_traits', 'trait_1', 'Trait #1', 'score', True),
        ('character_traits', 'character_traits', 'trait_2', 'Trait #2', 'score', True),
        ('character_traits', 'character_traits', 'trait_3', 'Trait #3', 'score', True),
    ]

    applicant_id = fields.Many2one('hr.applicant', string='ứng viên', required=True, ondelete='cascade')
    interview_round = fields.Selection([
        ('1', 'Vòng 1 (Manager)'),
        ('2', 'Vòng 2 (CEO)'),
        ('3', 'Vòng 3 (BOD)'),
        ('4', 'Vòng 4 (ABU)')
    ], string='Vòng phỏng vấn', required=True, tracking=True,
        default=lambda self: self._context.get('default_interview_round') or False)
    interviewer_id = fields.Many2one('res.users', string='Người phỏng vấn', default=lambda self: self.env.user, tracking=True)
    primary_interviewer_user_id = fields.Many2one(
        'res.users',
        string='Người phỏng vấn chính của vòng',
        compute='_compute_primary_interviewer_meta',
    )
    is_primary_interviewer = fields.Boolean(
        string='Là người phỏng vấn chính',
        compute='_compute_primary_interviewer_meta',
    )
    date = fields.Date(string='Ngày đánh giá', default=fields.Date.today(), tracking=True)
    
    # Criteria - using Selection for easier scoring in UI
    attitude_score = fields.Selection([
        ('1', 'Rất kém'), ('2', 'Kém'), ('3', 'Trung bình'), ('4', 'Khá'), ('5', 'Tốt')
    ], string='Thái độ', default='3', tracking=True)
    
    skill_score = fields.Selection([
        ('1', 'Rất kém'), ('2', 'Kém'), ('3', 'Trung bình'), ('4', 'Khá'), ('5', 'Tốt')
    ], string='Kỹ năng chuyên môn', default='3', tracking=True)
    
    experience_score = fields.Selection([
        ('1', 'Rất kém'), ('2', 'Kém'), ('3', 'Trung bình'), ('4', 'Khá'), ('5', 'Tốt')
    ], string='Kinh nghiệm', default='3', tracking=True)
    
    culture_fit_score = fields.Selection([
        ('1', 'Rất kém'), ('2', 'Kém'), ('3', 'Trung bình'), ('4', 'Khá'), ('5', 'Tốt')
    ], string='Phù hợp văn hóa', default='3', tracking=True)
    
    strengths = fields.Text(string='Điểm mạnh', tracking=True)
    weaknesses = fields.Text(string='Điểm yếu', tracking=True)
    note = fields.Text(string='Ghi chú chung', tracking=True)
    evaluation_item_ids = fields.One2many(
        'x_psm_applicant_evaluation_line',
        'evaluation_id',
        string='Chi tiết đánh giá',
        copy=True,
    )
    scored_line_count = fields.Integer(
        string='Số tiêu chí đã chấm',
        compute='_compute_evaluation_summary',
        store=True,
    )
    weighted_total_score = fields.Float(
        string='Tổng điểm quy đổi',
        compute='_compute_evaluation_summary',
        store=True,
    )
    average_score = fields.Float(
        string='Điểm trung bình',
        compute='_compute_evaluation_summary',
        store=True,
        digits=(16, 2),
    )
    final_result = fields.Selection(
        [('pass', 'Pass'), ('reject', 'Reject')],
        string='Kết quả cuối',
        compute='_compute_evaluation_summary',
        store=True,
    )
    onboard_time = fields.Char(string='Onboard Time', tracking=True)
    final_comment = fields.Text(string='Nhận xét cuối', tracking=True)
    
    recommendation = fields.Selection([
        ('pass', 'Đạt - Tiếp tục vòng sau'),
        ('fail', 'Không đạt - Loại'),
    ], string='Kết luận', required=True, default='pass', tracking=True)

    @api.depends(
        'evaluation_item_ids.line_type',
        'evaluation_item_ids.is_scored',
        'evaluation_item_ids.score_value',
    )
    def _compute_evaluation_summary(self):
        for rec in self:
            scored_lines = rec.evaluation_item_ids.filtered(
                lambda line: line.line_type == 'score' and line.is_scored and line.score_value
            )
            rec.scored_line_count = len(scored_lines)
            rec.weighted_total_score = sum(int(line.score_value) for line in scored_lines)
            rec.average_score = (
                rec.weighted_total_score / rec.scored_line_count if rec.scored_line_count else 0.0
            )
            if not rec.scored_line_count:
                rec.final_result = False
            else:
                rec.final_result = 'pass' if rec.average_score >= 3 else 'reject'

    def _get_recommendation_from_final_result(self):
        self.ensure_one()
        return {
            'pass': 'pass',
            'reject': 'fail',
        }.get(self.final_result)

    def _sync_recommendation_from_final_result(self):
        if self.env.context.get('skip_eval_recommendation_sync'):
            return
        updates = self.filtered(
            lambda rec: rec.final_result and rec.recommendation != rec._get_recommendation_from_final_result()
        )
        for rec in updates:
            rec.with_context(skip_eval_recommendation_sync=True).write({
                'recommendation': rec._get_recommendation_from_final_result(),
            })

    def _get_default_evaluation_line_vals(self):
        self.ensure_one()
        line_vals = []
        for sequence, (_section_key, section_code, item_code, item_label, line_type, is_scored) in enumerate(
            self.EVALUATION_TEMPLATE_LINES, start=1
        ):
            vals = {
                'sequence': sequence,
                'section_code': section_code,
                'item_code': item_code,
                'item_label': item_label,
                'line_type': line_type,
                'is_scored': is_scored,
            }
            if line_type == 'score':
                vals['score_value'] = False
            line_vals.append(vals)
        return line_vals

    def _get_evaluation_template_map(self):
        self.ensure_one()
        template_map = {}
        for sequence, (_section_key, section_code, item_code, item_label, line_type, is_scored) in enumerate(
            self.EVALUATION_TEMPLATE_LINES, start=1
        ):
            template_map[item_code] = {
                'sequence': sequence,
                'section_code': section_code,
                'item_label': item_label,
                'line_type': line_type,
                'is_scored': is_scored,
            }
        return template_map

    def _ensure_default_evaluation_lines(self):
        for rec in self:
            if rec.evaluation_item_ids:
                continue
            rec.with_context(skip_eval_line_sync=True).write({
                'evaluation_item_ids': [(0, 0, vals) for vals in rec._get_default_evaluation_line_vals()],
            })

    def _sync_evaluation_line_templates(self):
        for rec in self:
            if not rec.evaluation_item_ids:
                continue
            template_map = rec._get_evaluation_template_map()
            for line in rec.evaluation_item_ids.filtered(lambda item: item.item_code in template_map):
                target_vals = template_map[line.item_code]
                updates = {}
                for field_name, value in target_vals.items():
                    if line[field_name] != value:
                        updates[field_name] = value
                if updates:
                    line.with_context(skip_eval_line_sync=True).write(updates)
        self._after_eval_change()

    def _build_legacy_final_comment(self):
        self.ensure_one()
        comment_parts = []
        if self.strengths:
            comment_parts.append(_("Diem manh:\n%s") % self.strengths.strip())
        if self.weaknesses:
            comment_parts.append(_("Diem yeu:\n%s") % self.weaknesses.strip())
        if self.note:
            comment_parts.append(_("Ghi chu chung:\n%s") % self.note.strip())
        return "\n\n".join(comment_parts).strip()

    def _migrate_legacy_scores_to_lines(self):
        legacy_score_map = {
            'technical_skill_1': 'skill_score',
            'role_specific_skill_1': 'experience_score',
            'soft_skill_1': 'attitude_score',
            'background_values': 'culture_fit_score',
        }
        for rec in self.filtered(lambda evaluation: not evaluation.evaluation_item_ids):
            rec._ensure_default_evaluation_lines()
            lines_by_code = {line.item_code: line for line in rec.evaluation_item_ids}
            line_updates = []
            for item_code, field_name in legacy_score_map.items():
                score_value = getattr(rec, field_name)
                target_line = lines_by_code.get(item_code)
                if target_line and score_value:
                    line_updates.append((target_line, score_value))
            for line, score_value in line_updates:
                line.with_context(skip_eval_line_sync=True).write({'score_value': score_value})
            if not rec.final_comment:
                legacy_comment = rec._build_legacy_final_comment()
                if legacy_comment:
                    rec.with_context(skip_eval_recommendation_sync=True).write({
                        'final_comment': legacy_comment,
                    })
        self._after_eval_change()

    @api.model
    def _register_hook(self):
        result = super()._register_hook()
        self.env.cr.execute("SELECT to_regclass('public.hr_applicant_evaluation_line')")
        if not self.env.cr.fetchone()[0]:
            return result
        self.env.cr.execute("""
            SELECT evaluation.id
            FROM hr_applicant_evaluation AS evaluation
            LEFT JOIN hr_applicant_evaluation_line AS line
                ON line.evaluation_id = evaluation.id
            GROUP BY evaluation.id
            HAVING COUNT(line.id) = 0
        """)
        legacy_ids = [row[0] for row in self.env.cr.fetchall()]
        if legacy_ids:
            _logger.info(
                "Migrating %s legacy interview evaluations to line-based structure.",
                len(legacy_ids),
            )
            self.browse(legacy_ids)._migrate_legacy_scores_to_lines()
        existing_evaluations = self.search([])
        if existing_evaluations:
            existing_evaluations._sync_evaluation_line_templates()
        return result

    @api.model
    def default_get(self, fields):
        res = super().default_get(fields)
        ctx = self.env.context
        if 'interviewer_id' in fields and not res.get('interviewer_id'):
            interviewer = ctx.get('default_interviewer_id')
            if interviewer:
                res['interviewer_id'] = interviewer
        if 'evaluation_item_ids' in fields and not res.get('evaluation_item_ids'):
            draft_evaluation = self.new(res)
            res['evaluation_item_ids'] = [
                (0, 0, vals) for vals in draft_evaluation._get_default_evaluation_line_vals()
            ]
        return res

    @api.depends(
        'applicant_id.x_psm_0205_primary_interviewer_l1_user_id',
        'applicant_id.x_psm_0205_primary_interviewer_l2_user_id',
        'applicant_id.x_psm_0205_primary_interviewer_l3_user_id',
        'applicant_id.x_psm_0205_primary_interviewer_l4_user_id',
        'interviewer_id',
        'interview_round',
    )
    def _compute_primary_interviewer_meta(self):
        for rec in self:
            primary_user = False
            if rec.applicant_id and rec.interview_round:
                primary_user = rec.applicant_id._get_primary_interviewer_user(rec.interview_round)
            rec.primary_interviewer_user_id = primary_user
            rec.is_primary_interviewer = bool(primary_user and rec.interviewer_id == primary_user)

    @api.constrains('applicant_id', 'interview_round', 'interviewer_id')
    def _check_single_primary_evaluation_per_round(self):
        for rec in self:
            if not rec.applicant_id or not rec.interview_round or not rec.interviewer_id:
                continue
            primary_user = rec.primary_interviewer_user_id or rec.applicant_id._get_primary_interviewer_user(rec.interview_round)
            if not primary_user or rec.interviewer_id != primary_user:
                continue
            duplicate_count = self.search_count([
                ('applicant_id', '=', rec.applicant_id.id),
                ('interview_round', '=', rec.interview_round),
                ('interviewer_id', '=', rec.interviewer_id.id),
                ('id', '!=', rec.id),
            ])
            if duplicate_count:
                raise exceptions.ValidationError(
                    _("Mỗi vòng chỉ được có tối đa một bản đánh giá của người phỏng vấn chính.")
                )

    @api.model_create_multi
    def create(self, vals_list):
        ctx = self.env.context
        default_round = ctx.get('default_interview_round')
        default_interviewer = ctx.get('default_interviewer_id')
        stage_refs = [
            ('M02_P0205.stage_office_interview_1', '1'),
            ('M02_P0205.stage_office_interview_2', '2'),
            ('M02_P0205.stage_office_interview_3', '3'),
            ('M02_P0205.stage_office_interview_4', '4'),
        ]
        stage_map = {}
        for ref_name, round_value in stage_refs:
            try:
                stage_id = self.env.ref(ref_name, raise_if_not_found=True).id
            except ValueError:
                continue
            stage_map[stage_id] = round_value
        for vals in vals_list:
            interview_round = vals.get('interview_round') or default_round
            if not interview_round:
                applicant = vals.get('applicant_id') and self.env['hr.applicant'].browse(vals['applicant_id'])
                if applicant:
                    interview_round = stage_map.get(applicant.stage_id.id)
                    if not interview_round:
                        interview_round = applicant.x_psm_0205_next_interview_round or '1'
            if interview_round:
                vals['interview_round'] = interview_round
            if not vals.get('interviewer_id') and default_interviewer:
                vals['interviewer_id'] = default_interviewer
        records = super(HrApplicantEvaluation, self).create(vals_list)
        records._ensure_default_evaluation_lines()
        records._sync_evaluation_line_templates()
        records._after_eval_change()
        return records

    def write(self, vals):
        res = super(HrApplicantEvaluation, self).write(vals)
        self._after_eval_change()
        return res

    def unlink(self):
        rounds_by_applicant = {}
        for rec in self:
            if not rec.applicant_id:
                continue
            rounds_by_applicant.setdefault(rec.applicant_id, set()).add(rec.interview_round)
        res = super(HrApplicantEvaluation, self).unlink()
        for applicant, rounds in rounds_by_applicant.items():
            for interview_round in rounds:
                applicant._update_interview_round_outcome(interview_round)
        return res

    def _after_eval_change(self):
        self._sync_recommendation_from_final_result()
        rounds_by_applicant = {}
        for rec in self:
            if not rec.applicant_id:
                continue
            rounds_by_applicant.setdefault(rec.applicant_id, set()).add(rec.interview_round)
        for applicant, rounds in rounds_by_applicant.items():
            for interview_round in rounds:
                applicant._update_interview_round_outcome(interview_round)
            applicant._backfill_passed_round_handoff_activities()

    def name_get(self):
        result = []
        for rec in self:
            name = f"Đánh giá {rec.applicant_id.partner_name} - Vòng {rec.interview_round}"
            result.append((rec.id, name))
        return result

    def action_view_form(self):
        self.ensure_one()
        form_view = self.env.ref('M02_P0205.view_psm_applicant_evaluation_form', raise_if_not_found=False)
        return {
            'type': 'ir.actions.act_window',
            'name': 'Đánh giá phòng vấn',
            'res_model': 'x_psm_applicant_evaluation',
            'res_id': self.id,
            'view_mode': 'form',
            'view_id': form_view.id if form_view else False,
            'target': 'new',
        }


class HrApplicantEvaluationLine(models.Model):
    _name = 'x_psm_applicant_evaluation_line'
    _description = 'Chi tiết đánh giá phỏng vấn'
    _order = 'sequence, id'

    evaluation_id = fields.Many2one(
        'x_psm_applicant_evaluation',
        string='Phiếu đánh giá',
        required=True,
        ondelete='cascade',
    )
    sequence = fields.Integer(default=10)
    section_code = fields.Selection(
        HrApplicantEvaluation.EVALUATION_SECTION_SELECTION,
        string='Nhóm tiêu chí',
        required=True,
    )
    section_label = fields.Char(string='Nhóm', compute='_compute_section_label')
    item_code = fields.Char(string='Mã tiêu chí', required=True)
    item_label = fields.Char(string='Tiêu chí', required=True)
    line_type = fields.Selection(
        HrApplicantEvaluation.EVALUATION_LINE_TYPE_SELECTION,
        string='Loại dòng',
        required=True,
        default='score',
    )
    score_value = fields.Selection(
        HrApplicantEvaluation.EVALUATION_SCORE_SELECTION,
        string='Điểm',
    )
    score_1 = fields.Boolean(string='1', compute='_compute_score_flags', inverse='_inverse_score_1')
    score_2 = fields.Boolean(string='2', compute='_compute_score_flags', inverse='_inverse_score_2')
    score_3 = fields.Boolean(string='3', compute='_compute_score_flags', inverse='_inverse_score_3')
    score_4 = fields.Boolean(string='4', compute='_compute_score_flags', inverse='_inverse_score_4')
    score_5 = fields.Boolean(string='5', compute='_compute_score_flags', inverse='_inverse_score_5')
    note = fields.Char(string='Ghi chú')
    is_scored = fields.Boolean(string='Tính điểm', default=True)

    @api.onchange('line_type')
    def _onchange_line_type(self):
        for rec in self:
            if rec.line_type != 'score':
                rec.score_value = False
            elif not rec.score_value:
                rec.score_value = False

    @api.depends('score_value', 'line_type')
    def _compute_score_flags(self):
        for rec in self:
            for score in range(1, 6):
                setattr(
                    rec,
                    f'score_{score}',
                    rec.line_type == 'score' and rec.score_value == str(score)
                )

    @api.onchange('score_1', 'score_2', 'score_3', 'score_4', 'score_5')
    def _onchange_score_flags(self):
        for rec in self:
            if rec.line_type != 'score':
                rec.score_value = False
                continue
            checked_scores = [
                str(score)
                for score in range(1, 6)
                if rec[f'score_{score}']
            ]
            rec.score_value = checked_scores[-1] if checked_scores else False

    @api.depends('section_code')
    def _compute_section_label(self):
        selection_map = dict(HrApplicantEvaluation.EVALUATION_SECTION_SELECTION)
        for rec in self:
            rec.section_label = selection_map.get(rec.section_code, rec.section_code or '')

    def _set_score_flag_value(self, target_score):
        for rec in self:
            target_field = f'score_{target_score}'
            target_value = rec[target_field]
            if rec.line_type != 'score':
                rec.score_value = False
            elif target_value:
                rec.score_value = str(target_score)
            elif rec.score_value == str(target_score):
                rec.score_value = False

    def _inverse_score_1(self):
        self._set_score_flag_value(1)

    def _inverse_score_2(self):
        self._set_score_flag_value(2)

    def _inverse_score_3(self):
        self._set_score_flag_value(3)

    def _inverse_score_4(self):
        self._set_score_flag_value(4)

    def _inverse_score_5(self):
        self._set_score_flag_value(5)

    @staticmethod
    def _extract_score_value_from_checkbox_vals(vals):
        score_keys = [f'score_{score}' for score in range(1, 6)]
        checked_scores = [str(score) for score in range(1, 6) if vals.get(f'score_{score}') is True]
        unchecked_keys = [key for key in score_keys if key in vals]
        if checked_scores:
            return checked_scores[-1]
        if unchecked_keys and all(vals.get(key) is False for key in unchecked_keys):
            return False
        return None

    @classmethod
    def _get_template_defaults_by_item_code(cls, item_code):
        if not item_code:
            return {}
        for sequence, (_section_key, section_code, template_item_code, item_label, line_type, is_scored) in enumerate(
            HrApplicantEvaluation.EVALUATION_TEMPLATE_LINES, start=1
        ):
            if template_item_code == item_code:
                return {
                    'sequence': sequence,
                    'section_code': section_code,
                    'item_label': item_label,
                    'line_type': line_type,
                    'is_scored': is_scored,
                }
        return {}

    @classmethod
    def _get_template_defaults_by_item_label(cls, item_label):
        if not item_label:
            return {}
        for sequence, (_section_key, section_code, item_code, template_item_label, line_type, is_scored) in enumerate(
            HrApplicantEvaluation.EVALUATION_TEMPLATE_LINES, start=1
        ):
            if template_item_label == item_label:
                return {
                    'sequence': sequence,
                    'section_code': section_code,
                    'item_code': item_code,
                    'item_label': template_item_label,
                    'line_type': line_type,
                    'is_scored': is_scored,
                }
        return {}

    @classmethod
    def _normalize_score_checkbox_vals(cls, vals, fallback_item_code=None):
        template_defaults = cls._get_template_defaults_by_item_code(vals.get('item_code') or fallback_item_code)
        if not template_defaults:
            template_defaults = cls._get_template_defaults_by_item_label(vals.get('item_label'))
        for field_name, value in template_defaults.items():
            vals.setdefault(field_name, value)
        score_value = cls._extract_score_value_from_checkbox_vals(vals)
        if score_value is not None:
            vals['score_value'] = score_value
        if vals.get('line_type') and vals['line_type'] != 'score':
            vals['score_value'] = False
        return vals

    @api.constrains('line_type', 'score_value')
    def _check_score_value_for_line_type(self):
        for rec in self:
            if rec.line_type != 'score' and rec.score_value:
                raise exceptions.ValidationError(
                    _("Dòng text không được nhập điểm.")
                )

    @api.constrains('score_value')
    def _check_single_score_value(self):
        for rec in self:
            if rec.line_type == 'score' and rec.score_value not in {False, '1', '2', '3', '4', '5'}:
                raise exceptions.ValidationError(
                    _("Mỗi tiêu chí chỉ được chọn duy nhất một mức điểm.")
                )

    @api.model_create_multi
    def create(self, vals_list):
        normalized_vals_list = [self._normalize_score_checkbox_vals(dict(vals)) for vals in vals_list]
        records = super().create(normalized_vals_list)
        if not self.env.context.get('skip_eval_line_sync'):
            records.mapped('evaluation_id')._after_eval_change()
        return records

    def write(self, vals):
        results = []
        for rec in self:
            normalized_vals = self._normalize_score_checkbox_vals(dict(vals), fallback_item_code=rec.item_code)
            results.append(super(HrApplicantEvaluationLine, rec).write(normalized_vals))
        res = all(results) if results else True
        if not self.env.context.get('skip_eval_line_sync'):
            self.mapped('evaluation_id')._after_eval_change()
        return res

    def unlink(self):
        evaluations = self.mapped('evaluation_id')
        res = super().unlink()
        if not self.env.context.get('skip_eval_line_sync'):
            evaluations._after_eval_change()
        return res
