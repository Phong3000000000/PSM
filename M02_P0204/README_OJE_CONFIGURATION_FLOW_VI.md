# Tai Lieu Luong Cau Hinh Va Danh Gia OJE (Tieng Viet)

Tai lieu nay tong hop toan bo phan mo rong lien quan OJE trong module M02_P0204: model moi, model mo rong, field chinh, action, controller, route va luong runtime.

## 1) Pham Vi Chuc Nang

Thiet ke OJE hien tai tach thanh 3 tang:

1. Tang template mac dinh (master): cau truc chuan dung lai theo scope.
2. Tang cau hinh theo Job Position: nap tu master va cho phep tuy bien theo tung job.
3. Tang snapshot danh gia ung vien: ban chup cau hinh tai thoi diem danh gia, khong phu thuoc viec cau hinh bi sua sau do.

Scope duoc ho tro:

1. store_staff
2. store_management
3. legacy (fallback cho du lieu cu)

## 2) Model Moi Da Them

## 2.1 recruitment.oje.template

Muc dich:

1. Luu mau OJE mac dinh theo tung scope.

Field chinh:

1. name
2. scope
3. active
4. version
5. intro_html
6. section_ids

Method chinh:

1. action_preview_oje_form: mo man hinh preview cua template.

## 2.2 recruitment.oje.template.section

Muc dich:

1. Quan ly section trong template mac dinh.

Field chinh:

1. template_id
2. scope (related)
3. name
4. sequence
5. section_kind
6. objective_text
7. hint_html
8. behavior_html
9. is_active
10. line_ids
11. line_count (compute)

## 2.3 recruitment.oje.template.line

Muc dich:

1. Quan ly cau hoi/task trong tung section cua template.

Field chinh:

1. section_id
2. template_id (related)
3. scope (related)
4. sequence
5. line_kind
6. question_text
7. is_required
8. active

Hanh vi:

1. create co normalize de tu suy ra line_kind theo section_kind khi can.

## 2.4 hr.job.oje.config.section

Muc dich:

1. Cau hinh section OJE theo tung Job Position.

Field chinh:

1. job_id
2. sequence
3. is_active
4. name
5. section_kind
6. objective_text
7. hint_html
8. behavior_html
9. scope
10. rating_mode
11. is_from_master
12. source_template_section_id
13. line_ids
14. line_count (compute)

## 2.5 hr.applicant.oje.evaluation.section

Muc dich:

1. Snapshot section trong phieu danh gia OJE cua ung vien.

Field chinh:

1. evaluation_id
2. source_config_section_id
3. sequence
4. name
5. section_kind
6. scope
7. rating_mode
8. objective_text
9. hint_html
10. behavior_html
11. is_active
12. section_rating
13. line_ids

## 2.6 hr.applicant.oje.evaluation.line

Muc dich:

1. Snapshot line va cau tra loi trong phieu danh gia.

Field quan trong:

1. template_line_id
2. question_text
3. line_kind
4. scope
5. rating_mode
6. staff_rating
7. management_score
8. yes_no_answer
9. line_comment
10. awarded_score

## 3) Model Da Mo Rong

## 3.1 hr.job

Muc dich:

1. Chua cau hinh OJE theo job.
2. Dong bo tu template mac dinh.
3. Tu dong nap cau hinh mac dinh khi tao job moi (4 tab).

Field OJE chinh:

1. oje_pass_score
2. oje_evaluator_user_id
3. oje_config_section_ids
4. oje_config_line_ids

Method OJE chinh:

1. _get_oje_template_scope
2. _get_oje_rating_mode
3. _archive_oje_master_records_other_scopes
4. action_load_default_oje_template
5. _sync_default_oje_template
6. action_preview_oje_form

Auto bootstrap khi create:

1. create goi _bootstrap_default_configuration_on_create.
2. Tu dong load default cho:
3. action_load_default_fields
4. action_load_default_refuse_reasons
5. action_load_default_email_rules
6. action_load_default_oje_template (chi job store)

## 3.2 hr.job.oje.config.line

Muc dich:

1. Chuan hoa line theo section de add line nhanh va dung kieu.

Method chinh:

1. _derive_line_kind_from_section
2. _derive_field_type_from_line_kind
3. _normalize_vals_with_section
4. create (override)
5. write (override)

## 3.3 hr.applicant

Muc dich:

1. Kiem tra quyen danh gia OJE.
2. Tao va lam moi snapshot danh gia.
3. Mo form OJE noi bo.
4. Ap ket qua pass/fail vao stage tuyen dung.

Field OJE chinh:

1. oje_evaluator_user_id
2. oje_evaluation_id
3. oje_evaluation_state
4. can_backend_evaluate_oje
5. oje_template_scope (related)
6. oje_staff_decision (related)
7. oje_management_overall_rating (related)
8. oje_fail_reason

Method OJE chinh:

1. _compute_can_backend_evaluate_oje
2. _check_backend_oje_access
3. _get_oje_snapshot_source
4. _populate_oje_evaluation_snapshot
5. _ensure_oje_evaluation
6. action_open_backend_oje_evaluation
7. action_apply_oje_evaluation_result

