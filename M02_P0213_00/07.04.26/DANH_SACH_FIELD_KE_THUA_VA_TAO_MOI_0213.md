# Danh sách field kế thừa và field tạo mới của 0213

## Phạm vi kiểm tra

- Module: `M02_P0213_00`
- Thư mục đã quét: `models/`, `views/`
- Đối chiếu thêm: `security/ir.model.access.csv`
- Tiêu chí phân loại:
  - Field kế thừa từ model Odoo: field gốc đã có sẵn trên model của Odoo và được `0213` sử dụng trực tiếp hoặc mở rộng.
  - Field được tạo mới trong model gốc: field mới do `0213` bổ sung vào các model có sẵn của Odoo thông qua `_inherit`.
  - Field được tạo mới trong model mới: field thuộc các model khai báo bằng `_name`.

## 1. Field kế thừa từ các model của Odoo

Lưu ý: Tài liệu này không liệt kê toàn bộ field sẵn có của Odoo trên các model được kế thừa, mà chỉ liệt kê các field gốc được `0213` dùng trực tiếp trong Python hoặc XML.

### 1.1. Model `approval.category`

| Field gốc Odoo | Vai trò trong `0213` |
| --- | --- |
| `name` | Dùng để kiểm tra category nghỉ việc trong logic xử lý |
| `description` | Được kế thừa trên form view để chèn thêm field `is_offboarding` phía sau |

### 1.2. Model `approval.request`

| Field gốc Odoo | Vai trò trong `0213` |
| --- | --- |
| `name` | Dùng khi tạo đơn nghỉ việc từ portal |
| `category_id` | Xác định đơn có thuộc category nghỉ việc hay không |
| `request_status` | Field gốc được `0213` mở rộng thêm giá trị `done` bằng `selection_add` |
| `request_owner_id` | Dùng để xác định người tạo đơn, gửi mail, đối chiếu user/employee |
| `partner_id` | Dùng để liên kết với đối tác và suy ra nhân viên |
| `user_status` | Dùng trong điều kiện hiển thị/ẩn nút trên form |
| `has_access_to_request` | Được dùng làm mốc `xpath` để chèn thêm field vào form |
| `id` | Dùng trong domain/search và tạo activity liên quan đến đơn |

### 1.3. Model `mail.activity`

| Field gốc Odoo | Vai trò trong `0213` |
| --- | --- |
| `activity_type_id` | Hiển thị loại hoạt động trong checklist offboarding |
| `summary` | Dùng để tìm activity cần hoàn thành và hiển thị trên giao diện |
| `note` | Hiển thị mô tả công việc trong portal |
| `date_deadline` | Tính quá hạn, gia hạn deadline, hiển thị hạn xử lý |
| `user_id` | Xác định người phụ trách activity |
| `state` | Dùng để tính trạng thái hiển thị và hiển thị quá hạn |
| `res_model` | Xác định activity gắn với `approval.request` hay `hr.employee` |
| `res_id` | Xác định bản ghi đích của activity |
| `id` | Dùng cho thao tác mark done ngoài portal |

### 1.4. Model `survey.user_input`

| Field gốc Odoo | Vai trò trong `0213` |
| --- | --- |
| `survey_id` | Xác định đúng khảo sát nghỉ việc |
| `partner_id` | Tìm nhân viên tương ứng từ người trả lời khảo sát |
| `email` | Fallback để tìm nhân viên và gửi khảo sát |
| `state` | Kiểm tra khảo sát đã hoàn thành hay chưa |

### 1.5. Các model Odoo khác được tham chiếu bằng field gốc

| Model | Field gốc Odoo | Vai trò trong `0213` |
| --- | --- | --- |
| `hr.employee` | `name` | Hiển thị tên nhân viên |
| `hr.employee` | `parent_id` | Lấy line manager |
| `hr.employee` | `department_id` | Lấy phòng ban |
| `hr.employee` | `job_id` | Lấy chức vụ |
| `hr.employee` | `user_id` | Liên kết tài khoản người dùng |
| `hr.employee` | `work_contact_id` | Đối chiếu từ partner sang employee |
| `hr.employee` | `work_email` | Fallback đối chiếu employee theo email |
| `res.users` | `email` | Dùng trong gửi mail/đối chiếu |
| `res.users` | `partner_id` | Lấy partner của user |
| `res.users` | `active` | Vô hiệu hóa tài khoản khi hoàn tất nghỉ việc |

