# Tech Specs — Module 0213 (`M02_P0213_00`)

Module: Quy trình nghỉ việc (Offboarding/Resignation) dựa trên `approvals` + Portal + Survey.

## Depends

Theo `__manifest__.py`:
- `base`
- `mail`
- `approvals`
- `hr`
- `portal`
- `survey`

Phụ thuộc thực tế trong code (không khai báo trong manifest):
- Tham chiếu XML ID thuộc module `M02_P0214_00` (survey + email template + approval category) trong:
  - `models/resignation_request.py`
  - `models/survey_user_input.py`
  - `controllers/main.py`

## Model

Các model được kế thừa/mở rộng:
- `approval.category` (thêm field đánh dấu offboarding)
- `approval.request` (mở rộng để trở thành “Đơn nghỉ việc” + checklist offboarding)
- `mail.activity` (thêm trạng thái hiển thị OPS + chặn xóa để archive)
- `survey.user_input` (hook khi khảo sát hoàn thành để auto hoàn tất activity + auto gửi email)

## Field

### `approval.category` (`models/resignation_request.py`)

- `is_offboarding` (`Boolean`)
  - Mục đích: đánh dấu category là quy trình nghỉ việc.
  - Default: `False`

### `approval.request` (inherit) (`models/resignation_request.py`)

Nhóm field nghiệp vụ nghỉ việc:
- `resignation_reason` (`Text`) — Lý do nghỉ việc
- `resignation_reason_id` (`Many2one: hr.departure.reason`) — Loại nghỉ việc
- `resignation_date` (`Date`) — Ngày nghỉ dự kiến

Nhóm state/flag:
- `request_status` (`Selection` của `approval.request`, `selection_add=[('done','Done')]`)
- `is_rehire` (`Boolean`, default `False`, `copy=False`)
- `is_blacklisted` (`Boolean`, default `False`, `copy=False`)
- `is_plan_launched` (`Boolean`, default `False`, `copy=False`) — đã launch/schedule checklist
- `adecco_notification_sent` (`Boolean`, default `False`, `copy=False`) — đã gửi Adecco

Liên kết nhân sự (chuẩn hoá):
- `employee_id` (`Many2one: hr.employee`, `compute`, `store=True`) — suy ra từ `partner_id.work_contact_id` hoặc `request_owner_id.user_id`

Field related hiển thị:
- `resignation_employee_name` (`Char`, related `employee_id.name`, readonly)
- `resignation_manager_name` (`Char`, related `employee_id.parent_id.name`, readonly)
- `resignation_department` (`Char`, related `employee_id.department_id.name`, readonly)
- `job_id` (`Many2one`, related `employee_id.job_id`, readonly)
- `resignation_owner_email` (`Char`, related `request_owner_id.email`, readonly)

Checklist/Survey:
- `employee_activity_ids` (`Many2many: mail.activity`, `compute`, `compute_sudo=True`, `context={'active_test': False}`)
  - Nội dung: tổng hợp activity trên cả `approval.request` và `hr.employee` (kể cả `active=False`)
- `exit_survey_completed` (`Boolean`, `compute`, `compute_sudo=True`, `store=False`)
  - Nội dung: kiểm tra `survey.user_input(state='done')` của exit survey theo email/partner
- `all_activities_completed` (`Boolean`, `compute`, `store=False`)
  - Nội dung: đếm pending activity (`active=True`) trên request + employee, và chỉ True khi `is_plan_launched=True` và pending_count = 0
- `type_contract` (`Char`, `compute`, `store=False`)
  - Nội dung: lấy loại HĐ từ `employee.contract_id.contract_type_id` hoặc fallback `employee.contract_type_id`
- `exit_survey_user_input_id` (`Many2one: survey.user_input`, `copy=False`)
  - Mục đích: lưu `user_input` để Portal dùng link khảo sát

