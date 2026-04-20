# Danh sách field tạo mới của module 0213

## Kết luận

Module `M02_P0213_00` không tạo model mới, nhưng có bổ sung nhiều field mới trên các model có sẵn của Odoo thông qua `_inherit`.

Lưu ý: field `request_status` trong `approval.request` không phải field tạo mới. Module 0213 chỉ mở rộng field này bằng cách thêm lựa chọn `done`.

## 1. Field mới trên model `approval.category`

| Tên field | Kiểu field | File | Ghi chú |
| --- | --- | --- | --- |
| `is_offboarding` | `fields.Boolean` | `models/resignation_request.py` | Đánh dấu category là yêu cầu nghỉ việc/offboarding |

## 2. Field mới trên model `approval.request`

| Tên field | Kiểu field | File | Ghi chú |
| --- | --- | --- | --- |
| `resignation_reason` | `fields.Text` | `models/resignation_request.py` | Lý do nghỉ việc |
| `resignation_reason_id` | `fields.Many2one('hr.departure.reason')` | `models/resignation_request.py` | Loại nghỉ việc |
| `resignation_date` | `fields.Date` | `models/resignation_request.py` | Ngày nghỉ dự kiến |
| `is_rehire` | `fields.Boolean` | `models/resignation_request.py` | Đánh dấu tái tuyển |
| `is_blacklisted` | `fields.Boolean` | `models/resignation_request.py` | Đánh dấu blacklist |
| `employee_id` | `fields.Many2one('hr.employee')` | `models/resignation_request.py` | Nhân viên liên kết với đơn nghỉ việc, field compute/store |
| `resignation_employee_name` | `fields.Char` | `models/resignation_request.py` | Field related lấy tên nhân viên |
| `resignation_manager_name` | `fields.Char` | `models/resignation_request.py` | Field related lấy tên quản lý trực tiếp |
| `resignation_department` | `fields.Char` | `models/resignation_request.py` | Field related lấy phòng ban |
| `job_id` | `fields.Many2one` | `models/resignation_request.py` | Field related lấy chức vụ |
| `employee_activity_ids` | `fields.Many2many('mail.activity')` | `models/resignation_request.py` | Danh sách activity offboarding của đơn và nhân viên |
| `exit_survey_completed` | `fields.Boolean` | `models/resignation_request.py` | Đánh dấu đã hoàn thành khảo sát nghỉ việc |
| `all_activities_completed` | `fields.Boolean` | `models/resignation_request.py` | Đánh dấu đã hoàn thành toàn bộ activity |
| `type_contract` | `fields.Char` | `models/resignation_request.py` | Loại hợp đồng, field compute |
| `resignation_owner_email` | `fields.Char` | `models/resignation_request.py` | Field related lấy email người yêu cầu |
| `is_plan_launched` | `fields.Boolean` | `models/resignation_request.py` | Đánh dấu đã launch plan |
| `adecco_notification_sent` | `fields.Boolean` | `models/resignation_request.py` | Đánh dấu đã gửi thông báo Adecco |
| `exit_survey_user_input_id` | `fields.Many2one('survey.user_input')` | `models/resignation_request.py` | Lưu `user_input` dùng cho khảo sát nghỉ việc |
| `owner_related_activity_ids` | `fields.Many2many('mail.activity')` | `models/resignation_request.py` | Danh sách activity liên quan đến nhân viên/owner |

## 3. Field mới trên model `mail.activity`

| Tên field | Kiểu field | File | Ghi chú |
| --- | --- | --- | --- |
| `active` | `fields.Boolean` | `models/mail_activity.py` | Dùng để archive activity thay vì xóa |
| `ops_display_state` | `fields.Selection` | `models/mail_activity.py` | Trạng thái hiển thị riêng cho quy trình offboarding |

## 4. Model `survey.user_input`

Model `survey.user_input` trong module 0213 không có field mới. Module chỉ override method `write()` và bổ sung logic xử lý sau khi khảo sát hoàn tất.

## 5. Field có sẵn được mở rộng

| Model | Field | File | Cách mở rộng |
| --- | --- | --- | --- |
| `approval.request` | `request_status` | `models/resignation_request.py` | Thêm giá trị `done` bằng `selection_add` |

## Tổng số field mới

- `approval.category`: 1 field mới
- `approval.request`: 19 field mới
- `mail.activity`: 2 field mới
- `survey.user_input`: 0 field mới

Tổng cộng: **22 field mới**
