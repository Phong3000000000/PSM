# Phase 1 + Phase 2 Naming Inventory For Module 0205

Tai lieu nay chot pham vi va inventory doi ten cho module `M02_P0205_00` theo file rule moi:
- model goc: giu nguyen ten
- model moi: `x_psm_<ten_model>`
- field moi tren model goc: `x_psm_0205_<tenfield>`
- field moi tren model moi: `x_psm_<tenfield>`
- action moi: `action_psm_<tenaction>`
- view moi: `view_psm_<tenview>`
- security van phong: `group_gdh_rst_<module>_stf`, `group_gdh_rst_<module>_mgr`

## 1. Scope ap dung

Inventory nay chi bam vao active code path cua module:
- `__init__.py` chi import `models`, `controllers`, `hooks`
- `models/__init__.py` la diem tap hop model dang duoc load
- `controllers/__init__.py` la diem tap hop controller dang duoc load

Khong dua cac file trong `office/` vao scope rename chinh vi hien tai khong duoc import tu root module. Thu muc `office/` can duoc xem la tham khao/legacy cho den khi co bang chung no duoc load thuc te.

## 2. Gia dinh naming de dung xuyen suot

De co mot dich doi ten thong nhat, tai lieu nay dung 2 token sau:
- ma quy trinh: `0205`
- token nghiep vu de dat ten artifact phi model: `office_recruitment`

Neu business chot mot token khac cho phan security/menu/view, can doi dong loat tren tat ca de xuyen suot. Con cac model moi va field moi van giu theo rule chinh.

## 3. Phase 1 - Taxonomy va quyet dinh doi ten

### 3.1. Model goc giu nguyen ten

| Model | Loai | File active | Quy tac |
| --- | --- | --- | --- |
| `calendar.event` | model goc | `models/calendar.py` | giu nguyen `_inherit` |
| `hr.applicant` | model goc | `models/hr_applicant.py`, `models/recruitment_plan.py` | giu nguyen `_inherit` |
| `hr.job` | model goc | `models/hr_job.py` | giu nguyen `_inherit` |
| `hr.job.level` | model goc | `models/hr_job_level.py` | giu nguyen `_inherit` |
| `hr.recruitment.stage` | model goc | `models/hr_recruitment_stage.py` | giu nguyen `_inherit` |
| `mail.activity` | model goc | `models/mail_activity.py` | giu nguyen `_inherit` |
| `res.company` | model goc | `models/res_company.py` | giu nguyen `_inherit` |
| `survey.survey` | model goc | `models/survey_ext.py` | giu nguyen `_inherit` |
| `survey.question.answer` | model goc | `models/survey_ext.py` | giu nguyen `_inherit` |

### 3.2. Model moi can doi ten

| Model hien tai | Model de xuat | File active | Ghi chu |
| --- | --- | --- | --- |
| `recruitment.request.approver` | `x_psm_recruitment_request_approver` | `models/recruitment_request.py` | model moi |
| `recruitment.request` | `x_psm_recruitment_request` | `models/recruitment_request.py` | model moi |
| `recruitment.request.line` | `x_psm_recruitment_request_line` | `models/recruitment_request.py` | model moi |
| `recruitment.plan` | `x_psm_recruitment_plan` | `models/recruitment_plan.py` | model moi |
| `recruitment.plan.line` | `x_psm_recruitment_plan_line` | `models/recruitment_plan.py` | model moi |
| `recruitment.batch` | `x_psm_recruitment_batch` | `models/recruitment_plan.py` | model moi |
| `hr.applicant.evaluation` | `x_psm_applicant_evaluation` | `models/hr_applicant.py` | model moi, nen dung tu thong nhat `applicant` |
| `hr.applicant.evaluation.line` | `x_psm_applicant_evaluation_line` | `models/hr_applicant.py` | model moi |

### 3.3. Doi tuong khong doi ten ky thuat

| Doi tuong | Xu ly |
| --- | --- |
| Technical module folder `M02_P0205_00` | chua doi trong phase nay |
| Manifest display name `M02_P0205 - ...` | co the doi sau, khong phai blocker cua Phase 1 + 2 |
| Route URL controller | chua dua vao scope doi ten ky thuat, chi ra soat tham chieu |
| Model/field XML ID cua module goc Odoo hay module khac | giu nguyen |

