# -*- coding: utf-8 -*-
from odoo import http, fields, _
from odoo.http import request
import logging
import base64

_logger = logging.getLogger(__name__)

class WebsiteRecruitmentCustom(http.Controller):

    @http.route('/jobs/apply/<model("hr.job"):job>', type='http', auth='public', website=True)
    def website_job_apply_custom(self, job, **kwargs):
        """Render 1 trang duy nhất gồm Form thông tin + Câu hỏi Survey."""
        if not job or not job.active:
            return request.render("website_hr_recruitment.index")

        # Lấy bản ghi job đã sudo để đọc các cấu hình bị giới hạn quyền truy cập
        job_sudo = job.sudo()
        # Định nghĩa thứ tự ưu tiên của các phần (section)
        section_order = {
            'basic_info': 1,
            'other_info': 2,
            'supplementary_question': 3,
            'internal_question': 4
        }
        
        # Lấy cấu hình biểu mẫu ứng tuyển bằng sudo và sắp xếp theo nhóm, sau đó phân loại theo sequence
        form_fields = job_sudo.application_field_ids.filtered('is_active').sorted(
            key=lambda f: (section_order.get(f.section, 99), f.sequence)
        )

        # Lấy survey template đã cấu hình cho Job bằng sudo
        survey = job_sudo.generated_survey_template_id or job_sudo.survey_id
        questions = survey.sudo().question_ids if survey else []

        # Tìm interview.schedule confirmed: chỉ cho store jobs
        schedule = False
        if job_sudo.recruitment_type == 'store':
            domain = [('state', '=', 'confirmed'), ('week_end_date', '>=', fields.Date.today())]
            if job_sudo.department_id:
                domain.append(('department_id', '=', job_sudo.department_id.id))
            schedule = request.env['interview.schedule'].sudo().search(domain, order='week_start_date asc', limit=1)

        return request.render("M02_P0204_00.website_job_apply_custom", {
            'job': job,
            'form_fields': form_fields,
            'survey': survey,
            'questions': questions,
            'schedule': schedule,
            'error': {},
            'default': {},
        })

    @http.route('/jobs/apply/submit', type='http', auth='public', website=True, methods=['POST'], csrf=True)
    def website_job_apply_submit(self, **post):
        """Xử lý nộp hồ sơ: Tạo Applicant + Lưu kết quả Survey."""
        job_id = int(post.get('job_id', 0))
        job = request.env['hr.job'].sudo().browse(job_id)
        if not job.exists():
            return request.redirect('/jobs')

        import re
        error = {}
        default = {k: v for k, v in post.items() if isinstance(v, str)}

        if 'x_id_number' in post:
            x_id_number = post.get('x_id_number', '').strip()
            if not re.match(r'^\d{12}$', x_id_number):
                error['x_id_number'] = "Số CMT/CCCD/Hộ chiếu phải gồm đúng 12 chữ số."

        if error:
            job_sudo = job.sudo()
            section_order = {
                'basic_info': 1,
                'other_info': 2,
                'supplementary_question': 3,
                'internal_question': 4
            }
            form_fields = job_sudo.application_field_ids.filtered('is_active').sorted(
                key=lambda f: (section_order.get(f.section, 99), f.sequence)
            )
            survey = job_sudo.generated_survey_template_id or job_sudo.survey_id
            questions = survey.sudo().question_ids if survey else []
            schedule = False
            if job_sudo.recruitment_type == 'store':
                domain = [('state', '=', 'confirmed'), ('week_end_date', '>=', fields.Date.today())]
                if job_sudo.department_id:
                    domain.append(('department_id', '=', job_sudo.department_id.id))
                schedule = request.env['interview.schedule'].sudo().search(domain, order='week_start_date asc', limit=1)

            return request.render("M02_P0204_00.website_job_apply_custom", {
                'job': job,
                'form_fields': form_fields,
                'survey': survey,
                'questions': questions,
                'schedule': schedule,
                'error': error,
                'default': default,
            })

        # 1. Thu thập dữ liệu theo cấu hình biểu mẫu
        form_fields = job.application_field_ids.filtered('is_active')
        
        applicant_vals = {
            'job_id': job.id,
            'application_source': 'web',
        }
        # Only auto-approve documents for store jobs
        if job.recruitment_type == 'store':
            applicant_vals['document_approval_status'] = 'approved'
        properties_vals = {}
        attachments_to_create = []

        for field in form_fields:
            val = post.get(field.field_name)
            
            # Xử lý File
            if field.field_type == 'file':
                if val and hasattr(val, 'read'):
                    attachments_to_create.append((field.field_name, val))
                continue
            
            # Xử lý Checkbox (không có trong post nghĩa là False)
            if field.field_type == 'checkbox':
                val = True if val else False
            
            if field.is_default:
                # Gán vào field model nếu tồn tại
                if field.field_name in request.env['hr.applicant']._fields:
                    applicant_vals[field.field_name] = val
                    _logger.debug(f"Setting default field {field.field_name} = {val}")
            else:
                # Gán vào Odoo Properties
                converted_val = val
                if field.field_type == 'number':
                    try: converted_val = int(val)
                    except: converted_val = 0
                elif field.field_type == 'checkbox':
                    converted_val = bool(val)
                
                properties_vals[field.field_name] = converted_val
                _logger.debug(f"Setting property {field.field_name} = {converted_val}")

        if properties_vals:
            applicant_vals['applicant_properties'] = properties_vals

        # Tạo Applicant
        applicant = request.env['hr.applicant'].sudo().create(applicant_vals)

        # Xử lý lưu File Upload
        for field_name, file in attachments_to_create:
            try:
                # Tìm lại file pointer nếu cần
                if hasattr(file, 'seek'):
                    file.seek(0)
                file_data = file.read()
                if field_name == 'x_portrait_image':
                    applicant.sudo().write({'x_portrait_image': base64.b64encode(file_data)})
                else:
                    request.env['ir.attachment'].sudo().create({
                        'name': file.filename if hasattr(file, 'filename') else 'attachment',
                        'res_model': 'hr.applicant',
                        'res_id': applicant.id,
                        'type': 'binary',
                        'datas': base64.b64encode(file_data),
                    })
            except Exception as e:
                _logger.error(f"Error saving attachment {field_name}: {e}")

        # 2. Đánh giá "Phải đúng" (Answer Must Match) & Lưu Snapshot Lịch sử
        failed_must_match_fields = []
        failed_auto_reject_fields = []
        answer_lines_vals = []
        
        for field in form_fields:
            if field.field_type == 'file':
                continue # Bỏ qua file upload ở v1

            # Lấy giá trị thô từ post
            raw_val = post.get(field.field_name)
            actual_val = (raw_val or '').strip().lower() if raw_val else ''
            
            # Chuẩn hoá hiển thị cho Applicant Answer
            applicant_answer_text = raw_val or ''
            if field.field_type == 'checkbox':
                actual_val = 'yes' if raw_val else 'no'
                applicant_answer_text = 'Có' if raw_val else 'Không'
            elif field.field_type in ('select', 'radio') and actual_val:
                opt = field.option_ids.filtered(lambda o: o.value.lower() == actual_val)
                if opt:
                    applicant_answer_text = opt[0].name

            # Chuẩn hoá hiển thị cho Expected Answer
            expected_val = (field.expected_answer or '').strip().lower()
            expected_answer_text = ''
            if field.is_answer_must_match:
                if field.field_type == 'checkbox':
                    expected_answer_text = 'Có' if expected_val == 'yes' else 'Không'
                elif field.field_type in ('select', 'radio') and expected_val:
                    opt = field.option_ids.filtered(lambda o: o.value.lower() == expected_val)
                    if opt:
                        expected_answer_text = opt[0].name
                else:
                    expected_answer_text = field.expected_answer or ''

            # Kiểm tra tính đúng đắn cho câu Must Match
            is_correct = True
            if field.is_answer_must_match and expected_val:
                if actual_val != expected_val:
                    is_correct = False
                    failed_must_match_fields.append(field.field_label)
                    if field.auto_reject_if_wrong:
                        failed_auto_reject_fields.append(field.field_label)

            # Chuẩn bị data cho snapshot line
            answer_lines_vals.append({
                'applicant_id': applicant.id,
                'master_field_id': field.master_field_id.id if field.master_field_id else False,
                'section': field.section,
                'sequence': field.sequence,
                'field_label': field.field_label,
                'field_type': field.field_type,
                'applicant_answer_text': applicant_answer_text,
                'expected_answer_text': expected_answer_text,
                'is_answer_must_match': field.is_answer_must_match,
                'is_answer_correct': is_correct,
            })

        # Tạo hàng loạt snapshot lines
        if answer_lines_vals:
            request.env['hr.applicant.application.answer.line'].sudo().create(answer_lines_vals)

        # Xử lý kết quả logic
        if failed_auto_reject_fields:
            auto_reject_list = ', '.join(failed_auto_reject_fields)
            note_html = (
                f"<p><b>Ứng viên bị loại ngay do trả lời sai câu có cờ 'Loại khi sai':</b></p>"
                f"<ul>{''.join(f'<li>{f}</li>' for f in failed_auto_reject_fields)}</ul>"
            )

            applicant.sudo().write({
                'failed_mandatory_questions': note_html,
                'survey_under_review_date': False,
            })

            reject_stage = request.env['hr.applicant']._get_target_pipeline_stage(
                'Reject',
                recruitment_type=job.recruitment_type,
                position_level=job.position_level,
            )
            if reject_stage:
                applicant.sudo().write({'stage_id': reject_stage.id})
                _logger.info(
                    "[ANSWER_MATCH] Applicant %s → Reject (immediate auto-reject: %s)",
                    applicant.partner_name, auto_reject_list,
                )
            else:
                _logger.warning(
                    "[ANSWER_MATCH] Reject stage not found for applicant %s (failed auto-reject: %s)",
                    applicant.partner_name, auto_reject_list,
                )

            try:
                applicant.sudo().message_post(
                    body=note_html,
                    message_type='comment',
                    subtype_xmlid='mail.mt_note',
                )
            except Exception as e:
                _logger.error("[ANSWER_MATCH] Failed to post chatter note: %s", e)
        elif failed_must_match_fields:
            failed_list = ', '.join(failed_must_match_fields)
            note_html = (
                f"<p><b>⚠ Ứng viên trả lời sai câu phải đúng:</b></p>"
                f"<ul>{''.join(f'<li>{f}</li>' for f in failed_must_match_fields)}</ul>"
            )
            # Ghi lại danh sách lỗi vào database (fallback UI)
            applicant.sudo().write({
                'failed_mandatory_questions': note_html,
            })
            
            if job.recruitment_type == 'store':
                # Store: ép vào Under Review
                review_stage = request.env['hr.applicant']._get_target_pipeline_stage(
                    'Under Review',
                    recruitment_type='store',
                    position_level=job.position_level
                )
                
                if review_stage:
                    applicant.sudo().write({
                        'stage_id': review_stage.id,
                        'survey_under_review_date': fields.Datetime.now(),
                    })
                    _logger.info(
                        "[ANSWER_MATCH] Store applicant %s → Under Review (failed: %s)",
                        applicant.partner_name, failed_list,
                    )
            else:
                # Office: không đổi stage, chỉ log
                _logger.info(
                    "[ANSWER_MATCH] Office applicant %s failed answer match (no stage change): %s",
                    applicant.partner_name, failed_list,
                )
            
            # Ghi chatter note cho cả store và office
            try:
                applicant.sudo().message_post(
                    body=note_html,
                    message_type='comment',
                    subtype_xmlid='mail.mt_note',
                )
            except Exception as e:
                _logger.error("[ANSWER_MATCH] Failed to post chatter note: %s", e)
        else:
            # Nếu pass hoàn toàn thì xoá ghi nhận lỗi
            applicant.sudo().write({
                'failed_mandatory_questions': False,
                'survey_under_review_date': False,
            })
            
            # Quyết định stage cho Store applicant (Pass form)
            if job.recruitment_type == 'store':
                target_name = 'Interview & OJE' if job.position_level == 'staff' else 'Interview'
                pass_stage = request.env['hr.applicant']._get_target_pipeline_stage(
                    target_name, 
                    recruitment_type='store', 
                    position_level=job.position_level
                )
                    
                if pass_stage:
                    applicant.sudo().write({'stage_id': pass_stage.id})
                    _logger.info(
                        "[ANSWER_MATCH] Store applicant %s → %s (passed mandatory matching)",
                        applicant.partner_name, target_name,
                    )

        # 3. (Bypass) Xử lý Survey Answers: Luồng khảo sát pre-interview cũ đã bị thay thế bằng master form.
        #    Tạm thời vô hiệu hoá phân đoạn tạo survey.user_input để không còn side effect.
        
        # 4. Cập nhật Interview Slot đã chọn từ UI vào applicant để hệ thống gọi auto-book
        if job.recruitment_type == 'store':
            interview_slot = post.get('interview_slot') # '1', '2', '3'
            schedule_id = post.get('schedule_id')
            if interview_slot and schedule_id:
                schedule = request.env['interview.schedule'].sudo().browse(int(schedule_id))
                if schedule.exists():
                    applicant.sudo().write({
                        'interview_booked_slot': interview_slot,
                        'interview_schedule_id': schedule.id,
                    })
                    # Gọi auto-book của FCFS để tạo event ngay 
                    if applicant.stage_id and 'interview' in (applicant.stage_id.name or '').lower():
                        try:
                            applicant.action_auto_book_interview_from_survey()
                        except Exception as e:
                            _logger.error("[AUTO_BOOK] Lỗi không thể tạo calendar event tự động: %s", getattr(e, "name", str(e)))

        # Gửi thông báo BUS PUSH real-time cho các ứng viên khác sau khi mọi thứ hoàn thành
            if job.recruitment_type == 'store':
                interview_slot = post.get('interview_slot')
                schedule_id = post.get('schedule_id')
                if interview_slot and schedule_id:
                    schedule = request.env['interview.schedule'].sudo().browse(int(schedule_id))
                    if schedule.exists():
                        request.env['bus.bus']._sendone(
                            f'interview_slots_{schedule.id}',
                            'slot_update',
                            schedule.get_slot_availability(),
                        )

        # 5. Gửi thông báo Activity cho Recruiter (Nội bộ)
        job_sudo = job.sudo()
        target_user = applicant.sudo().user_id or job_sudo.user_id
        
        # Fallback 1: Trưởng phòng ban của vị trí
        if not target_user and job_sudo.department_id.manager_id.user_id:
            target_user = job_sudo.department_id.manager_id.user_id
            
        # Fallback 2: Admin hệ thống (để đảm bảo không bị mất thông báo)
        if not target_user:
            target_user = request.env.ref('base.user_admin', raise_if_not_found=False)

        if target_user:
            try:
                note = f"""
                    <p><b>Ứng viên mới:</b> {applicant.partner_name or applicant.name or 'Chưa rõ'}</p>
                    <p><b>Vị trí:</b> {job.name}</p>
                    <p><b>Nguồn:</b> Website Portal</p>
                    <p>Vui lòng kiểm tra hồ sơ và xử lý bước tiếp theo.</p>
                """
                applicant.sudo().activity_schedule(
                    'mail.mail_activity_data_todo',
                    user_id=target_user.id,
                    summary=f'Hồ sơ ứng tuyển mới: {applicant.partner_name or applicant.name or "Ứng viên"}',
                    note=note,
                    date_deadline=fields.Date.context_today(applicant)
                )
            except Exception as e:
                _logger.error(f"Failed to create new applicant activity for applicant {applicant.id}: {e}")

        return request.render("M02_P0204_00.website_apply_thankyou", {
            'job': job,
            'applicant': applicant,
        })
