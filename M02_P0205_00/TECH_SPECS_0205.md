# Tech Specs — Module 0205 (`M02_P0205_00`)

Module: Quy trình tuyển dụng Khối Văn Phòng (kế hoạch/batch/yêu cầu tuyển dụng) + website/portal job posting + khảo sát năng lực + nhiều vòng phỏng vấn.

## Depends

Theo `__manifest__.py`:
- Odoo core: `hr_recruitment`, `hr`, `mail`, `survey`, `approvals`, `portal`, `website_blog`
- Custom modules:
  - `M02_P0211_00` (Onboarding)
  - `M02_P0213_00` (Offboarding)
- (Đã tách) `recruitment_type` được đưa vào `M02_P0205_00` để chạy độc lập
  - `M02_P0200_00` (Department Block / Khối)
  - `portal_custom`

## Model

### Model mới (custom)
- `recruitment.request` — Yêu cầu tuyển dụng (đột xuất / theo kế hoạch)
- `recruitment.request.line` — Chi tiết vị trí trong YCTD (loại theo kế hoạch)
- `recruitment.request.approver` — Danh sách manager duyệt theo phòng ban cho YCTD
- `recruitment.plan` — Kế hoạch tuyển dụng (có parent/sub-plan theo phòng ban)
- `recruitment.plan.line` — Chi tiết vị trí trong kế hoạch + chỉ số funnel (applicant/interview/hired)
- `recruitment.batch` — Đợt tuyển dụng (gom các plan.line vào batch)
- `hr.applicant.evaluation` — Phiếu đánh giá phỏng vấn theo vòng

### Model kế thừa / mở rộng
- `hr.applicant` — thêm survey/interview/evaluation/offer fields + hành động gửi email/slot interview
- `hr.job` — thêm cấu hình survey + nội dung website + auto map `recruitment_type` theo “Khối”
- `survey.question.answer` — flag Must-have/Nice-to-have phục vụ auto đánh giá
- `survey.user_input` — hook khi nộp bài khảo sát để auto update status ứng viên
- `mail.activity` — hook khi “Done” activity để auto tick `cv_checked`
- `res.company` — cấu hình CEO user nhận activity duyệt kế hoạch

## Field

### `recruitment.request.approver` (`models/recruitment_request.py`)
- `request_id` (`Many2one: recruitment.request`, required, ondelete=cascade)
- `department_id` (`Many2one: hr.department`, required)
- `manager_id` (`Many2one: hr.employee`, required)
- `user_id` (`Many2one: res.users`, related `manager_id.user_id`, store, readonly)
- `status` (`Selection`: `new/approved/rejected`, default `new`, tracking)
- `approved_date` (`Datetime`, readonly)
- `notes` (`Text`)

### `recruitment.request` (`models/recruitment_request.py`)
- `name` (`Char`, sequence `recruitment.request`, readonly, default `New`)
- `batch_id` (`Many2one: recruitment.batch`, domain state=open)
- `request_type` (`Selection`: `unplanned/planned`, default `unplanned`)
- `job_id` (`Many2one: hr.job`)
- `department_id` (`Many2one: hr.department`)
- `quantity` (`Integer`, default 1)
- `date_start`, `date_end` (`Date`)
- `reason` (`Text`, required)
- `line_ids` (`One2many: recruitment.request.line`)
- `approver_ids` (`One2many: recruitment.request.approver`)
- `user_id` (`Many2one: res.users`, default current user)
- `company_id` (`Many2one: res.company`, default current company)
- `recruitment_plan_id` (`Many2one: recruitment.plan`, readonly)
- `state` (`Selection`: `draft/manager_approval/hr_validation/ceo_approval/in_progress/done/cancel`, default `draft`, tracking)
- `is_published` (`Boolean`, default False, copy=False)
- `can_approve_as_manager` (`Boolean`, compute) — user hiện tại có phải manager thuộc approver_ids ở bước manager_approval

### `recruitment.request.line` (`models/recruitment_request.py`)
- `request_id` (`Many2one: recruitment.request`, ondelete=cascade)
- `department_id` (`Many2one: hr.department`, required)
- `job_id` (`Many2one: hr.job`, required)
- `quantity` (`Integer`, default 1, required)
- `planned_date` (`Date`, required)
- `reason` (`Text`)