## 4. Phase 2 - Inventory doi ten

## 4.1. Inventory model theo nhom

### Nhom A - Model goc co field custom can rename theo `x_psm_0205_*`

| Model | Tinh trang |
| --- | --- |
| `calendar.event` | co field custom |
| `hr.applicant` | co nhieu field custom |
| `hr.job` | co field custom |
| `hr.job.level` | can ra soat ky, hien tai chu yeu la bo sung logic/view |
| `res.company` | co field custom |
| `survey.survey` | co field custom |
| `survey.question.answer` | co field custom |

### Nhom B - Model goc chi override logic, khong thay ten model

| Model | Tinh trang |
| --- | --- |
| `mail.activity` | override logic |
| `hr.recruitment.stage` | compatibility/logic |

### Nhom C - Model moi can doi `_name` va field noi bo

| Model hien tai | Model de xuat |
| --- | --- |
| `recruitment.request.approver` | `x_psm_recruitment_request_approver` |
| `recruitment.request` | `x_psm_recruitment_request` |
| `recruitment.request.line` | `x_psm_recruitment_request_line` |
| `recruitment.plan` | `x_psm_recruitment_plan` |
| `recruitment.plan.line` | `x_psm_recruitment_plan_line` |
| `recruitment.batch` | `x_psm_recruitment_batch` |
| `hr.applicant.evaluation` | `x_psm_applicant_evaluation` |
| `hr.applicant.evaluation.line` | `x_psm_applicant_evaluation_line` |

## 4.2. Inventory field theo quy tac moi

### A. Field tren model goc: rename theo `x_psm_0205_*`

Day la nhom field custom can doi ten ky thuat. Danh sach day du nam trong `FIELD_LIST_0205.md`; duoi day la mapping phuc vu Phase 1 + 2.

#### `calendar.event`

| Field hien tai | Field de xuat |
| --- | --- |
| `round2_notification_sent` | `x_psm_0205_round2_notification_sent` |
| `round3_notification_sent` | `x_psm_0205_round3_notification_sent` |
| `round4_notification_sent` | `x_psm_0205_round4_notification_sent` |
| `interview_round` | `x_psm_0205_interview_round` |

#### `hr.applicant`

