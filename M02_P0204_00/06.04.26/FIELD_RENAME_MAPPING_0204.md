# Field Rename Mapping 0204

Tai lieu nay la mapping de xuat theo rule:

- Field tren model goc: `x_psm_0204_<tenfield>`
- Field tren model moi: `x_psm_<tenfield>`

Luu y:

- Day la inventory mapping ky thuat, chua phai patch rename code.
- Khi thuc thi that, can lap migration cho du lieu cu (`oldname`/SQL script).

## 1. Model goc (_inherit)

## 1.1 hr.applicant

- `company_id` -> `x_psm_0204_company_id`
- `department_id` -> `x_psm_0204_department_id`
- `recruitment_type` -> `x_psm_0204_recruitment_type`
- `position_level` -> `x_psm_0204_position_level`
- `stage_filter_type` -> `x_psm_0204_stage_filter_type`
- `interview_schedule_id` -> `x_psm_0204_interview_schedule_id`
- `available_department_ids` -> `x_psm_0204_available_department_ids`
- `pre_interview_survey_id` -> `x_psm_0204_pre_interview_survey_id`
- `survey_user_input_id` -> `x_psm_0204_survey_user_input_id`
- `survey_url` -> `x_psm_0204_survey_url`
- `survey_state` -> `x_psm_0204_survey_state`
- `survey_scoring_percentage` -> `x_psm_0204_survey_scoring_percentage`
- `survey_scoring_success` -> `x_psm_0204_survey_scoring_success`
- `survey_result_url` -> `x_psm_0204_survey_result_url`
- `application_match_result` -> `x_psm_0204_application_match_result`
- `application_form_review_payload` -> `x_psm_0204_application_form_review_payload`
- `application_form_review_html` -> `x_psm_0204_application_form_review_html`
- `failed_mandatory_questions` -> `x_psm_0204_failed_mandatory_questions`
- `interview_evaluator_user_id` -> `x_psm_0204_interview_evaluator_user_id`
- `interview_evaluation_id` -> `x_psm_0204_interview_evaluation_id`
- `interview_evaluation_state` -> `x_psm_0204_interview_evaluation_state`
- `can_backend_evaluate_interview` -> `x_psm_0204_can_backend_evaluate_interview`
- `interview_final_score` -> `x_psm_0204_interview_final_score`
- `interview_result` -> `x_psm_0204_interview_result`
- `interview_evaluated_by` -> `x_psm_0204_interview_evaluated_by`
- `interview_evaluated_at` -> `x_psm_0204_interview_evaluated_at`
- `interview_fail_reason` -> `x_psm_0204_interview_fail_reason`
- `oje_evaluator_user_id` -> `x_psm_0204_oje_evaluator_user_id`
- `oje_evaluation_id` -> `x_psm_0204_oje_evaluation_id`
- `oje_evaluation_state` -> `x_psm_0204_oje_evaluation_state`
- `can_backend_evaluate_oje` -> `x_psm_0204_can_backend_evaluate_oje`
- `reject_reason` -> `x_psm_0204_reject_reason`
- `refuse_reason_m2m_ids` -> `x_psm_0204_refuse_reason_m2m_ids`
- `oje_total_score` -> `x_psm_0204_oje_total_score`
- `oje_result` -> `x_psm_0204_oje_result`
- `oje_evaluated_by` -> `x_psm_0204_oje_evaluated_by`
- `oje_evaluated_at` -> `x_psm_0204_oje_evaluated_at`
- `oje_pass_score_snapshot` -> `x_psm_0204_oje_pass_score_snapshot`
- `oje_template_scope` -> `x_psm_0204_oje_template_scope`
- `oje_staff_decision` -> `x_psm_0204_oje_staff_decision`
- `oje_staff_ni_count` -> `x_psm_0204_oje_staff_ni_count`
- `oje_staff_gd_count` -> `x_psm_0204_oje_staff_gd_count`
- `oje_staff_ex_count` -> `x_psm_0204_oje_staff_ex_count`
- `oje_staff_os_count` -> `x_psm_0204_oje_staff_os_count`
- `oje_management_overall_rating` -> `x_psm_0204_oje_management_overall_rating`
- `oje_fail_reason` -> `x_psm_0204_oje_fail_reason`
- `oje_survey_id` -> `x_psm_0204_oje_survey_id`
- `oje_survey_user_input_id` -> `x_psm_0204_oje_survey_user_input_id`
- `oje_survey_url` -> `x_psm_0204_oje_survey_url`
- `oje_survey_state` -> `x_psm_0204_oje_survey_state`
- `oje_survey_scoring_percentage` -> `x_psm_0204_oje_survey_scoring_percentage`
- `oje_survey_scoring_success` -> `x_psm_0204_oje_survey_scoring_success`
- `survey_display_text` -> `x_psm_0204_survey_display_text`
- `survey_display_result` -> `x_psm_0204_survey_display_result`
- `interview_display_text` -> `x_psm_0204_interview_display_text`
- `interview_display_result` -> `x_psm_0204_interview_display_result`
- `oje_display_text` -> `x_psm_0204_oje_display_text`
- `oje_display_result` -> `x_psm_0204_oje_display_result`
- `interview_invitation_sent` -> `x_psm_0204_interview_invitation_sent`
- `invitation_sent_date` -> `x_psm_0204_invitation_sent_date`
- `interview_confirmation_state` -> `x_psm_0204_interview_confirmation_state`
- `interview_accept_token` -> `x_psm_0204_interview_accept_token`
- `interview_confirmation_sent_date` -> `x_psm_0204_interview_confirmation_sent_date`
- `interview_preferred_datetime` -> `x_psm_0204_interview_preferred_datetime`
- `interview_preferred_slot_label` -> `x_psm_0204_interview_preferred_slot_label`
- `interview_accepted_date` -> `x_psm_0204_interview_accepted_date`
- `interview_confirmed_datetime` -> `x_psm_0204_interview_confirmed_datetime`
- `interview_event_id` -> `x_psm_0204_interview_event_id`
- `interview_booked_slot` -> `x_psm_0204_interview_booked_slot`
- `interview_booking_status` -> `x_psm_0204_interview_booking_status`
- `survey_under_review_date` -> `x_psm_0204_survey_under_review_date`
- `application_source` -> `x_psm_0204_application_source`
- `current_stage_name` -> `x_psm_0204_current_stage_name`
- `hide_approval_buttons` -> `x_psm_0204_hide_approval_buttons`
- `x_birthday` -> `x_psm_0204_x_birthday`
- `x_current_job` -> `x_psm_0204_x_current_job`
- `x_portrait_image` -> `x_psm_0204_x_portrait_image`
- `x_gender` -> `x_psm_0204_x_gender`
- `x_id_document_type` -> `x_psm_0204_x_id_document_type`
- `x_id_number` -> `x_psm_0204_x_id_number`
- `x_education_level` -> `x_psm_0204_x_education_level`
- `x_school_name` -> `x_psm_0204_x_school_name`
- `x_current_address` -> `x_psm_0204_x_current_address`
- `x_weekend_available` -> `x_psm_0204_x_weekend_available`
- `x_worked_mcdonalds` -> `x_psm_0204_x_worked_mcdonalds`
- `x_last_company` -> `x_psm_0204_x_last_company`
- `x_referral_staff_id` -> `x_psm_0204_x_referral_staff_id`
- `x_application_content` -> `x_psm_0204_x_application_content`
- `x_salutation` -> `x_psm_0204_x_salutation`
- `x_id_issue_date` -> `x_psm_0204_x_id_issue_date`
- `x_id_issue_place` -> `x_psm_0204_x_id_issue_place`
- `x_permanent_address` -> `x_psm_0204_x_permanent_address`
- `x_hometown` -> `x_psm_0204_x_hometown`
- `x_years_experience` -> `x_psm_0204_x_years_experience`
- `x_height` -> `x_psm_0204_x_height`
- `x_weight` -> `x_psm_0204_x_weight`
- `x_nationality` -> `x_psm_0204_x_nationality`

