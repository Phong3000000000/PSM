# Danh Sách Field Module 0205

Tài liệu này liệt kê các field được dùng trong module `M02_P0205_00`, chia thành 2 nhóm:

- Field khai báo trên các model kế thừa từ Odoo
- Field khai báo trên các model được tạo mới hoàn toàn trong module `0205`

## 1. Field dùng trên model kế thừa từ Odoo

### `calendar.event`

- File: `models/calendar.py`
- Các field bổ sung:
  - `round2_notification_sent`
  - `round3_notification_sent`
  - `round4_notification_sent`
  - `interview_round`

### `hr.applicant`

- File: `models/hr_applicant.py`
- File: `models/recruitment_plan.py`
- Các field bổ sung:
  - `stage_id`
  - `priority`
  - `recruitment_type`
  - `document_approval_status`
  - `passport_photo`
  - `passport_photo_filename`
  - `id_card_front`
  - `id_card_front_filename`
  - `id_card_back`
  - `id_card_back_filename`
  - `household_registration`
  - `household_registration_filename`
  - `judicial_record`
  - `judicial_record_filename`
  - `professional_certificate`
  - `professional_certificate_filename`
  - `additional_certificates`
  - `additional_certificates_filename`
  - `portal_last_update`
  - `portal_updates_count`
  - `survey_sent`
  - `survey_result_url`
  - `interview_date_1`
  - `interview_result_1`
  - `interview_date_2`
  - `interview_result_2`
  - `interview_date_3`
  - `interview_result_3`
  - `interview_date_4`
  - `interview_result_4`
  - `interview_slot_token`
  - `interview_slot_event_id`
  - `next_interview_round`
  - `job_level_code`
  - `max_interview_round`
  - `office_stage_statusbar_ids`
  - `next_round_event_id`
  - `next_round_event_needs_notification`
  - `cv_checked`
  - `offer_status`
  - `eval_l1_id`
  - `eval_l2_id`
  - `eval_l3_id`
  - `eval_l4_id`
  - `primary_interviewer_l1_user_id`
  - `primary_interviewer_l2_user_id`
  - `primary_interviewer_l3_user_id`
  - `primary_interviewer_l4_user_id`
  - `allowed_primary_interviewer_l3_ids`
  - `allowed_primary_interviewer_l4_ids`
  - `evaluation_line_ids`
  - `eval_round_1_score`
  - `eval_round_2_score`
  - `eval_round_3_score`
  - `eval_round_4_score`
  - `eval_round_1_pass`
  - `eval_round_2_pass`
  - `eval_round_3_pass`
  - `eval_round_4_pass`
  - `eval_round_1_toggle`
  - `eval_round_2_toggle`
  - `eval_round_3_toggle`
  - `eval_round_4_toggle`
  - `eval_round_1_primary_pending`
  - `eval_round_2_primary_pending`
  - `eval_round_3_primary_pending`
  - `eval_round_4_primary_pending`
  - `eval_round_1_primary_warning`
  - `eval_round_2_primary_warning`
  - `eval_round_3_primary_warning`
  - `eval_round_4_primary_warning`
  - `needs_primary_interviewer_review`
  - `primary_interviewer_review_note`
  - `application_source`

### `hr.job`

- File: `models/hr_job.py`
- Các field bổ sung:
  - `current_employee_count`
  - `needed_recruitment`
  - `is_office_job`
  - `survey_id`
  - `job_intro`
  - `responsibilities`
  - `must_have`
  - `nice_to_have`
  - `whats_great`

### `res.company`

- File: `models/res_company.py`
- Các field bổ sung:
  - `ceo_id`

### `survey.survey`

- File: `models/survey_ext.py`
- Các field bổ sung:
  - `is_pre_interview`

### `survey.question.answer`

- File: `models/survey_ext.py`
- Các field bổ sung:
  - `is_must_have`
  - `is_nice_to_have`

### Ghi chú

- `hr.recruitment.stage` và `mail.activity` có được kế thừa trong module, nhưng hiện không khai báo field mới.

## 2. Field tạo mới hoàn toàn trong module 0205

### `recruitment.request.approver`

- File: `models/recruitment_request.py`
- Các field:
  - `request_id`
  - `department_id`
  - `manager_id`
  - `user_id`
  - `status`
  - `approved_date`
  - `notes`

### `recruitment.request`

- File: `models/recruitment_request.py`
- Các field:
  - `name`
  - `batch_id`
  - `request_type`
  - `job_id`
  - `department_id`
  - `quantity`
  - `date_start`
  - `date_end`
  - `reason`
  - `line_ids`
  - `approver_ids`
  - `user_id`
  - `company_id`
  - `recruitment_plan_id`
  - `user_department_id`
  - `state`
  - `is_published`

### `recruitment.request.line`

- File: `models/recruitment_request.py`
- Các field:
  - `request_id`
  - `department_id`
  - `job_id`
  - `quantity`
  - `planned_date`
  - `date_start`
  - `date_end`
  - `reason`

### `recruitment.plan`

- File: `models/recruitment_plan.py`
- Các field:
  - `name`
  - `line_ids`
  - `priority`
  - `reason`
  - `state`
  - `company_id`
  - `user_id`
  - `request_count`
  - `job_count`
  - `total_quantity`
  - `batch_id`
  - `date_submitted`
  - `is_reminder_sent`
  - `can_approve_as_manager`
  - `parent_id`
  - `sub_plan_ids`
  - `department_id`
  - `is_sub_plan`

### `recruitment.plan.line`

- File: `models/recruitment_plan.py`
- Các field:
  - `plan_id`
  - `department_id`
  - `job_id`
  - `quantity`
  - `planned_date`
  - `reason`
  - `is_approved`
  - `state`
  - `batch_id`
  - `applicant_count`
  - `interview_count`
  - `hired_count`
  - `is_published`

### `recruitment.batch`

- File: `models/recruitment_plan.py`
- Các field:
  - `name`
  - `batch_name`
  - `date_start`
  - `date_end`
  - `state`
  - `line_ids`

### `hr.applicant.evaluation`

- File: `models/hr_applicant.py`
- Các field:
  - `applicant_id`
  - `interview_round`
  - `interviewer_id`
  - `primary_interviewer_user_id`
  - `is_primary_interviewer`
  - `date`
  - `attitude_score`
  - `skill_score`
  - `experience_score`
  - `culture_fit_score`
  - `strengths`
  - `weaknesses`
  - `note`
  - `evaluation_item_ids`
  - `scored_line_count`
  - `weighted_total_score`
  - `average_score`
  - `final_result`
  - `onboard_time`
  - `final_comment`
  - `recommendation`

### `hr.applicant.evaluation.line`

- File: `models/hr_applicant.py`
- Các field:
  - `evaluation_id`
  - `sequence`
  - `section_code`
  - `section_label`
  - `item_code`
  - `item_label`
  - `line_type`
  - `score_value`
  - `score_1`
  - `score_2`
  - `score_3`
  - `score_4`
  - `score_5`
  - `note`
  - `is_scored`

## 3. Tóm tắt nhanh

### Nhóm field kế thừa từ Odoo

- `calendar.event`
- `hr.applicant`
- `hr.job`
- `res.company`
- `survey.survey`
- `survey.question.answer`

### Nhóm field của model tạo mới

- `recruitment.request.approver`
- `recruitment.request`
- `recruitment.request.line`
- `recruitment.plan`
- `recruitment.plan.line`
- `recruitment.batch`
- `hr.applicant.evaluation`
- `hr.applicant.evaluation.line`
