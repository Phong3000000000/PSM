# Danh sách view được tạo mới của module 0213

## Kết luận

Module `M02_P0213_00` có các view được khai báo trong 2 file:

- `views/resignation_request_views.xml`
- `views/resignation_portal_template.xml`

Xét theo kỹ thuật Odoo, module có:

- 2 view backend dạng `ir.ui.view` kế thừa từ view có sẵn
- 1 QWeb template portal được tạo mới

Không thấy module tạo `menuitem` hay `ir.actions.act_window` mới trong phần view.

## 1. Danh sách tất cả view trong module

| XML ID | Tên view/template | Loại | Model | File | Ghi chú |
| --- | --- | --- | --- | --- | --- |
| `approval_request_resignation_view_form` | `approval.request.resignation.form` | `ir.ui.view` | `approval.request` | `views/resignation_request_views.xml` | View kế thừa form `approval.request` |
| `approval_category_resignation_view_form` | `approval.category.resignation.form` | `ir.ui.view` | `approval.category` | `views/resignation_request_views.xml` | View kế thừa form `approval.category` |
| `resignation_portal_template` | `Form yêu cầu nghỉ việc` | `QWeb template` | Portal | `views/resignation_portal_template.xml` | Template portal tạo mới |

## 2. View tạo mới hoàn toàn

Đây là view/template không dùng `inherit_id` để kế thừa trực tiếp từ một view khác.

| XML ID | Tên | Loại | File | Mô tả |
| --- | --- | --- | --- | --- |
| `resignation_portal_template` | `Form yêu cầu nghỉ việc` | `QWeb template` | `views/resignation_portal_template.xml` | Giao diện portal cho nhân viên gửi đơn nghỉ việc và theo dõi tiến trình nghỉ việc |

### Nội dung chính của `resignation_portal_template`

- Hiển thị form gửi yêu cầu nghỉ việc trên portal
- Hiển thị trạng thái đơn: `pending`, `approved`, `done`
- Hiển thị link khảo sát Exit Interview
- Hiển thị checklist activity offboarding cho portal user
- Cung cấp nút xác nhận hoàn thành activity ngay trên portal

## 3. View kế thừa/mở rộng từ view có sẵn

Các view dưới đây là XML record mới của module, nhưng về bản chất là view kế thừa từ module khác thông qua `inherit_id`.

| XML ID | Tên | Kế thừa từ | File | Mô tả |
| --- | --- | --- | --- | --- |
| `approval_request_resignation_view_form` | `approval.request.resignation.form` | `approvals.approval_request_view_form` | `views/resignation_request_views.xml` | Mở rộng form đơn phê duyệt để phục vụ quy trình nghỉ việc |
| `approval_category_resignation_view_form` | `approval.category.resignation.form` | `approvals.approval_category_view_form` | `views/resignation_request_views.xml` | Bổ sung field `is_offboarding` trên form category |

### Nội dung mở rộng chính của `approval_request_resignation_view_form`

- Chỉnh điều kiện hiển thị của nút `action_withdraw`
- Chỉnh điều kiện hiển thị của nút `action_cancel`
- Thêm các nút nghiệp vụ:
  - `action_send_social_insurance`
  - `action_send_adecco_notification`
  - `action_done`
  - `action_rehire`
  - `action_blacklist`
- Mở rộng `statusbar_visible` thành `new,pending,approved,done`
- Thêm các field ẩn như `employee_id`, `adecco_notification_sent`
- Thêm tab `Thông tin nghỉ việc`
- Thêm tab `Quá trình nghỉ việc`
- Thêm nút `action_view_survey_results` trong form

### Nội dung mở rộng chính của `approval_category_resignation_view_form`

- Thêm field `is_offboarding` vào form `approval.category`

## 4. Tổng hợp nhanh

- Tổng số view/template được khai báo trong module: **3**
- View backend kế thừa: **2**
- QWeb template tạo mới: **1**
- `menuitem` mới: **0**
- `ir.actions.act_window` mới trong phần view: **0**