Field computed phục vụ debug (hiện không thấy dùng trong view module 0213):
- `owner_related_activity_ids` (`Many2many: mail.activity`, `compute`) — các activity của `hr.employee` theo `res_id`

### `mail.activity` (inherit) (`models/mail_activity.py`)

- `active` (`Boolean`, default `True`) — dùng để archive thay vì xóa (trong bối cảnh checklist OPS)
- `ops_display_state` (`Selection`, compute)
  - `pending`: `active=True` và chưa quá hạn
  - `overdue`: `active=True` và `date_deadline < today`
  - `done`: `active=False`

### `survey.user_input` (inherit) (`models/survey_user_input.py`)

Không thêm field; override `write()` để bắt sự kiện `state -> done`.

## State

### `approval.request.request_status`

Module chỉ “mở rộng” selection bằng state:
- `done` — được set bởi `action_done()` khi hoàn tất checklist + exit survey

Luồng trạng thái chính (dựa trên `approvals` core):
- `new` → `pending` (Portal submit gọi `action_confirm()`)
- `pending` → `approved` (manager approve)
- `approved` → `done` (nhấn “Hoàn thành nghỉ việc” sau khi đủ điều kiện)
- `pending/approved` → `refused` (từ approvals)
- `*` → `cancel` (bị chặn theo điều kiện riêng cho category nghỉ việc)

### `mail.activity`

- Dùng `active` để biểu diễn “đã done” (archive) thay vì xóa.
- `ops_display_state` là trạng thái hiển thị trên view checklist.

### `survey.user_input.state`

- Khi `state='done'`, module tự mark done activity “Hoàn thành Exit Interview” (gắn trên `hr.employee`).

## View

### Backend

`views/resignation_request_views.xml`
- `approval_request_resignation_view_form` (inherit `approvals.approval_request_view_form`)
  - Chỉnh điều kiện hiển thị nút `action_withdraw`, `action_cancel` để chặn rút/hủy khi đơn nghỉ việc đã `approved/refused`.
  - Thêm nút header:
    - `action_send_social_insurance` (ẩn/hiện theo `type_contract`, `all_activities_completed`, `request_status`)
    - `action_send_adecco_notification` (ẩn/hiện theo `type_contract`, `exit_survey_completed`, `adecco_notification_sent`)
    - `action_done` (ẩn/hiện theo checklist + survey + adecco/bhxh)
    - `action_rehire`, `action_blacklist` (sau khi `request_status='done'`)
  - Thêm page:
    - “Thông tin nghỉ việc”: hiển thị thông tin nhân sự + lý do/ngày nghỉ
    - “Quá trình nghỉ việc”: list `employee_activity_ids` (readonly), dùng `ops_display_state` dạng badge
- `approval_category_resignation_view_form` (inherit `approvals.approval_category_view_form`)
  - Thêm field `is_offboarding` (boolean_toggle)

### Portal

`views/resignation_portal_template.xml`
- Template `M02_P0213_00.resignation_portal_template`
  - GET hiển thị form submit hoặc trạng thái + checklist (activity) + link survey (nếu có)
  - POST submit tạo `approval.request` + approver là line manager (nếu có)
  - POST mark activity done: gọi feedback cho `mail.activity` nếu activity thuộc user hiện tại

## API

### HTTP Controllers (Portal)

`controllers/main.py`
- `GET /my/resignation/ops`
  - Hiển thị form hoặc trạng thái đơn gần nhất của user theo category `approval_category_resignation`
  - Lấy activities trên `approval.request` (with `active_test=False`) để hiển thị checklist
  - Tạo `survey.user_input` nếu cần và dựng `survey_url`
- `POST /my/resignation/ops/activity/done`
  - Mark done 1 activity (chỉ khi `activity.user_id == current_user`)
- `POST /my/resignation/submit`
  - Tạo `approval.request` (sudo), set approver là line manager, gọi `action_confirm()` để chuyển sang Submitted/Pending

### Model methods (RPC / buttons / automation)