## 1.2 hr.job

- `no_of_recruitment` -> `x_psm_0204_no_of_recruitment`
- `recruitment_qty_updated_at` -> `x_psm_0204_recruitment_qty_updated_at`
- `recruitment_type` -> `x_psm_0204_recruitment_type`
- `position_level` -> `x_psm_0204_position_level`
- `auto_evaluate_survey` -> `x_psm_0204_auto_evaluate_survey`
- `survey_eval_mode` -> `x_psm_0204_survey_eval_mode`
- `min_correct_answers` -> `x_psm_0204_min_correct_answers`
- `display_name_with_dept` -> `x_psm_0204_display_name_with_dept`
- `job_refuse_reason_ids` -> `x_psm_0204_job_refuse_reason_ids`
- `email_rule_ids` -> `x_psm_0204_email_rule_ids`
- `email_rule_stage_ids` -> `x_psm_0204_email_rule_stage_ids`
- `email_rule_event_ids` -> `x_psm_0204_email_rule_event_ids`
- `oje_pass_score` -> `x_psm_0204_oje_pass_score`
- `oje_evaluator_user_id` -> `x_psm_0204_oje_evaluator_user_id`
- `interview_evaluator_user_id` -> `x_psm_0204_interview_evaluator_user_id`

## 1.3 hr.recruitment.stage

