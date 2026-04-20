# Phase 1 + Phase 2 Naming Inventory For Module 0204

Tai lieu nay chot pham vi va mapping doi ten cho `M02_P0204` theo quy uoc:

- model goc: giu nguyen ten
- model moi: `x_psm_<ten_model>`
- field moi tren model goc: `x_psm_0204_<tenfield>`
- field moi tren model moi: `x_psm_<tenfield>`
- action: `action_psm_<tenaction>`
- view: `view_psm_<tenview>`
- security nha hang: `group_gdh_ops_<module>_crw`, `group_gdh_ops_<module>_mgr`

## 1. Scope ap dung

Inventory nay bam vao code dang duoc load boi module:

- `__manifest__.py`
- `models/__init__.py`
- `controllers/__init__.py`
- `security/*.xml`, `security/*.csv`
- `views/*.xml`, `data/*.xml`

## 2. Phase 1 - Taxonomy

### 2.1 Model goc (_inherit, giu nguyen ten)

| Model goc | File |
| --- | --- |
| `hr.applicant` | `models/hr_applicant.py` |
| `hr.job` | `models/hr_job.py` |
| `hr.recruitment.stage` | `models/hr_recruitment_stage.py` |
| `survey.survey` | `models/survey_survey.py` |
| `survey.question` | `models/survey_survey.py` |
| `survey.user_input` | `models/survey_user_input.py` |
| `survey.user_input.line` | `models/survey_user_input.py` |
| `hr.applicant.refuse.reason` | `models/applicant_refuse_reason.py` |
| `applicant.get.refuse.reason` | `models/applicant_refuse_reason.py` |

### 2.2 Model moi (_name, can doi ten)

| Model hien tai | Model de xuat |
| --- | --- |
| `interview.schedule` | `x_psm_interview_schedule` |
| `hr.job.email.rule` | `x_psm_job_email_rule` |
| `hr.applicant.oje.evaluation` | `x_psm_applicant_oje_evaluation` |
| `hr.applicant.oje.evaluation.section` | `x_psm_applicant_oje_evaluation_section` |
| `hr.applicant.oje.evaluation.line` | `x_psm_applicant_oje_evaluation_line` |
| `hr.applicant.interview.evaluation` | `x_psm_applicant_interview_evaluation` |
| `hr.applicant.interview.evaluation.section` | `x_psm_applicant_interview_evaluation_section` |
| `hr.applicant.interview.evaluation.line` | `x_psm_applicant_interview_evaluation_line` |
| `applicant.get.refuse.reason.line` | `x_psm_applicant_get_refuse_reason_line` |

## 3. Phase 2 - Inventory XML ID

### 3.1 Action ID mapping

| Action ID hien tai | Action ID de xuat |
| --- | --- |
| `action_create_job_templates_wizard` | `action_psm_create_job_templates_wizard` |
| `action_interview_schedule` | `action_psm_interview_schedule` |
| `hr_applicant_oje_evaluation_action` | `action_psm_applicant_oje_evaluation` |

### 3.2 View ID mapping

