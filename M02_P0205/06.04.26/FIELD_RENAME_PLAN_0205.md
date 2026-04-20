# Danh Sách Field Cần Đổi Tên Theo Chuẩn `x_psm_`

Tài liệu này liệt kê các field trong module `M02_P0205` nên được đổi tên theo quy ước:

- `x_psm_<ten_field_cu>`

Mục tiêu:

- chuẩn hóa naming cho toàn bộ field custom
- tách rõ field custom với field chuẩn của Odoo
- tránh nhầm lẫn khi bảo trì, nâng cấp hoặc đối chiếu với core model

## 1. Nguyên tắc lập danh sách

Danh sách này được chia thành 2 nhóm:

- Nhóm A: field custom nên đổi tên ngay
- Nhóm B: field cần rà lại trước khi đổi tên vì đang trùng hoặc chạm vào field chuẩn của Odoo

Lưu ý:

- Không nên đổi tên mù tất cả field trong các model kế thừa.
- Với các field đang override hoặc redeclare field chuẩn của Odoo, cần xem lại kỹ trước khi rename.

## 2. Nhóm A - Field custom nên đổi tên ngay

## 2.1. Field custom trên model kế thừa từ Odoo

### `calendar.event`

- `round2_notification_sent` -> `x_psm_round2_notification_sent`
- `round3_notification_sent` -> `x_psm_round3_notification_sent`
- `round4_notification_sent` -> `x_psm_round4_notification_sent`
- `interview_round` -> `x_psm_interview_round`

### `hr.applicant`

- `recruitment_type` -> `x_psm_recruitment_type`
- `document_approval_status` -> `x_psm_document_approval_status`
- `passport_photo` -> `x_psm_passport_photo`
- `passport_photo_filename` -> `x_psm_passport_photo_filename`
- `id_card_front` -> `x_psm_id_card_front`
- `id_card_front_filename` -> `x_psm_id_card_front_filename`
- `id_card_back` -> `x_psm_id_card_back`
- `id_card_back_filename` -> `x_psm_id_card_back_filename`
- `household_registration` -> `x_psm_household_registration`
- `household_registration_filename` -> `x_psm_household_registration_filename`
- `judicial_record` -> `x_psm_judicial_record`
- `judicial_record_filename` -> `x_psm_judicial_record_filename`
- `professional_certificate` -> `x_psm_professional_certificate`
- `professional_certificate_filename` -> `x_psm_professional_certificate_filename`
- `additional_certificates` -> `x_psm_additional_certificates`
- `additional_certificates_filename` -> `x_psm_additional_certificates_filename`
- `portal_last_update` -> `x_psm_portal_last_update`
- `portal_updates_count` -> `x_psm_portal_updates_count`
- `survey_sent` -> `x_psm_survey_sent`
- `survey_result_url` -> `x_psm_survey_result_url`
- `interview_date_1` -> `x_psm_interview_date_1`
- `interview_result_1` -> `x_psm_interview_result_1`
- `interview_date_2` -> `x_psm_interview_date_2`
- `interview_result_2` -> `x_psm_interview_result_2`
- `interview_date_3` -> `x_psm_interview_date_3`
- `interview_result_3` -> `x_psm_interview_result_3`
- `interview_date_4` -> `x_psm_interview_date_4`
- `interview_result_4` -> `x_psm_interview_result_4`
- `interview_slot_token` -> `x_psm_interview_slot_token`
- `interview_slot_event_id` -> `x_psm_interview_slot_event_id`
- `next_interview_round` -> `x_psm_next_interview_round`
- `job_level_code` -> `x_psm_job_level_code`
- `max_interview_round` -> `x_psm_max_interview_round`
- `office_stage_statusbar_ids` -> `x_psm_office_stage_statusbar_ids`
- `next_round_event_id` -> `x_psm_next_round_event_id`
- `next_round_event_needs_notification` -> `x_psm_next_round_event_needs_notification`
- `cv_checked` -> `x_psm_cv_checked`
- `offer_status` -> `x_psm_offer_status`
- `eval_l1_id` -> `x_psm_eval_l1_id`
- `eval_l2_id` -> `x_psm_eval_l2_id`
- `eval_l3_id` -> `x_psm_eval_l3_id`
- `eval_l4_id` -> `x_psm_eval_l4_id`
- `primary_interviewer_l1_user_id` -> `x_psm_primary_interviewer_l1_user_id`
- `primary_interviewer_l2_user_id` -> `x_psm_primary_interviewer_l2_user_id`
- `primary_interviewer_l3_user_id` -> `x_psm_primary_interviewer_l3_user_id`
- `primary_interviewer_l4_user_id` -> `x_psm_primary_interviewer_l4_user_id`
- `allowed_primary_interviewer_l3_ids` -> `x_psm_allowed_primary_interviewer_l3_ids`
- `allowed_primary_interviewer_l4_ids` -> `x_psm_allowed_primary_interviewer_l4_ids`
- `evaluation_line_ids` -> `x_psm_evaluation_line_ids`
- `eval_round_1_score` -> `x_psm_eval_round_1_score`
- `eval_round_2_score` -> `x_psm_eval_round_2_score`
- `eval_round_3_score` -> `x_psm_eval_round_3_score`
- `eval_round_4_score` -> `x_psm_eval_round_4_score`
- `eval_round_1_pass` -> `x_psm_eval_round_1_pass`
- `eval_round_2_pass` -> `x_psm_eval_round_2_pass`
- `eval_round_3_pass` -> `x_psm_eval_round_3_pass`
- `eval_round_4_pass` -> `x_psm_eval_round_4_pass`
- `eval_round_1_toggle` -> `x_psm_eval_round_1_toggle`
- `eval_round_2_toggle` -> `x_psm_eval_round_2_toggle`
- `eval_round_3_toggle` -> `x_psm_eval_round_3_toggle`
- `eval_round_4_toggle` -> `x_psm_eval_round_4_toggle`
- `eval_round_1_primary_pending` -> `x_psm_eval_round_1_primary_pending`
- `eval_round_2_primary_pending` -> `x_psm_eval_round_2_primary_pending`
- `eval_round_3_primary_pending` -> `x_psm_eval_round_3_primary_pending`
- `eval_round_4_primary_pending` -> `x_psm_eval_round_4_primary_pending`
- `eval_round_1_primary_warning` -> `x_psm_eval_round_1_primary_warning`
- `eval_round_2_primary_warning` -> `x_psm_eval_round_2_primary_warning`
- `eval_round_3_primary_warning` -> `x_psm_eval_round_3_primary_warning`
- `eval_round_4_primary_warning` -> `x_psm_eval_round_4_primary_warning`
- `needs_primary_interviewer_review` -> `x_psm_needs_primary_interviewer_review`
- `primary_interviewer_review_note` -> `x_psm_primary_interviewer_review_note`
- `application_source` -> `x_psm_application_source`