| Field hien tai | Field de xuat |
| --- | --- |
| `recruitment_type` | `x_psm_0205_recruitment_type` |
| `document_approval_status` | `x_psm_0205_document_approval_status` |
| `passport_photo` | `x_psm_0205_passport_photo` |
| `passport_photo_filename` | `x_psm_0205_passport_photo_filename` |
| `id_card_front` | `x_psm_0205_id_card_front` |
| `id_card_front_filename` | `x_psm_0205_id_card_front_filename` |
| `id_card_back` | `x_psm_0205_id_card_back` |
| `id_card_back_filename` | `x_psm_0205_id_card_back_filename` |
| `household_registration` | `x_psm_0205_household_registration` |
| `household_registration_filename` | `x_psm_0205_household_registration_filename` |
| `judicial_record` | `x_psm_0205_judicial_record` |
| `judicial_record_filename` | `x_psm_0205_judicial_record_filename` |
| `professional_certificate` | `x_psm_0205_professional_certificate` |
| `professional_certificate_filename` | `x_psm_0205_professional_certificate_filename` |
| `additional_certificates` | `x_psm_0205_additional_certificates` |
| `additional_certificates_filename` | `x_psm_0205_additional_certificates_filename` |
| `portal_last_update` | `x_psm_0205_portal_last_update` |
| `portal_updates_count` | `x_psm_0205_portal_updates_count` |
| `survey_sent` | `x_psm_0205_survey_sent` |
| `survey_result_url` | `x_psm_0205_survey_result_url` |
| `interview_date_1` | `x_psm_0205_interview_date_1` |
| `interview_result_1` | `x_psm_0205_interview_result_1` |
| `interview_date_2` | `x_psm_0205_interview_date_2` |
| `interview_result_2` | `x_psm_0205_interview_result_2` |
| `interview_date_3` | `x_psm_0205_interview_date_3` |
| `interview_result_3` | `x_psm_0205_interview_result_3` |
| `interview_date_4` | `x_psm_0205_interview_date_4` |
| `interview_result_4` | `x_psm_0205_interview_result_4` |
| `interview_slot_token` | `x_psm_0205_interview_slot_token` |
| `interview_slot_event_id` | `x_psm_0205_interview_slot_event_id` |
| `next_interview_round` | `x_psm_0205_next_interview_round` |
| `job_level_code` | `x_psm_0205_job_level_code` |
| `max_interview_round` | `x_psm_0205_max_interview_round` |
| `office_stage_statusbar_ids` | `x_psm_0205_office_stage_statusbar_ids` |
| `next_round_event_id` | `x_psm_0205_next_round_event_id` |
| `next_round_event_needs_notification` | `x_psm_0205_next_round_event_needs_notification` |
| `cv_checked` | `x_psm_0205_cv_checked` |
| `offer_status` | `x_psm_0205_offer_status` |
| `eval_l1_id` | `x_psm_0205_eval_l1_id` |
| `eval_l2_id` | `x_psm_0205_eval_l2_id` |
| `eval_l3_id` | `x_psm_0205_eval_l3_id` |
| `eval_l4_id` | `x_psm_0205_eval_l4_id` |
| `primary_interviewer_l1_user_id` | `x_psm_0205_primary_interviewer_l1_user_id` |
| `primary_interviewer_l2_user_id` | `x_psm_0205_primary_interviewer_l2_user_id` |
| `primary_interviewer_l3_user_id` | `x_psm_0205_primary_interviewer_l3_user_id` |
| `primary_interviewer_l4_user_id` | `x_psm_0205_primary_interviewer_l4_user_id` |
| `allowed_primary_interviewer_l3_ids` | `x_psm_0205_allowed_primary_interviewer_l3_ids` |
| `allowed_primary_interviewer_l4_ids` | `x_psm_0205_allowed_primary_interviewer_l4_ids` |
| `evaluation_line_ids` | `x_psm_0205_evaluation_line_ids` |
| `eval_round_1_score` | `x_psm_0205_eval_round_1_score` |
| `eval_round_2_score` | `x_psm_0205_eval_round_2_score` |
| `eval_round_3_score` | `x_psm_0205_eval_round_3_score` |
| `eval_round_4_score` | `x_psm_0205_eval_round_4_score` |
| `eval_round_1_pass` | `x_psm_0205_eval_round_1_pass` |
| `eval_round_2_pass` | `x_psm_0205_eval_round_2_pass` |
| `eval_round_3_pass` | `x_psm_0205_eval_round_3_pass` |
| `eval_round_4_pass` | `x_psm_0205_eval_round_4_pass` |
| `eval_round_1_toggle` | `x_psm_0205_eval_round_1_toggle` |
| `eval_round_2_toggle` | `x_psm_0205_eval_round_2_toggle` |
| `eval_round_3_toggle` | `x_psm_0205_eval_round_3_toggle` |
| `eval_round_4_toggle` | `x_psm_0205_eval_round_4_toggle` |
| `eval_round_1_primary_pending` | `x_psm_0205_eval_round_1_primary_pending` |
| `eval_round_2_primary_pending` | `x_psm_0205_eval_round_2_primary_pending` |
| `eval_round_3_primary_pending` | `x_psm_0205_eval_round_3_primary_pending` |
| `eval_round_4_primary_pending` | `x_psm_0205_eval_round_4_primary_pending` |
| `eval_round_1_primary_warning` | `x_psm_0205_eval_round_1_primary_warning` |
| `eval_round_2_primary_warning` | `x_psm_0205_eval_round_2_primary_warning` |
| `eval_round_3_primary_warning` | `x_psm_0205_eval_round_3_primary_warning` |
| `eval_round_4_primary_warning` | `x_psm_0205_eval_round_4_primary_warning` |
| `needs_primary_interviewer_review` | `x_psm_0205_needs_primary_interviewer_review` |
| `primary_interviewer_review_note` | `x_psm_0205_primary_interviewer_review_note` |
| `application_source` | `x_psm_0205_application_source` |