## 3.4 hr.applicant.oje.evaluation

Muc dich:

1. Luu phieu danh gia OJE, validate va tinh ket qua theo scope.

Field chinh:

1. template_scope
2. template_version
3. staff_decision
4. staff_ni_count, staff_gd_count, staff_ex_count, staff_os_count
5. management_overall_rating
6. management_final_display
7. total_score
8. result
9. fail_reason
10. submitted_at

Method chinh:

1. _validate_before_submit
2. action_submit
3. _compute_total_score
4. _compute_result

## 4) Controller Va Route Dang Dung

## 4.1 backend_oje.py

Muc dich:

1. Render form OJE noi bo (staff/management).
2. Submit va luu ket qua.
3. Cung cap preview read-only cho template va job.

Method core:

1. _get_evaluation_with_access
2. _prepare_render_values
3. _write_common_header_values
4. _write_staff_answers
5. _write_management_answers
6. _friendly_error_message
7. _prepare_oje_preview_values

Route:

1. /recruitment/oje/internal/<evaluation_id>
2. /recruitment/oje/internal/<evaluation_id>/submit
3. /recruitment/oje/template-preview/<template_id>
4. /recruitment/oje/job-preview/<job_id>

## 4.2 portal_recruitment.py

Muc dich:

1. Giu luong portal danh sach/start, nhung ep store scope vao form OJE moi.

Method va route chinh:

1. _get_dm_oje_applicants
2. _should_use_internal_oje_form
3. /my/oje-evaluation/start/<applicant_id>
4. /my/recruitment/oje/<applicant_id> (legacy fallback)
5. /my/recruitment/oje/submit (legacy fallback)

## 5) View Va UI Da Chinh

File UI OJE chinh:

1. views/recruitment_oje_template_views.xml
2. views/hr_job_application_field_views.xml
3. views/backend_oje_templates.xml
4. views/hr_applicant_views.xml
5. views/portal_recruitment_templates.xml

Diem thay doi UX noi bat:

1. Nut Pass OJE o header Applicant.
2. Cau hinh theo section, co line_count de theo doi so cau.
3. Nut Preview o form template mac dinh va tab OJE cua Job.
4. Form OJE staff/management noi bo.
5. Preview read-only de xem cau truc form.

## 6) Data, Asset, Manifest

Data:

1. data/oje_master_template_data.xml: seed template mac dinh cho store_staff va store_management.

Asset:

1. static/src/js/oje_backend_staff.js
2. static/src/scss/oje_backend.scss

Manifest da dang ky:

1. views/recruitment_oje_template_views.xml
2. views/backend_oje_templates.xml
3. data/oje_master_template_data.xml
4. web.assets_frontend cho OJE JS/SCSS

## 7) Security Va Quyen

ACL lien quan:

1. hr.job.oje.config.section
2. hr.job.oje.config.line
3. recruitment.oje.template
4. recruitment.oje.template.section
5. recruitment.oje.template.line
6. hr.applicant.oje.evaluation
7. hr.applicant.oje.evaluation.section
8. hr.applicant.oje.evaluation.line

Kiem tra quyen runtime:

1. _check_backend_oje_access tren hr.applicant (admin, evaluator, portal manager fallback).
2. backend controller validate quyen truoc khi render/submit.

## 8) Luong End-to-End

## 8.1 Luong Cau Hinh

1. Cau hinh template mac dinh theo scope o menu Configuration.
2. Job Position nap default tu template active.
3. Nguoi dung tuy bien section/line theo tung job.

## 8.2 Luong Danh Gia

1. Tu Applicant bam Pass OJE.
2. He thong _ensure_oje_evaluation de tao/refresh snapshot.
3. Render form theo template_scope.
4. Submit validate du lieu bat buoc.
5. Tinh ket qua va update stage ung vien.

## 8.3 Luong Preview

1. Preview tu template mac dinh: route template-preview.
2. Preview tu Job: route job-preview.
3. Preview chi de xem cau truc, khong luu ket qua danh gia.

## 9) Cron

Khong co cron OJE moi duoc them trong dot mo rong nay.

## 10) Tuong Thich Nguoc

1. Legacy survey va route cu van duoc giu de khong vo du lieu cu.
2. Store scope duoc dieu huong dan sang route OJE noi bo moi.

## 11) Danh Sach File Chinh

1. models/recruitment_oje_template.py
2. models/hr_job_oje_config.py
3. models/hr_job.py
4. models/hr_applicant.py
5. models/hr_applicant_oje_evaluation.py
6. controllers/backend_oje.py
7. controllers/portal_recruitment.py
8. views/recruitment_oje_template_views.xml
9. views/hr_job_application_field_views.xml
10. views/backend_oje_templates.xml
11. views/hr_applicant_views.xml
12. views/portal_recruitment_templates.xml
13. data/oje_master_template_data.xml
14. security/ir.model.access.csv
15. __manifest__.py