### `hr.job`

- `current_employee_count` -> `x_psm_current_employee_count`
- `needed_recruitment` -> `x_psm_needed_recruitment`
- `is_office_job` -> `x_psm_is_office_job`
- `job_intro` -> `x_psm_job_intro`
- `responsibilities` -> `x_psm_responsibilities`
- `must_have` -> `x_psm_must_have`
- `nice_to_have` -> `x_psm_nice_to_have`
- `whats_great` -> `x_psm_whats_great`

### `res.company`

- `ceo_id` -> `x_psm_ceo_id`

### `survey.survey`

- `is_pre_interview` -> `x_psm_is_pre_interview`

### `survey.question.answer`

- `is_must_have` -> `x_psm_is_must_have`
- `is_nice_to_have` -> `x_psm_is_nice_to_have`

## 2.2. Field trên các model tạo mới hoàn toàn trong module 0205

### `recruitment.request.approver`

- `request_id` -> `x_psm_request_id`
- `department_id` -> `x_psm_department_id`
- `manager_id` -> `x_psm_manager_id`
- `user_id` -> `x_psm_user_id`
- `status` -> `x_psm_status`
- `approved_date` -> `x_psm_approved_date`
- `notes` -> `x_psm_notes`

### `recruitment.request`

- `name` -> `x_psm_name`
- `batch_id` -> `x_psm_batch_id`
- `request_type` -> `x_psm_request_type`
- `job_id` -> `x_psm_job_id`
- `department_id` -> `x_psm_department_id`
- `quantity` -> `x_psm_quantity`
- `date_start` -> `x_psm_date_start`
- `date_end` -> `x_psm_date_end`
- `reason` -> `x_psm_reason`
- `line_ids` -> `x_psm_line_ids`
- `approver_ids` -> `x_psm_approver_ids`
- `user_id` -> `x_psm_user_id`
- `company_id` -> `x_psm_company_id`
- `recruitment_plan_id` -> `x_psm_recruitment_plan_id`
- `user_department_id` -> `x_psm_user_department_id`
- `state` -> `x_psm_state`
- `is_published` -> `x_psm_is_published`

### `recruitment.request.line`

- `request_id` -> `x_psm_request_id`
- `department_id` -> `x_psm_department_id`
- `job_id` -> `x_psm_job_id`
- `quantity` -> `x_psm_quantity`
- `planned_date` -> `x_psm_planned_date`
- `date_start` -> `x_psm_date_start`
- `date_end` -> `x_psm_date_end`
- `reason` -> `x_psm_reason`

### `recruitment.plan`

- `name` -> `x_psm_name`
- `line_ids` -> `x_psm_line_ids`
- `priority` -> `x_psm_priority`
- `reason` -> `x_psm_reason`
- `state` -> `x_psm_state`
- `company_id` -> `x_psm_company_id`
- `user_id` -> `x_psm_user_id`
- `request_count` -> `x_psm_request_count`
- `job_count` -> `x_psm_job_count`
- `total_quantity` -> `x_psm_total_quantity`
- `batch_id` -> `x_psm_batch_id`
- `date_submitted` -> `x_psm_date_submitted`
- `is_reminder_sent` -> `x_psm_is_reminder_sent`
- `can_approve_as_manager` -> `x_psm_can_approve_as_manager`
- `parent_id` -> `x_psm_parent_id`
- `sub_plan_ids` -> `x_psm_sub_plan_ids`
- `department_id` -> `x_psm_department_id`
- `is_sub_plan` -> `x_psm_is_sub_plan`