- `recruitment_type` -> `x_psm_0204_recruitment_type`
- `office_pipeline_visible` -> `x_psm_0204_office_pipeline_visible`
- `candidate_email_enabled` -> `x_psm_0204_candidate_email_enabled`
- `candidate_email_template_id` -> `x_psm_0204_candidate_email_template_id`

## 1.4 survey.survey / survey.question

- `is_pre_interview` -> `x_psm_0204_is_pre_interview`
- `is_oje_evaluation` -> `x_psm_0204_is_oje_evaluation`
- `owner_job_id` -> `x_psm_0204_owner_job_id`
- `default_template_for` -> `x_psm_0204_default_template_for`
- `is_mandatory_correct` -> `x_psm_0204_is_mandatory_correct`
- `is_reject_when_wrong` -> `x_psm_0204_is_reject_when_wrong`

## 1.5 survey.user_input.line

- `is_mandatory_correct` -> `x_psm_0204_is_mandatory_correct`
- `is_reject_when_wrong` -> `x_psm_0204_is_reject_when_wrong`

## 1.6 applicant.get.refuse.reason (wizard)

- `job_id` -> `x_psm_0204_job_id`
- `reason_type` -> `x_psm_0204_reason_type`
- `wizard_id` -> `x_psm_0204_wizard_id`
- `job_refuse_reason_id` -> `x_psm_0204_job_refuse_reason_id`
- `name` -> `x_psm_0204_name`
- `is_selected` -> `x_psm_0204_is_selected`
- `custom_text` -> `x_psm_0204_custom_text`
- `refuse_reason_ids` -> `x_psm_0204_refuse_reason_ids`
- `source_action` -> `x_psm_0204_source_action`
- `wizard_line_ids` -> `x_psm_0204_wizard_line_ids`

## 2. Model moi (_name)

## 2.1 interview.schedule

- `company_id` -> `x_psm_company_id`
- `department_id` -> `x_psm_department_id`
- `store_address` -> `x_psm_store_address`
- `manager_id` -> `x_psm_manager_id`
- `week_start_date` -> `x_psm_week_start_date`
- `week_display` -> `x_psm_week_display`
- `week_end_date` -> `x_psm_week_end_date`
- `is_current_week` -> `x_psm_is_current_week`
- `interview_date_1` -> `x_psm_interview_date_1`
- `interview_date_2` -> `x_psm_interview_date_2`
- `interview_date_3` -> `x_psm_interview_date_3`
- `interview_date_1_vn` -> `x_psm_interview_date_1_vn`
- `interview_date_2_vn` -> `x_psm_interview_date_2_vn`
- `interview_date_3_vn` -> `x_psm_interview_date_3_vn`
- `max_candidates_slot_1` -> `x_psm_max_candidates_slot_1`
- `max_candidates_slot_2` -> `x_psm_max_candidates_slot_2`
- `max_candidates_slot_3` -> `x_psm_max_candidates_slot_3`
- `slot_1_remaining` -> `x_psm_slot_1_remaining`
- `slot_2_remaining` -> `x_psm_slot_2_remaining`
- `slot_3_remaining` -> `x_psm_slot_3_remaining`
- `state` -> `x_psm_state`
- `applicant_count` -> `x_psm_applicant_count`
- `display_name` -> `x_psm_display_name`

## 2.2 hr.job.email.rule

- `job_id` -> `x_psm_job_id`
- `active` -> `x_psm_active`
- `sequence` -> `x_psm_sequence`
- `rule_type` -> `x_psm_rule_type`
- `stage_id` -> `x_psm_stage_id`
- `event_code` -> `x_psm_event_code`
- `template_id` -> `x_psm_template_id`

## 2.3 hr.applicant.interview.evaluation*

- `applicant_id` -> `x_psm_applicant_id`
- `job_id` -> `x_psm_job_id`
- `evaluator_user_id` -> `x_psm_evaluator_user_id`
- `state` -> `x_psm_state`
- `interview_date` -> `x_psm_interview_date`
- `interviewer_name` -> `x_psm_interviewer_name`
- `onboard_time` -> `x_psm_onboard_time`
- `submitted_at` -> `x_psm_submitted_at`
- `overall_note` -> `x_psm_overall_note`
- `template_version` -> `x_psm_template_version`
- `config_signature` -> `x_psm_config_signature`
- `score_1_count` -> `x_psm_score_1_count`
- `score_2_count` -> `x_psm_score_2_count`
- `score_3_count` -> `x_psm_score_3_count`
- `score_4_count` -> `x_psm_score_4_count`
- `score_5_count` -> `x_psm_score_5_count`
- `weighted_total` -> `x_psm_weighted_total`
- `rated_line_count` -> `x_psm_rated_line_count`
- `final_score` -> `x_psm_final_score`
- `result` -> `x_psm_result`
- `stage_applied` -> `x_psm_stage_applied`
- `section_ids` -> `x_psm_section_ids`
- `line_ids` -> `x_psm_line_ids`
- `evaluation_id` -> `x_psm_evaluation_id`
- `source_config_section_id` -> `x_psm_source_config_section_id`
- `sequence` -> `x_psm_sequence`
- `name` -> `x_psm_name`
- `is_active` -> `x_psm_is_active`
- `section_id` -> `x_psm_section_id`
- `template_line_id` -> `x_psm_template_line_id`
- `display_type` -> `x_psm_display_type`
- `label` -> `x_psm_label`
- `question_text` -> `x_psm_question_text`
- `is_required` -> `x_psm_is_required`
- `selected_score` -> `x_psm_selected_score`
- `line_comment` -> `x_psm_line_comment`