#### `hr.job`

| Field hien tai | Field de xuat |
| --- | --- |
| `current_employee_count` | `x_psm_0205_current_employee_count` |
| `needed_recruitment` | `x_psm_0205_needed_recruitment` |
| `is_office_job` | `x_psm_0205_is_office_job` |
| `job_intro` | `x_psm_0205_job_intro` |
| `responsibilities` | `x_psm_0205_responsibilities` |
| `must_have` | `x_psm_0205_must_have` |
| `nice_to_have` | `x_psm_0205_nice_to_have` |
| `whats_great` | `x_psm_0205_whats_great` |

#### `res.company`

| Field hien tai | Field de xuat |
| --- | --- |
| `ceo_id` | `x_psm_0205_ceo_id` |

#### `survey.survey`

| Field hien tai | Field de xuat |
| --- | --- |
| `is_pre_interview` | `x_psm_0205_is_pre_interview` |

#### `survey.question.answer`

| Field hien tai | Field de xuat |
| --- | --- |
| `is_must_have` | `x_psm_0205_is_must_have` |
| `is_nice_to_have` | `x_psm_0205_is_nice_to_have` |

### B. Field tren model goc nhung khong dua vao rename scope

Day la nhom can giu nguyen vi la field goc da ton tai san hoac dang override hanh vi tren field co san:
- `hr.applicant.stage_id`
- `hr.applicant.priority`
- `hr.job.survey_id`

Nhom nay can duoc kiem tra ky trong Phase 5 de tranh doi ten nham field san co cua Odoo/module goc.

### C. Field tren model moi: rename theo `x_psm_*`

Danh sach day du da co trong `FIELD_LIST_0205.md`. Quy tac chung duoc chot nhu sau:
- `recruitment.request.approver.*` -> `x_psm_*`
- `recruitment.request.*` -> `x_psm_*`
- `recruitment.request.line.*` -> `x_psm_*`
- `recruitment.plan.*` -> `x_psm_*`
- `recruitment.plan.line.*` -> `x_psm_*`
- `recruitment.batch.*` -> `x_psm_*`
- `hr.applicant.evaluation.*` -> `x_psm_*`
- `hr.applicant.evaluation.line.*` -> `x_psm_*`

Vi du:

| Model | Field hien tai | Field de xuat |
| --- | --- | --- |
| `recruitment.request` | `batch_id` | `x_psm_batch_id` |
| `recruitment.request` | `approver_ids` | `x_psm_approver_ids` |
| `recruitment.plan` | `line_ids` | `x_psm_line_ids` |
| `recruitment.plan.line` | `applicant_count` | `x_psm_applicant_count` |
| `recruitment.batch` | `batch_name` | `x_psm_batch_name` |
| `hr.applicant.evaluation` | `final_result` | `x_psm_final_result` |
| `hr.applicant.evaluation.line` | `score_value` | `x_psm_score_value` |

## 4.3. Inventory action/view/menu/group/XML ID

### A. Action can doi ten sang `action_psm_*`

| XML ID hien tai | XML ID de xuat |
| --- | --- |
| `crm_case_categ0_act_job_office` | `action_psm_job_office_applicant` |
| `crm_case_categ0_act_job_store` | `action_psm_job_store_applicant` |
| `action_recruitment_request_approver` | `action_psm_recruitment_request_approver` |
| `action_recruitment_request_unplanned` | `action_psm_recruitment_request_unplanned` |
| `action_recruitment_request_planned` | `action_psm_recruitment_request_planned` |
| `action_recruitment_plan` | `action_psm_recruitment_plan` |
| `action_recruitment_plan_sub` | `action_psm_recruitment_sub_plan` |
| `action_recruitment_batch` | `action_psm_recruitment_batch` |
| `crm_case_categ0_act_job` | `action_psm_job_office_filter` |

### B. View can doi ten sang `view_psm_*`

