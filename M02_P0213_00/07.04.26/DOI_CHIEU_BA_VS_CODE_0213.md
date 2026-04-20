# Đối chiếu BA và code hiện tại của `M02_P0213_00`

**Ngày cập nhật**: 2026-04-07  
**Phạm vi**: Đối chiếu theo các hạng mục trong bảng BA mà người dùng cung cấp, so với code runtime hiện tại của module `0213`.

## Kết luận nhanh

- Module `0213` hiện **có nhiều điểm lệch BA** nếu BA thật sự yêu cầu mô hình nghiệp vụ dựa trên `hr.employee.offboard` với state machine riêng.
- Tuy nhiên, một số mục trong bảng **không phải lỗi kỹ thuật**, mà là khác lựa chọn kiến trúc.
- `0213` hiện đang được xây trên hướng:
  - kế thừa `approval.request`
  - dùng `approval.category`
  - dùng `mail.activity` + `survey.user_input`
  - dùng portal + approval flow có sẵn của Odoo

---

## Bảng đối chiếu

| Hạng mục | BA yêu cầu | Code hiện tại của `0213` | Kết luận | Mức độ ảnh hưởng |
|---|---|---|---|---|
| Model | `hr.employee.offboard` | Kế thừa `approval.category`, `approval.request`, `mail.activity`, `survey.user_input` | **Lệch BA** | Cao |
| States | 10 state riêng: `confirmed`, `done`, `draft`, `handover`, `notifying`, `offboarding`, `payment_processing`, `pending_approval`, `processing`, `recruiting` | Không có state machine riêng; chỉ mở rộng `request_status` của `approval.request`, thêm `done` | **Lệch BA** | Cao |
| Server Actions | Có các action theo luồng BA như `action_confirm`, `action_create_payment`, `action_refuse`, `action_submit` | Có một số action nghiệp vụ khác, nhưng thiếu nhiều action BA nêu | **Lệch BA** | Cao |
| Computed Fields | Nên có computed fields cho dữ liệu dẫn xuất | Có nhiều computed fields | **Đạt** | Thấp |
| Constraints | Nên có validation constraints | Có constraint nhưng còn ít | **Có nhưng mỏng** | Trung bình |
| Views | Tối thiểu `form`, `list`, `search` | Có form/list và portal template, chưa thấy `search view` riêng | **Thiếu một phần** | Trung bình |
| Security (ACL) | Có `ir.model.access.csv` + security groups | Có ACL và record rule, nhưng chưa có group nghiệp vụ riêng của `0213` | **Thiếu một phần** | Trung bình |
| Email Templates | BA yêu cầu 2 template | Code hiện có 5 template | **Đủ, thậm chí nhiều hơn** | Thấp |
| Approval Workflow | BA yêu cầu 2 bước duyệt | Chưa thấy custom workflow 2 bước riêng; đang dựa nhiều vào `approval.request` | **Lệch BA** | Cao |
| Code Density | LOC/Field ratio mục tiêu `< 50` | Code runtime chính khá dày | **Cần lưu ý** | Trung bình |

---

## Phân tích chi tiết từng mục

### 1. Model

**BA yêu cầu**
- Model gốc là `hr.employee.offboard`

**Code hiện tại**
- Module `0213` không tạo model mới bằng `_name`
- Module đang kế thừa các model:
  - `approval.category`
  - `approval.request`
  - `mail.activity`
  - `survey.user_input`

**File liên quan**
- `models/resignation_request.py`
- `models/mail_activity.py`
- `models/survey_user_input.py`

**Kết luận**
- Đây là **lệch kiến trúc rõ ràng** so với BA nếu BA bắt buộc phải dùng `hr.employee.offboard`.
- Nếu BA chỉ quan tâm nghiệp vụ offboarding, còn cho phép tận dụng `approval.request`, thì đây là khác giải pháp chứ chưa chắc là sai.

---

### 2. States

**BA yêu cầu**
- Có 10 states riêng:
  - `confirmed`
  - `done`
  - `draft`
  - `handover`
  - `notifying`
  - `offboarding`
  - `payment_processing`
  - `pending_approval`
  - `processing`
  - `recruiting`

**Code hiện tại**
- `0213` không có state machine riêng kiểu model nghiệp vụ độc lập
- Chỉ mở rộng `request_status` của `approval.request`
- Có thêm state `done`
- Luồng thực tế hiện bám trên:
  - `pending`
  - `approved`
  - `refused`
  - `done`
  - `cancel`

**File liên quan**
- `models/resignation_request.py`
- `views/resignation_request_views.xml`
- `views/resignation_portal_template.xml`

**Kết luận**
- **Lệch BA rõ ràng**
- Nếu cần bám BA thật, gần như phải thiết kế lại workflow hoặc đổi nền tảng model

---

### 3. Server Actions

**BA yêu cầu**
- Có các action:
  - `action_approve`
  - `action_confirm`
  - `action_create_payment`
  - `action_done`
  - `action_refuse`
  - `action_submit`