| View ID hien tai | View ID de xuat |
| --- | --- |
| `applicant_get_refuse_reason_view_form_inherit` | `view_psm_applicant_get_refuse_reason_view_form_inherit` |
| `hr_applicant_oje_evaluation_view_form` | `view_psm_hr_applicant_oje_evaluation_view_form` |
| `hr_applicant_oje_evaluation_view_form_edit` | `view_psm_hr_applicant_oje_evaluation_view_form_edit` |
| `hr_applicant_oje_evaluation_view_list` | `view_psm_hr_applicant_oje_evaluation_view_list` |
| `hr_recruitment_stage_form_inherit` | `view_psm_hr_recruitment_stage_form_inherit` |
| `hr_recruitment_stage_tree_inherit` | `view_psm_hr_recruitment_stage_tree_inherit` |
| `survey_question_form_inherit_mandatory` | `view_psm_survey_question_form_inherit_mandatory` |
| `survey_survey_form_inherit_flags` | `view_psm_survey_survey_form_inherit_flags` |
| `survey_user_input_view_form_inherit_ui_clean` | `view_psm_survey_user_input_view_form_inherit_ui_clean` |
| `view_applicant_filter_recruitment_type` | `view_psm_applicant_filter_recruitment_type` |
| `view_applicant_kanban_recruitment_type` | `view_psm_applicant_kanban_recruitment_type` |
| `view_create_job_templates_wizard_form` | `view_psm_create_job_templates_wizard_form` |
| `view_hr_applicant_application_result_popup` | `view_psm_hr_applicant_application_result_popup` |
| `view_hr_applicant_form_hide_send_interview_store` | `view_psm_hr_applicant_form_hide_send_interview_store` |
| `view_hr_applicant_form_inherit` | `view_psm_hr_applicant_form_inherit` |
| `view_hr_applicant_kanban_no_sample` | `view_psm_hr_applicant_kanban_no_sample` |
| `view_hr_job_form_inherit` | `view_psm_hr_job_form_inherit` |
| `view_hr_job_form_inherit_applications_button` | `view_psm_hr_job_form_inherit_applications_button` |
| `view_hr_job_search_inherit` | `view_psm_hr_job_search_inherit` |
| `view_interview_schedule_form` | `view_psm_interview_schedule_form` |
| `view_interview_schedule_kanban` | `view_psm_interview_schedule_kanban` |

Ghi chu: `view_applicant_filter_recruitment_type` va `view_applicant_kanban_recruitment_type` dang nam trong `views/applicant_search_view.xml` nhung file nay chua duoc load trong `__manifest__.py`, nen chua them XML ID alias trong batch nay de tranh loi `ref()` khi upgrade.

### 3.3 Security group ID mapping

| Group ID hien tai | Group ID de xuat |
| --- | --- |
| `group_store_manager` | `group_gdh_ops_0204_crw` |
| `group_operations_manager` | `group_gdh_ops_0204_mgr` |

## 4. Inventory gap field naming (tong quan)

So lieu quet nhanh tu cac file model:

| File model | Tong field custom | Field chua theo `x_psm_*` |
| --- | --- | --- |
| `models/applicant_refuse_reason.py` | 10 | 10 |
| `models/hr_applicant.py` | 97 | 97 |
| `models/hr_applicant_interview_evaluation.py` | 38 | 36 |
| `models/hr_applicant_oje_evaluation.py` | 61 | 60 |
| `models/hr_job.py` | 17 | 15 |
| `models/hr_job_email_rule.py` | 7 | 7 |
| `models/hr_recruitment_stage.py` | 4 | 4 |
| `models/interview_schedule.py` | 23 | 23 |
| `models/survey_survey.py` | 14 | 6 |
| `models/survey_user_input.py` | 2 | 2 |

Chi tiet mapping field nam trong file:
- `FIELD_RENAME_MAPPING_0204.md`

## 5. External dependency risk (truoc Phase 6)

### 5.1 Model `interview.schedule`

Dang duoc tham chieu boi module ngoai `M02_P0204`:

- `M02_P0204_01`
- `M02_P0205`

Neu doi ten model nay, can migration cross-module bat buoc.

### 5.2 Cac model OJE/Interview evaluation

Hien thay tham chieu chu yeu noi bo trong `M02_P0204` (models, controllers, views, ACL). Risk thap hon so voi `interview.schedule`, nhung van can migration data + `res_model`.

## 6. De xuat thu tu thuc thi an toan

1. Security ID + action/view ID (co migration XML ID alias).
2. Field rename tren model goc (co `oldname` + migration script).
3. Model rename cho model noi bo truoc.
4. Model `interview.schedule` de cuoi cung, sau khi lock cross-module regression test.
