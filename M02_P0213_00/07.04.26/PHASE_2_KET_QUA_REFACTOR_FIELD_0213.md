# Phase 2 - Kết quả refactor field module 0213

## 1. Phạm vi đã thực hiện

Phase 2 đã triển khai các hạng mục sau:

- Đổi tên field mới trên model gốc sang chuẩn `x_psm_0213_*`
- Cập nhật tham chiếu field tương ứng trong:
  - Python model
  - controller
  - file `views/main.py`
  - XML view
  - QWeb portal template
  - email template có dùng field của `approval.request`
- Thống nhất các tham chiếu survey/email từ `M02_P0214_00` về `M02_P0213_00`

## 2. Kết quả chính

### Đã đổi tên field

- `approval.category`
  - `is_offboarding` -> `x_psm_0213_is_offboarding`

- `approval.request`
  - `resignation_reason` -> `x_psm_0213_resignation_reason`
  - `resignation_reason_id` -> `x_psm_0213_resignation_reason_id`
  - `resignation_date` -> `x_psm_0213_resignation_date`
  - `employee_id` -> `x_psm_0213_employee_id`
  - `resignation_employee_name` -> `x_psm_0213_resignation_employee_name`
  - `resignation_manager_name` -> `x_psm_0213_resignation_manager_name`
  - `resignation_department` -> `x_psm_0213_resignation_department`
  - `job_id` -> `x_psm_0213_job_id`
  - `employee_activity_ids` -> `x_psm_0213_employee_activity_ids`
  - `exit_survey_completed` -> `x_psm_0213_exit_survey_completed`
  - `all_activities_completed` -> `x_psm_0213_all_activities_completed`
  - `type_contract` -> `x_psm_0213_type_contract`
  - `resignation_owner_email` -> `x_psm_0213_resignation_owner_email`
  - `is_plan_launched` -> `x_psm_0213_is_plan_launched`
  - `adecco_notification_sent` -> `x_psm_0213_adecco_notification_sent`
  - `exit_survey_user_input_id` -> `x_psm_0213_exit_survey_user_input_id`
  - `owner_related_activity_ids` -> `x_psm_0213_owner_related_activity_ids`
  - `is_rehire` -> `x_psm_0213_is_rehire`
  - `is_blacklisted` -> `x_psm_0213_is_blacklisted`

- `mail.activity`
  - `ops_display_state` -> `x_psm_0213_ops_display_state`

### Không đổi tên trong Phase 2

- `approval.request.request_status`
  - giữ nguyên, vì đây là field gốc Odoo chỉ được mở rộng `selection_add`

- `mail.activity.active`
  - không đổi tên
  - đã xác minh đây là field gốc của Odoo, không phải field custom của `0213`

## 3. Lỗi kỹ thuật được sửa kèm trong Phase 2

- Sửa tham chiếu nhầm `self.resignation_employee_id` thành field đúng đang dùng theo logic mới
- Bổ sung import `timedelta` trong `models/resignation_request.py`
- Đồng bộ reference survey/email từ `0214` về `0213`

## 4. File đã chỉnh sửa trong Phase 2

- `addons/M02_P0213_00/models/resignation_request.py`
- `addons/M02_P0213_00/models/mail_activity.py`
- `addons/M02_P0213_00/models/survey_user_input.py`
- `addons/M02_P0213_00/controllers/main.py`
- `addons/M02_P0213_00/views/main.py`
- `addons/M02_P0213_00/views/resignation_request_views.xml`
- `addons/M02_P0213_00/views/resignation_portal_template.xml`
- `addons/M02_P0213_00/data/email_template_dept_offboarding_reminder.xml`

## 5. Kiểm tra đã thực hiện

- Đã chạy `py_compile` cho các file Python chính của phase này
- Kết quả: pass syntax Python

## 6. Việc còn lại cho phase sau

- Phase 3:
  - tiếp tục chuẩn hóa `xml id` theo kế hoạch
- Phase 4 trở đi:
  - tách logic
  - dọn controller trùng
  - rà security
  - kiểm thử hồi quy theo checklist Phase 1