## 2.4 hr.applicant.oje.evaluation*

- `applicant_id` -> `x_psm_applicant_id`
- `job_id` -> `x_psm_job_id`
- `evaluator_user_id` -> `x_psm_evaluator_user_id`
- `evaluator_partner_id` -> `x_psm_evaluator_partner_id`
- `state` -> `x_psm_state`
- `template_scope` -> `x_psm_template_scope`
- `template_version` -> `x_psm_template_version`
- `trial_date` -> `x_psm_trial_date`
- `trial_time` -> `x_psm_trial_time`
- `restaurant_name` -> `x_psm_restaurant_name`
- `shift_schedule` -> `x_psm_shift_schedule`
- `operation_consultant_name` -> `x_psm_operation_consultant_name`
- `overall_comments` -> `x_psm_overall_comments`
- `interviewer_note` -> `x_psm_interviewer_note`
- `manager_signature_name` -> `x_psm_manager_signature_name`
- `staff_decision` -> `x_psm_staff_decision`
- `staff_ni_count` -> `x_psm_staff_ni_count`
- `staff_gd_count` -> `x_psm_staff_gd_count`
- `staff_ex_count` -> `x_psm_staff_ex_count`
- `staff_os_count` -> `x_psm_staff_os_count`
- `has_any_ni` -> `x_psm_has_any_ni`
- `management_overall_rating` -> `x_psm_management_overall_rating`
- `management_final_display` -> `x_psm_management_final_display`
- `pass_score_snapshot` -> `x_psm_pass_score_snapshot`
- `total_score` -> `x_psm_total_score`
- `result` -> `x_psm_result`
- `fail_reason` -> `x_psm_fail_reason`
- `submitted_at` -> `x_psm_submitted_at`
- `section_ids` -> `x_psm_section_ids`
- `line_ids` -> `x_psm_line_ids`
- `evaluation_id` -> `x_psm_evaluation_id`
- `source_config_section_id` -> `x_psm_source_config_section_id`
- `sequence` -> `x_psm_sequence`
- `name` -> `x_psm_name`
- `section_kind` -> `x_psm_section_kind`
- `scope` -> `x_psm_scope`
- `rating_mode` -> `x_psm_rating_mode`
- `objective_text` -> `x_psm_objective_text`
- `hint_html` -> `x_psm_hint_html`
- `behavior_html` -> `x_psm_behavior_html`
- `is_active` -> `x_psm_is_active`
- `section_rating` -> `x_psm_section_rating`
- `section_id` -> `x_psm_section_id`
- `template_line_id` -> `x_psm_template_line_id`
- `question_text` -> `x_psm_question_text`
- `is_required` -> `x_psm_is_required`
- `line_kind` -> `x_psm_line_kind`
- `field_type` -> `x_psm_field_type`
- `text_value` -> `x_psm_text_value`
- `text_score` -> `x_psm_text_score`
- `text_max_score` -> `x_psm_text_max_score`
- `checkbox_value` -> `x_psm_checkbox_value`
- `checkbox_score` -> `x_psm_checkbox_score`
- `selected_option_id` -> `x_psm_selected_option_id`
- `selected_option_score` -> `x_psm_selected_option_score`
- `staff_rating` -> `x_psm_staff_rating`
- `management_score` -> `x_psm_management_score`
- `yes_no_answer` -> `x_psm_yes_no_answer`
- `line_comment` -> `x_psm_line_comment`
- `awarded_score` -> `x_psm_awarded_score`

## 3. Field dang dung prefix x_psm_* (giu nguyen)

Trong 0204 da co mot so field dung prefix `x_psm_*` (vi du trong survey va interview line). Cac field nay khong nam trong danh sach doi ten o tren.

## 4. Ghi chu migration

Khi doi ten code that:

- Model goc: uu tien dung `oldname=` cho field.
- Model moi: can migration relation string + ACL + res_model.
- Khong rename truc tiep tren production khi chua co script migration + backup.