**Code hiện tại**
- Có các action custom như:
  - `action_approve`
  - `action_done`
  - `action_send_exit_survey`
  - `action_send_social_insurance`
  - `action_send_adecco_notification`
  - `action_manual_reminder_extension`
  - `action_rehire`
  - `action_blacklist`
  - `action_launch_plan`
- Không thấy:
  - `action_confirm`
  - `action_create_payment`
  - `action_refuse`
  - `action_submit`

**Kết luận**
- **Lệch BA**
- Đây là khác ở mặt hành vi hệ thống, không chỉ là naming

---

### 4. Computed Fields

**BA yêu cầu**
- Nên có computed fields cho dữ liệu dẫn xuất

**Code hiện tại**
- Có nhiều computed fields, ví dụ:
  - `_compute_type_contract`
  - `_compute_all_activities_completed`
  - `_compute_exit_survey_completed`
  - `_compute_owner_related_activity_ids`
  - `_compute_employee_activity_ids`
  - `_compute_employee_id`

**Kết luận**
- **Đạt**

---

### 5. Constraints

**BA yêu cầu**
- Nên có validation constraints

**Code hiện tại**
- Có ít nhất 1 constraint ở `survey_user_input`
- Nhưng số lượng validation constraint ở tầng model chính còn khá ít

**Kết luận**
- **Có nhưng còn mỏng**
- Không phải không có, nhưng chưa thể xem là mạnh theo góc nhìn BA nghiệp vụ

---

### 6. Views

**BA yêu cầu**
- Tối thiểu có:
  - `form`
  - `list`
  - `search`

**Code hiện tại**
- Có:
  - form inherit cho `approval.request`
  - form inherit cho `approval.category`
  - list bên trong form
  - portal template
- Chưa thấy `search view` riêng

**Kết luận**
- **Thiếu một phần**

---

### 7. Security (ACL)

**BA yêu cầu**
- Có `ir.model.access.csv` và security groups

**Code hiện tại**
- Có `ir.model.access.csv`
- Có record rule cho portal ở `security/security.xml`
- Dùng group chuẩn của Odoo:
  - `base.group_user`
  - `base.group_portal`
- Chưa thấy group nghiệp vụ riêng kiểu:
  - `group_offboarding_user`
  - `group_offboarding_manager`
  - tương tự

**Kết luận**
- **Thiếu một phần**
- Về mặt kỹ thuật không thiếu security hoàn toàn, nhưng thiếu tầng group nghiệp vụ riêng nếu BA yêu cầu

---

### 8. Email Templates

**BA yêu cầu**
- Có 2 template

**Code hiện tại**
- Có 5 template:
  - exit survey
  - adecco notification
  - social insurance
  - offboarding reminder
  - department offboarding reminder

**Kết luận**
- **Đủ**
- Không phải lỗi

---

### 9. Approval Workflow

**BA yêu cầu**
- Workflow 2 bước duyệt

**Code hiện tại**
- Chưa thấy custom workflow 2 bước riêng trong code `0213`
- Module hiện tận dụng cơ chế approval sẵn có của `approval.request`
- Có override `action_approve()`, nhưng không thấy dựng rõ flow 2 bước nghiệp vụ như BA mô tả

**Kết luận**
- **Lệch BA**

---

### 10. Code Density

**BA yêu cầu**
- LOC/Field ratio mục tiêu `< 50`

**Code hiện tại**
- Các file runtime chính hiện có số dòng xấp xỉ:
  - `models/resignation_request.py`: 877
  - `models/mail_activity.py`: 120
  - `models/survey_user_input.py`: 89
  - `controllers/main.py`: 185
- Tổng xấp xỉ: `1271 LOC`

**Kết luận**
- Code khá dày so với phạm vi field hiện có
- Đây là **cảnh báo kiến trúc/bảo trì**, không phải lỗi runtime ngay lập tức

---

## Kết luận cuối

Nếu lấy bảng BA làm chuẩn tuyệt đối, thì `0213` hiện đang có các lệch chính sau:

- Sai nền tảng model nghiệp vụ
- Thiếu state machine riêng theo BA
- Thiếu nhiều server action BA yêu cầu
- Chưa có search view riêng
- Chưa có security group nghiệp vụ riêng
- Chưa thể hiện rõ approval workflow 2 bước

Các mục không phải lỗi hoặc đang ổn:

- Computed fields: có
- Email templates: đủ
- Constraints: có nhưng còn ít

## Khuyến nghị bước tiếp theo

Có 2 hướng xử lý:

### Hướng 1 - Giữ kiến trúc hiện tại
- Tiếp tục dùng `approval.request` làm lõi
- Cập nhật lại tài liệu BA/FS cho khớp với code thực tế
- Chỉ bổ sung các phần còn thiếu nhẹ như:
  - `search view`
  - security group riêng
  - tài liệu workflow

### Hướng 2 - Bám BA tuyệt đối
- Thiết kế lại module theo model `hr.employee.offboard`
- Dựng state machine riêng
- Tạo lại server actions theo BA
- Rà toàn bộ view, security, workflow

Hướng 2 là một đợt refactor lớn, không còn là chỉnh sửa nhỏ trên code hiện tại.