### `recruitment.plan` (`models/recruitment_plan.py`)
- `name` (`Char`, sequence `recruitment.plan`, readonly, default `New`)
- `line_ids` (`One2many: recruitment.plan.line`)
- `priority` (`Selection`: `0/1/2`, default `0`, tracking)
- `reason` (`Text`)
- `state` (`Selection`: `draft/waiting_manager/manager_approved/hr_validation/waiting_ceo/in_progress/done/cancel`, default `draft`, tracking)
- `company_id` (`Many2one: res.company`)
- `user_id` (`Many2one: res.users`)
- `request_count` (`Integer`)
- `job_count` (`Integer`, compute)
- `total_quantity` (`Integer`, compute, store)
- `batch_id` (`Many2one: recruitment.batch`)
- `date_submitted` (`Datetime`, readonly)
- `is_reminder_sent` (`Boolean`, default False)
- `can_approve_as_manager` (`Boolean`, compute) — chỉ manager của `department_id` (đối với sub-plan) mới duyệt được
- `parent_id` (`Many2one: recruitment.plan`)
- `sub_plan_ids` (`One2many: recruitment.plan`)
- `department_id` (`Many2one: hr.department`) — dùng cho sub-plan
- `is_sub_plan` (`Boolean`, default False)

### `recruitment.plan.line` (`models/recruitment_plan.py`)
- `plan_id` (`Many2one: recruitment.plan`, required, ondelete=cascade)
- `department_id` (`Many2one: hr.department`, required)
- `job_id` (`Many2one: hr.job`, required)
- `quantity` (`Integer`, default 1, required)
- `planned_date` (`Date`, required)
- `reason` (`Text`)
- `is_approved` (`Boolean`, default True) — line được giữ lại khi manager duyệt
- `state` (`Selection`: `draft/waiting_manager/manager_approved/hr_validation/waiting_ceo/in_progress/done/cancel`, default `draft`)
- `batch_id` (`Many2one: recruitment.batch`)
- `applicant_count`, `interview_count`, `hired_count` (`Integer`, compute) — metrics theo `job_id + department_id`
- `is_published` (`Boolean`, default False, copy=False)

### `recruitment.batch` (`models/recruitment_plan.py`)
- `name` (`Char`, sequence `recruitment.batch`, readonly, default `New`)
- `batch_name` (`Char`, required, tracking)
- `date_start`, `date_end` (`Date`, tracking)
- `state` (`Selection`: `draft/open/waiting_ceo/approved/closed`, default `draft`, tracking)
- `line_ids` (`One2many: recruitment.plan.line`)

### `hr.applicant` (inherit) (`models/hr_applicant.py`)

Survey (Step 9–11):
- `survey_sent` (`Boolean`, tracking)
- `survey_result_url` (`Char`) — link review kết quả

Phỏng vấn nhiều vòng:
- `interview_date_1..4` (`Datetime`, tracking)
- `interview_result_1..4` (`Selection` điểm 0–5, tracking)
- `interview_slot_token` (`Char`, copy=False)
- `interview_slot_event_id` (`Many2one: calendar.event`, copy=False)

Checklist/Offer:
- `cv_checked` (`Boolean`, default False, tracking)
- `offer_status` (`Selection`: `proposed/accepted/refused`, tracking)

Đánh giá phỏng vấn:
- `eval_l1_id..eval_l4_id` (`Many2one: hr.applicant.evaluation`, copy=False)

### `hr.applicant.evaluation` (`models/hr_applicant.py`)
- `applicant_id` (`Many2one: hr.applicant`, required, ondelete=cascade)
- `interview_round` (`Selection`: 1–4, required, tracking)
- `interviewer_id` (`Many2one: res.users`, default current user, tracking)
- `date` (`Date`, default today, tracking)
- `attitude_score`, `skill_score`, `experience_score`, `culture_fit_score` (`Selection` 1–5, default 3, tracking)
- `strengths`, `weaknesses`, `note` (`Text`, tracking)
- `recommendation` (`Selection`: `pass/fail/consider`, default `pass`, required, tracking)

### `hr.job` (inherit) (`models/hr_job.py`)
- `survey_id` (`Many2one: survey.survey`, domain `is_pre_interview=True`)
- `job_intro`, `responsibilities`, `must_have`, `nice_to_have`, `whats_great` (`Text`) — nội dung hiển thị website

Behavior:
- Auto map `recruitment_type` theo `department_id.block_id.code` (RST→office, OPS→store) khi `create()/write()`
- `_register_hook()` + `security/recruitment_security.xml` update rule `hr.hr_job_comp_rule` để cho phép đọc job `website_published=True` (bypass multi-company rule)

### `res.company` (inherit) (`models/res_company.py`)
- `ceo_user_id` (`Many2one: res.users`) — CEO nhận activity duyệt KHTN

### `survey.question.answer` (inherit) (`models/survey_ext.py`)
- `is_must_have` (`Boolean`, default False)
- `is_nice_to_have` (`Boolean`, default False)