`models/resignation_request.py` (trên `approval.request`)
- Override:
  - `action_withdraw()`, `action_cancel()` — chặn rút/hủy với category nghỉ việc khi đã `approved/refused`
  - `action_approve()` — khi approve category nghỉ việc: gửi exit survey + schedule checklist từ activity plan + set `is_plan_launched=True`
- Buttons:
  - `action_send_exit_survey()` — tạo `survey.user_input` và gửi email template (gắn link survey)
  - `action_send_social_insurance()` — gửi email BHXH (hr.employee) và gọi `action_done()`
  - `action_send_adecco_notification()` — gửi email cho Adecco và set `adecco_notification_sent=True`
  - `action_done()` — set `request_status='done'`, deactivate user (portal/internal) và auto feedback các To-Do còn lại của request owner
  - `action_rehire()`, `action_blacklist()` — set cờ và post message
  - `action_manual_reminder_extension()` — nhắc nhở + gia hạn thủ công các activity quá hạn (tương tự cron)
- Compute helpers:
  - `_compute_employee_id()`, `_compute_employee_activity_ids()`, `_compute_exit_survey_completed()`, `_compute_all_activities_completed()`, `_compute_type_contract()`

`models/mail_activity.py` (trên `mail.activity`)
- Override:
  - `unlink()` — chặn xóa activity liên quan offboarding OPS, thay bằng `active=False` (archive)
  - `_action_done()` — sau khi mark done, trigger recompute checklist ở `approval.request`

`models/survey_user_input.py` (trên `survey.user_input`)
- Override:
  - `write()` — khi survey `state='done'`: mark done activity “Hoàn thành Exit Interview”; có logic auto gửi email BHXH khi mọi activity offboarding đã hoàn tất

## Crons

`data/ir_cron_data.xml`
- `ir_cron_offboarding_reminder`
  - Model: `approval.request`
  - Code: `model._cron_send_offboarding_reminders()`
  - Schedule: mỗi `3 days`

`models/resignation_request.py`
- `_cron_send_offboarding_reminders()`:
  - Quét các đơn nghỉ việc `request_status='approved'`
  - Lọc các `mail.activity(active=True)` quá hạn (`date_deadline < today`) trên cả request + employee
  - Gửi email reminder theo người phụ trách:
    - Nếu là request owner: template employee
    - Nếu là user khác (IT/HR/manager...): template dept, gửi tới email của user phụ trách
  - Gia hạn due date các activity quá hạn thêm `+4 days`

## Access

`security/ir.model.access.csv`
- Portal (`base.group_portal`):
  - `approval.request`: read=1, create=1, write=0, unlink=0
  - `mail.activity`: read=1
  - `hr.employee`: read=1
  - `survey.survey`, `survey.question`, `survey.question.answer`: read=1
  - `survey.user_input`: read=1, write=1, create=1, unlink=0
  - `hr.contract.type`, `hr.departure.reason`: read=1
- Internal (`base.group_user`):
  - Quyền read/write/create/unlink cho `approval.request`, `mail.activity`, `survey.user_input`
  - `hr.employee`: read/write (không create/unlink)

## Notes (rủi ro kỹ thuật / điểm cần xác nhận)

- Module load data có survey + email template với XML ID `M02_P0213_00.*` nhưng code/controllers lại tham chiếu nhiều đến `M02_P0214_00.*` → cần xác nhận hệ thống chạy theo 0213 hay 0214, và bổ sung `depends` nếu bắt buộc.
- Một số đoạn code có dấu hiệu typo/missing import (vd `resignation_employee_id`, `timedelta`) — có thể gây lỗi runtime nếu flow chạm tới.
- So khớp category bằng `category_id.name == "Yêu cầu nghỉ việc "` (có khoảng trắng cuối) trong `action_withdraw/action_cancel` là brittle; nên ưu tiên so khớp bằng XML ID (`env.ref`).