| XML ID hien tai | XML ID de xuat |
| --- | --- |
| `m02_p0205_calendar_event_tree_inherit` | `view_psm_calendar_event_tree_inherit` |
| `m02_p0205_calendar_event_form_inherit` | `view_psm_calendar_event_form_inherit` |
| `m02_p0205_calendar_event_quick_create_inherit` | `view_psm_calendar_event_quick_create_inherit` |
| `m02_p0205_calendar_event_search_interview_round` | `view_psm_calendar_event_search_interview_round` |
| `hr_applicant_view_form_inherit_office` | `view_psm_hr_applicant_form_office` |
| `view_hr_applicant_evaluation_form` | `view_psm_applicant_evaluation_form` |
| `view_hr_applicant_evaluation_tree` | `view_psm_applicant_evaluation_tree` |
| `hr_applicant_view_search_inherit_primary_interviewer_review` | `view_psm_hr_applicant_search_primary_interviewer_review` |
| `hr_applicant_view_form_inherit_documents_office` | `view_psm_hr_applicant_form_documents_office` |
| `view_hr_job_tree_interview_round_0205` | `view_psm_hr_job_tree_interview_round` |
| `view_hr_job_form_inherit_portal_mcd` | `view_psm_hr_job_form_portal` |
| `view_hr_job_level_tree_interview_round_0205` | `view_psm_hr_job_level_tree_interview_round` |
| `view_hr_job_level_form_interview_round_0205` | `view_psm_hr_job_level_form_interview_round` |
| `view_company_form_ceo_inherit` | `view_psm_company_form_ceo_inherit` |
| `view_recruitment_request_approver_tree` | `view_psm_recruitment_request_approver_tree` |
| `view_recruitment_request_approver_form` | `view_psm_recruitment_request_approver_form` |
| `view_recruitment_request_form` | `view_psm_recruitment_request_form` |
| `view_recruitment_request_tree` | `view_psm_recruitment_request_tree` |
| `view_recruitment_request_form_reason_inline` | `view_psm_recruitment_request_form_reason_inline` |
| `view_recruitment_plan_tree` | `view_psm_recruitment_plan_tree` |
| `view_recruitment_plan_form` | `view_psm_recruitment_plan_form` |
| `view_recruitment_plan_search` | `view_psm_recruitment_plan_search` |
| `view_recruitment_batch_tree` | `view_psm_recruitment_batch_tree` |
| `view_recruitment_batch_form` | `view_psm_recruitment_batch_form` |
| `survey_question_view_form_inherit_must_have` | `view_psm_survey_question_form_must_have` |

### C. Menu XML ID can doi ten

| XML ID hien tai | XML ID de xuat |
| --- | --- |
| `menu_office_recruitment_root` | `menu_psm_office_recruitment_root` |
| `menu_recruitment_plan` | `menu_psm_recruitment_plan` |
| `menu_recruitment_plan_sub` | `menu_psm_recruitment_sub_plan` |
| `menu_recruitment_batch` | `menu_psm_recruitment_batch` |
| `menu_recruitment_plan_hr` | `menu_psm_recruitment_plan_hr` |
| `menu_recruitment_plan_sub_hr` | `menu_psm_recruitment_sub_plan_hr` |
| `menu_recruitment_request_unplanned` | `menu_psm_recruitment_request_unplanned` |
| `menu_recruitment_request_root` | `menu_psm_recruitment_request_root` |
| `menu_applications_office` | `menu_psm_applications_office` |

### D. Security group can doi ten theo rule van phong

Tai lieu nay de xuat `module` token cho nhom security la `office_recruitment`.

| XML ID hien tai | XML ID de xuat | Ghi chu |
| --- | --- | --- |
| `group_gdh_rst_hr_recruitment_m` | `group_gdh_rst_office_recruitment_mgr` | nhom manager/validator |
| `group_gdh_rst_all_ceo_recruitment_m` | `group_gdh_rst_office_recruitment_mgr_ceo` | ngoai rule mau, can xac nhan co tach role dac thu khong |
| `group_gdh_rst_all_bod_recruitment_m` | `group_gdh_rst_office_recruitment_mgr_bod` | ngoai rule mau, can xac nhan |
| `group_gdh_rst_all_abu_recruitment_m` | `group_gdh_rst_office_recruitment_mgr_abu` | ngoai rule mau, can xac nhan |