## 2. Field được tạo mới trong model gốc của Odoo

### 2.1. Trên model `approval.category`

| STT | Field | Kiểu field | Ghi chú |
| --- | --- | --- | --- |
| 1 | `is_offboarding` | `fields.Boolean` | Đánh dấu category là yêu cầu nghỉ việc/offboarding |

### 2.2. Trên model `approval.request`

| STT | Field | Kiểu field | Ghi chú |
| --- | --- | --- | --- |
| 1 | `resignation_reason` | `fields.Text` | Lý do nghỉ việc |
| 2 | `resignation_reason_id` | `fields.Many2one('hr.departure.reason')` | Loại nghỉ việc |
| 3 | `resignation_date` | `fields.Date` | Ngày nghỉ dự kiến |
| 4 | `employee_id` | `fields.Many2one('hr.employee')` | Nhân viên liên kết với đơn nghỉ việc |
| 5 | `resignation_employee_name` | `fields.Char` | Related field lấy tên nhân viên |
| 6 | `resignation_manager_name` | `fields.Char` | Related field lấy line manager |
| 7 | `resignation_department` | `fields.Char` | Related field lấy phòng ban |
| 8 | `job_id` | `fields.Many2one` | Related field lấy chức vụ |
| 9 | `employee_activity_ids` | `fields.Many2many('mail.activity')` | Danh sách activity offboarding của đơn và nhân viên |
| 10 | `exit_survey_completed` | `fields.Boolean` | Cờ đánh dấu đã hoàn thành khảo sát nghỉ việc |
| 11 | `all_activities_completed` | `fields.Boolean` | Cờ đánh dấu đã hoàn tất toàn bộ activity |
| 12 | `type_contract` | `fields.Char` | Loại hợp đồng, field compute |
| 13 | `resignation_owner_email` | `fields.Char` | Related field lấy email người yêu cầu |
| 14 | `is_plan_launched` | `fields.Boolean` | Đánh dấu đã launch plan |
| 15 | `adecco_notification_sent` | `fields.Boolean` | Đánh dấu đã gửi thông tin cho Adecco |
| 16 | `exit_survey_user_input_id` | `fields.Many2one('survey.user_input')` | Lưu bản ghi khảo sát đã dùng |
| 17 | `owner_related_activity_ids` | `fields.Many2many('mail.activity')` | Danh sách activity liên quan tới nhân viên/owner |
| 18 | `is_rehire` | `fields.Boolean` | Đánh dấu tái tuyển |
| 19 | `is_blacklisted` | `fields.Boolean` | Đánh dấu blacklist |

### 2.3. Trên model `mail.activity`

| STT | Field | Kiểu field | Ghi chú |
| --- | --- | --- | --- |
| 1 | `active` | `fields.Boolean` | Dùng để archive activity thay vì xóa hẳn |
| 2 | `ops_display_state` | `fields.Selection` | Trạng thái hiển thị riêng cho quy trình offboarding |

### 2.4. Trên model `survey.user_input`

Không có field mới nào được tạo trên model `survey.user_input`. Module `0213` chỉ override method `write()` và bổ sung logic xử lý.

### 2.5. Field gốc được mở rộng, không phải field mới

| Model | Field | Cách mở rộng |
| --- | --- | --- |
| `approval.request` | `request_status` | Thêm giá trị `done` bằng `selection_add` |

## 3. Field được tạo mới trong model mới

Không có.

Lý do: module `M02_P0213_00` không khai báo model mới bằng `_name`, nên không phát sinh field thuộc model mới.

## 4. Tổng hợp nhanh

- Số field gốc Odoo được `0213` dùng trực tiếp hoặc mở rộng: có, được liệt kê ở Mục 1
- Số field mới trên model gốc Odoo:
  - `approval.category`: 1 field
  - `approval.request`: 19 field
  - `mail.activity`: 2 field
  - `survey.user_input`: 0 field
- Tổng số field mới trên model gốc Odoo: **22 field**
- Số field mới trên model mới: **0 field**

## 5. Nguồn xác nhận

- `addons/M02_P0213_00/models/resignation_request.py`
- `addons/M02_P0213_00/models/mail_activity.py`
- `addons/M02_P0213_00/models/survey_user_input.py`
- `addons/M02_P0213_00/views/resignation_request_views.xml`
- `addons/M02_P0213_00/views/resignation_portal_template.xml`