### `recruitment.plan.line`

- `plan_id` -> `x_psm_plan_id`
- `department_id` -> `x_psm_department_id`
- `job_id` -> `x_psm_job_id`
- `quantity` -> `x_psm_quantity`
- `planned_date` -> `x_psm_planned_date`
- `reason` -> `x_psm_reason`
- `is_approved` -> `x_psm_is_approved`
- `state` -> `x_psm_state`
- `batch_id` -> `x_psm_batch_id`
- `applicant_count` -> `x_psm_applicant_count`
- `interview_count` -> `x_psm_interview_count`
- `hired_count` -> `x_psm_hired_count`
- `is_published` -> `x_psm_is_published`

### `recruitment.batch`

- `name` -> `x_psm_name`
- `batch_name` -> `x_psm_batch_name`
- `date_start` -> `x_psm_date_start`
- `date_end` -> `x_psm_date_end`
- `state` -> `x_psm_state`
- `line_ids` -> `x_psm_line_ids`

### `hr.applicant.evaluation`

- `applicant_id` -> `x_psm_applicant_id`
- `interview_round` -> `x_psm_interview_round`
- `interviewer_id` -> `x_psm_interviewer_id`
- `primary_interviewer_user_id` -> `x_psm_primary_interviewer_user_id`
- `is_primary_interviewer` -> `x_psm_is_primary_interviewer`
- `date` -> `x_psm_date`
- `attitude_score` -> `x_psm_attitude_score`
- `skill_score` -> `x_psm_skill_score`
- `experience_score` -> `x_psm_experience_score`
- `culture_fit_score` -> `x_psm_culture_fit_score`
- `strengths` -> `x_psm_strengths`
- `weaknesses` -> `x_psm_weaknesses`
- `note` -> `x_psm_note`
- `evaluation_item_ids` -> `x_psm_evaluation_item_ids`
- `scored_line_count` -> `x_psm_scored_line_count`
- `weighted_total_score` -> `x_psm_weighted_total_score`
- `average_score` -> `x_psm_average_score`
- `final_result` -> `x_psm_final_result`
- `onboard_time` -> `x_psm_onboard_time`
- `final_comment` -> `x_psm_final_comment`
- `recommendation` -> `x_psm_recommendation`

### `hr.applicant.evaluation.line`

- `evaluation_id` -> `x_psm_evaluation_id`
- `sequence` -> `x_psm_sequence`
- `section_code` -> `x_psm_section_code`
- `section_label` -> `x_psm_section_label`
- `item_code` -> `x_psm_item_code`
- `item_label` -> `x_psm_item_label`
- `line_type` -> `x_psm_line_type`
- `score_value` -> `x_psm_score_value`
- `score_1` -> `x_psm_score_1`
- `score_2` -> `x_psm_score_2`
- `score_3` -> `x_psm_score_3`
- `score_4` -> `x_psm_score_4`
- `score_5` -> `x_psm_score_5`
- `note` -> `x_psm_note`
- `is_scored` -> `x_psm_is_scored`

## 3. Nhóm B - Field cần rà lại trước khi đổi tên

Các field dưới đây hiện đang trùng tên hoặc chạm vào field chuẩn của Odoo. Không nên đổi sang `X_PSM_*` một cách tự động trước khi xác nhận rõ mục tiêu kỹ thuật.

### `hr.applicant`

- `stage_id`
- `priority`

Lý do:

- đây là field chuẩn của Odoo đã tồn tại trên `hr.applicant`
- trong module hiện tại, các field này đang bị override hoặc redeclare
- nếu đổi sang `x_psm_stage_id` hoặc `x_psm_priority`, logic view, domain, pipeline và core flow của Odoo sẽ thay đổi rất mạnh

### `hr.job`

- `survey_id`

Lý do:

- `survey_id` đã tồn tại sẵn từ addon chuẩn `hr_recruitment_survey`
- đây là field nên được dùng theo chuẩn Odoo, không nên đổi tên thành field custom mới nếu chưa có kế hoạch refactor rõ ràng

## 4. Gợi ý triển khai

Nếu triển khai rename thực tế, nên làm theo thứ tự:

1. đổi các field custom trên model kế thừa nhưng không đụng core field
2. đổi các field trên model tạo mới hoàn toàn
3. rà lại riêng các field override/redeclare trước khi quyết định có đổi hay không

## 5. Kết luận ngắn

Danh sách trong tài liệu này là danh sách an toàn hơn để phục vụ chuẩn hóa naming.

Nếu cần rename ở mức code thật, nên coi:

- Nhóm A là danh sách có thể triển khai trước
- Nhóm B là danh sách cần phân tích kỹ trước khi sửa
