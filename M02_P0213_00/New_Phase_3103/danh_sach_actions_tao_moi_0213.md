# Danh sách action được tạo mới của module 0213

## Kết luận

Module `M02_P0213_00` không tạo record `ir.actions.act_window` hay `ir.actions.server` độc lập trong XML.

Các action mới của module 0213 chủ yếu gồm:

- 1 action hệ thống dạng `ir.cron`
- nhiều action dạng method `type="object"` gắn vào nút bấm trên form
- một số action runtime được trả về từ Python như `ir.actions.client` và `ir.actions.act_window`

## 1. Action hệ thống được tạo mới trong dữ liệu XML

| XML ID | Loại action | File | Mô tả |
| --- | --- | --- | --- |
| `ir_cron_offboarding_reminder` | `ir.cron` | `data/ir_cron_data.xml` | Cron tự động nhắc nhở các activity offboarding đang trễ hạn |

### Chi tiết

- `name`: `Offboarding: Remind Pending Activities`
- `model_id`: `approvals.model_approval_request`
- `state`: `code`
- `code`: `model._cron_send_offboarding_reminders()`
- `interval_number`: `3`
- `interval_type`: `days`

## 2. Action nút bấm `type="object"` được khai báo mới trên giao diện

Các action dưới đây được gắn vào form `approval.request` qua file `views/resignation_request_views.xml`.

| Tên method | Model | File | Mô tả |
| --- | --- | --- | --- |
| `action_send_social_insurance` | `approval.request` | `views/resignation_request_views.xml` | Gửi thông tin bảo hiểm xã hội |
| `action_send_adecco_notification` | `approval.request` | `views/resignation_request_views.xml` | Gửi thông tin nghỉ việc cho Adecco |
| `action_done` | `approval.request` | `views/resignation_request_views.xml` | Hoàn tất quy trình nghỉ việc |
| `action_rehire` | `approval.request` | `views/resignation_request_views.xml` | Đánh dấu nhân viên đủ điều kiện tái tuyển |
| `action_blacklist` | `approval.request` | `views/resignation_request_views.xml` | Đưa nhân viên vào blacklist |
| `action_view_survey_results` | `approval.request` | `views/resignation_request_views.xml` | Xem kết quả khảo sát nghỉ việc |

## 3. Action runtime được trả về từ Python

Đây là các action không được tạo thành record XML riêng, nhưng được method Python trả về để Odoo thực thi.

| Method | Kiểu action trả về | File | Mô tả |
| --- | --- | --- | --- |
| `action_send_adecco_notification` | `ir.actions.client` | `models/resignation_request.py` | Hiển thị thông báo thành công/lỗi sau khi gửi email Adecco |
| `action_send_social_insurance` | `ir.actions.client` | `models/resignation_request.py` | Hiển thị thông báo sau khi gửi email BHXH |
| `action_view_survey_results` | `ir.actions.act_window` hoặc `ir.actions.client` | `models/resignation_request.py` | Mở form/list kết quả khảo sát, hoặc báo không tìm thấy dữ liệu |
| `action_launch_plan` | `ir.actions.act_window` | `models/resignation_request.py` | Mở wizard Launch Plan của module `hr` với context nhân viên |
| `action_send_exit_survey` | `ir.actions.client` | `models/resignation_request.py` | Hiển thị thông báo sau khi gửi khảo sát nghỉ việc |
| `action_rehire` | `ir.actions.client` | `models/resignation_request.py` | Hiển thị thông báo và reload sau khi đánh dấu tái tuyển |
| `action_blacklist` | `ir.actions.client` | `models/resignation_request.py` | Hiển thị thông báo và reload sau khi đưa vào blacklist |
| `action_manual_reminder_extension` | `ir.actions.client` | `models/resignation_request.py` | Hiển thị thông báo kết quả nhắc nhở và gia hạn activity trễ hạn |

## 4. Method action nội bộ phục vụ nghiệp vụ

Các method dưới đây là action theo cách đặt tên trong Python, nhưng không thấy được gắn trực tiếp thành nút mới trong XML của module.

| Method | Model | File | Mô tả |
| --- | --- | --- | --- |
| `_cron_send_offboarding_reminders` | `approval.request` | `models/resignation_request.py` | Logic được cron gọi để nhắc nhở activity quá hạn |

## 5. Các action sẵn có được override, không phải action tạo mới

Đây là các action đã tồn tại từ trước trong Odoo hoặc module phụ thuộc, module 0213 chỉ ghi đè hành vi:

| Method | Model | File | Ghi chú |
| --- | --- | --- | --- |
| `action_withdraw` | `approval.request` | `models/resignation_request.py` | Override để chặn rút đơn sau khi đã approved/refused |
| `action_cancel` | `approval.request` | `models/resignation_request.py` | Override để chặn hủy đơn trong một số trạng thái |
| `action_approve` | `approval.request` | `models/resignation_request.py` | Override để tự động gửi survey và tạo offboarding activities |

## Tổng hợp nhanh

- Action record XML mới: **1**
- Action nút bấm `type="object"` mới trên giao diện: **6**
- Action runtime trả về từ Python: **8**
- Action override, không phải tạo mới: **3**