### `survey.user_input` (inherit) (`models/survey_ext.py`)
- Override `_mark_done()`:
  - Nếu survey có scoring: tìm `hr.applicant` theo `survey_id` + `email/partner`
  - Auto update stage + message kết quả (PASS/CONSIDER/FAIL) dựa trên ngưỡng must-have (mặc định dùng `scoring_success_min` hoặc 80%)
  - FAIL: set `refuse_reason_id` và gửi template `email_candidate_survey_fail` nếu cấu hình
  - PASS: tạo activity To-Do cho manager để “kiểm tra CV”

### `mail.activity` (inherit) (`models/mail_activity.py`)
- Override `action_done()`:
  - Nếu activity thuộc `hr.applicant` và summary có “CV” + “PASS” → set `hr.applicant.cv_checked=True`

## State

### `recruitment.request.state`
- `draft` → `manager_approval` (`action_submit()`, tạo approver theo phòng ban)
- `manager_approval` → `hr_validation` (`action_manager_approve()`, khi tất cả approver approved, tạo activity To-Do cho HR)
- `hr_validation` → `ceo_approval` (`action_hr_validate()`)
- `ceo_approval` → `in_progress` (`action_ceo_approve()`, tăng `no_of_recruitment` và publish job)
- `in_progress` → `done` (`action_done()`)
- `*` → `cancel` (`action_reject()`), `cancel` → `draft` (`action_reset_draft()`)

### `recruitment.plan.state` (parent/sub-plan)
- `draft` → `waiting_manager` (`action_notify_department_heads()`, set `date_submitted`, tạo activity cho managers)
  - Nếu là parent plan: tự tạo sub-plan theo từng `department_id` và notify theo sub-plan
- `waiting_manager` → `manager_approved` (`action_manager_approve()`, duyệt theo department của sub-plan)
- `manager_approved` → `waiting_ceo` (`action_hr_validate()`, đồng bộ parent/sub + tạo activity cho CEO theo `res.company.ceo_user_id`)
- `waiting_ceo` → `in_progress` (`action_ceo_approve()`, đồng bộ parent/sub)
- `in_progress` → publish jobs (`action_publish_jobs()`) → `done` (`action_done()`)
  - `action_done()` kiểm tra đủ `hired_count >= quantity` cho từng line (đối với sub/standalone); parent plan chỉ Done khi mọi sub-plan done
- `*` → `cancel` (`action_cancel()`), `cancel` → `draft` (`action_reset_draft()`)

### `recruitment.batch.state`
- `draft/open` → `waiting_ceo` (`action_send_ceo()`, đồng bộ state các plan liên quan)
- `waiting_ceo` → `approved` (`action_ceo_approve_batch()`)
- `waiting_ceo` → reject (`action_ceo_reject_batch()`)
- `approved` → `closed` (`action_close()`), `closed` → `approved` (`action_reopen()`)

### `hr.applicant` stage (office)
Defined in `data/office_stages.xml` (office): `New`, `Screening`, `Interview 1..4`, `Offer`, `Probation`, `Hired`, `Reject`.
- Survey scoring xong có thể auto chuyển stage sang `stage_office_screening` (PASS/CONSIDER) hoặc `stage_office_reject` (FAIL).

## View

### Backend views
- `views/recruitment_request_views.xml`
  - Form/list cho `recruitment.request` + statusbar + buttons theo state
  - Notebook: approver list / line_ids (planned) / reason
  - Actions: unplanned/planned
  - Menu: “Tuyển dụng VP” → “Yêu cầu Tuyển dụng”
- `views/recruitment_request_approver_views.xml` — tree/form/action cho `recruitment.request.approver`
- `views/recruitment_plan_views.xml`
  - Form/list cho `recruitment.plan` + thống kê + buttons duyệt/publish/done
  - Form/list cho `recruitment.batch` + buttons send CEO/approve/close + view applicants + pull approved lines
  - Menu root `menu_office_recruitment_root` + menu Kế hoạch/Batches/Sub-plans
- `views/hr_job_views.xml` — thêm button “Đăng lên Portal” + tab “Nội dung Website” + survey_id
- `views/hr_applicant_views.xml` — thêm buttons/fields cho survey, interview, evaluation, offer
- `views/hr_applicant_block_actions.xml` — tạo actions/menus lọc applicant theo `recruitment_type` office/store
- `views/survey_views.xml` — thêm cột `is_must_have/is_nice_to_have` trên danh sách suggested answers
- `views/res_company_views.xml` — thêm `ceo_user_id` trên company form

### Portal / Website templates
- `views/portal_templates.xml`
  - Inherit portal home (`portal_custom.portal_my_home_inherit`) để thêm link `/my/jobs` và `/my/recruitment_requests`
  - Template danh sách jobs theo batch + unplanned requests
  - Template list “My Recruitment Requests”
- `views/job_portal_templates.xml`
  - Public job application form + upload CV
  - Thank-you page `/jobs/thankyou`