Ghi chu:
- chi co `group_gdh_rst_office_recruitment_stf` va `group_gdh_rst_office_recruitment_mgr` la bam sat rule mau
- 3 group CEO/BOD/ABU la role dac thu cua flow `0205`, nen can business quyet dinh giu tach rieng hay map lai vao bo group chuan khac

### E. Sequence, cron, mail template, stage, survey, template

Nhom nay can doi ten XML ID theo prefix thong nhat `psm_`/`view_psm_`/`action_psm_` tuy theo loai artifact:
- sequence:
  - `seq_recruitment_request`
  - `seq_recruitment_plan`
  - `seq_recruitment_plan_force`
- cron:
  - `ir_cron_remind_line_manager`
  - `ir_cron_monthly_recruitment_notification`
  - `ir_cron_auto_publish_batches`
- mail template:
  - `email_candidate_survey_office`
  - `email_interview_invitation_office`
  - `email_interview_round2_notification`
  - `email_interview_round3_notification`
  - `email_interview_round4_notification`
  - `email_interview_slot_survey`
  - `email_offer_letter_office`
  - `email_candidate_survey_fail`
- stage:
  - `stage_office_new`
  - `stage_office_screening`
  - `stage_office_interview_1`
  - `stage_office_interview_2`
  - `stage_office_interview_3`
  - `stage_office_interview_4`
  - `stage_office_probation`
  - `stage_office_proposal`
  - `stage_office_hired`
  - `stage_office_reject`
- website/portal template:
  - `portal_recruitment_theme_assets`
  - `portal_my_home_recruitment_custom`
  - `portal_my_published_jobs`
  - `portal_my_recruitment_requests`
  - `job_portal_theme_assets`
  - `job_apply_template`
  - `job_thankyou_template`
  - `office_job_public_list`
  - `detail_custom_fields`
  - `detail_office_apply_button`
  - `jobs_index_theme`
  - `interview_slot_confirm`
  - `interview_slot_invalid`
  - `office_job_apply_custom`
  - `office_job_apply_field_renderer`
  - `thankyou_recruiter_name_wrap`

### F. Survey data XML ID

Module co so luong lon XML ID cho survey/question/answer. Khong can dat ten tung dong o Phase 1 + 2, nhung can chot quy tac de doi ten hang loat:
- survey goc cua module: `survey_<ten_nghiep_vu>` -> `psm_survey_<ten_nghiep_vu>`
- question section/page: `sq_*`, `mq_*`, `dm_*` -> `psm_sq_*`, `psm_mq_*`, `psm_dm_*`
- answer: `*_a*` -> giu suffix cau truc, doi prefix theo nhom moi

## 5. Khu vuc co rui ro cao khi doi ten

Can danh dau som de cac phase sau chuan bi migration:
- `env.ref('M02_P0205_00...')` trong Python
- `groups="M02_P0205_00.*"` trong XML
- `has_group('M02_P0205_00.*')` trong Python
- ACL `ir.model.access.csv` dang tro vao model custom cu
- relation field giua model moi va model goc
- mail template Jinja dang goi field custom cu
- survey/stage data co the bi ref tu nhieu noi trong code

## 6. Ket luan cho Phase 1 + 2

Sau khi inventory, pham vi doi ten cua `0205` duoc chot nhu sau:
- giu nguyen tat ca model goc Odoo/module goc dang `_inherit`
- doi ten 8 model moi sang prefix `x_psm_`
- doi ten field custom tren model goc sang `x_psm_0205_*`
- doi ten field tren model moi sang `x_psm_*`
- doi ten action sang `action_psm_*`
- doi ten view sang `view_psm_*`
- doi ten menu/group/sequence/cron/template theo prefix thong nhat, nhung 3 group dac thu CEO/BOD/ABU van can business chot muc tieu cuoi cung

Tai lieu nay la input chinh cho:
- Phase 3: security
- Phase 4: action/view/menu/XML ID
- Phase 5: field tren model goc
- Phase 6: model moi