- `views/website_hr_recruitment_templates.xml`
  - Customize `website_hr_recruitment.thankyou` để show survey button theo `job.survey_id` (lấy job_id từ session)
  - Inherit job detail page để render theo các field website content của job
  - Templates confirm/invalid cho interview slot
- `views/website_thankyou_inherit.xml` — chỉnh wrap recruiter name/job title cho thankyou page

## API

### HTTP Controllers

`controllers/portal.py`
- `GET /my/jobs` (paged) — list jobs published (`hr.job.website_published=True`)
- `GET /my/recruitment_requests` (paged) — list YCTD của user portal

`controllers/job_portal.py`
- `GET /my/jobs` — list jobs publish theo `recruitment.plan.line` (plan in_progress + line approved) + YCTD đột xuất published
- `GET /jobs/detail/<line_id>` — job detail theo `recruitment.plan.line`
- `GET /jobs/request/detail/<request_id>` — job detail theo `recruitment.request` (unplanned)
- `POST /jobs/submit` — tạo `res.partner` + `hr.applicant` + attachment CV
- `GET /jobs/thankyou` — thank-you page

`controllers/interview_slot.py`
- `GET /interview/choose/<token>/<event_id>` — ứng viên chọn slot PV (ghi `interview_date_1` + `interview_slot_event_id`)

`controllers/website_recruitment.py`
- Override `WebsiteHrRecruitment.insert_record()`:
  - tạo `hr.applicant` với context `from_website=True`
  - lưu `job_id` vào session để thank-you page render đúng survey button

### Model methods (buttons / automation)

`models/recruitment_request.py`:
- `action_submit`, `action_manager_approve`, `_send_activity_to_hr`, `action_hr_validate`, `action_ceo_approve`, `action_publish_jobs`, `action_done`, `action_reject`, `action_open_job_page`, …

`models/recruitment_plan.py`:
- `action_notify_department_heads`, `_notify_department_heads`
- `action_manager_approve`, `action_hr_validate`, `_send_activity_to_ceo_for_approval`, `action_ceo_approve`
- `action_publish_jobs`, `action_done`
- `action_send_ceo`, `action_ceo_approve_batch`, `action_pull_approved_lines`, …

`models/hr_applicant.py`:
- `action_send_survey`, `action_invite_interview_l1..l4`
- `action_send_interview_slot_survey`, `get_interview_slot_url()`
- `action_start_eval_l1..l4` (mở/khởi tạo evaluation record)

## Crons

`data/ir_cron_data.xml`
- `ir_cron_remind_line_manager` (mỗi 1 phút): `recruitment.plan._cron_remind_manager()`
  - Nhắc manager nếu sub-plan ở `waiting_manager` quá 1 phút kể từ `date_submitted` và chưa nhắc (`is_reminder_sent=False`).
- `ir_cron_monthly_recruitment_notification` (mỗi 1 ngày): `recruitment.plan._cron_check_monthly_notification()`
  - Thông báo khi có `planned_date` rơi vào tháng hiện tại cho plan đang `in_progress`.
- `ir_cron_auto_publish_batches` (mỗi 1 phút): `recruitment.batch._cron_auto_publish_approved_batches()`
  - Khi batch `approved` và `today >= date_start`: set batch `open`, publish jobs, message_post thông báo.

## Access

`security/ir.model.access.csv` (tóm tắt)
- `base.group_user` và `hr_recruitment.group_hr_recruitment_manager`: full CRUD cho
  - `recruitment.request`, `recruitment.request.line`, `recruitment.request.approver`
  - `recruitment.plan`, `recruitment.plan.line`, `recruitment.batch`
  - `hr.applicant.evaluation`
- Read-only `survey.survey` cho `base.group_user` và `hr_recruitment.group_hr_recruitment_manager`

`security/recruitment_security.xml`
- Ghi đè domain của rule `hr.hr_job_comp_rule` để cho phép đọc jobs đã publish (`website_published=True`) bất kể company (phục vụ portal/website job listing).

## Notes (rủi ro kỹ thuật / điểm cần xác nhận)

- Route bị trùng: `/my/jobs` được khai báo ở cả `controllers/portal.py` và `controllers/job_portal.py` → cần xác nhận controller nào đang “đè” route trong runtime (phụ thuộc load order).
- `recruitment.batch.action_pull_approved_lines()` đang set `recruitment.plan.line.state='waiting'` nhưng selection của `recruitment.plan.line.state` không có giá trị `waiting` → có nguy cơ crash/invalid state khi chạy nút này.
- Update rule `hr.hr_job_comp_rule` được thực hiện cả trong `security/recruitment_security.xml` và trong `hr.job._register_hook()` → cần xác nhận có cần cả hai hay chỉ giữ một cơ chế.
