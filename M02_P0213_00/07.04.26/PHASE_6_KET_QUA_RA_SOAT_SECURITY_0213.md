# PHASE 6 - KẾT QUẢ RÀ SOÁT SECURITY MODULE 0213

## 1. Mục tiêu Phase 6

Phase 6 tập trung rà soát và siết lại các điểm rủi ro bảo mật chính của module `0213`, ưu tiên:

- quyền truy cập portal trên các model nhạy cảm
- độ an toàn của các route portal đang dùng `sudo()`
- giới hạn phạm vi dữ liệu mà portal user có thể thao tác

Trong bối cảnh triển khai trên DB sạch, mục tiêu là giảm bề mặt tấn công nhưng vẫn không làm gãy luồng nghỉ việc hiện có.

## 2. Rủi ro chính được xác định

### 2.1. Quyền portal đang mở rộng trên nhiều model không thật sự cần thiết

File `security/ir.model.access.csv` ban đầu cấp quyền portal cho:

- `approval.request`
- `mail.activity`
- `hr.employee`
- `hr.contract.type`
- `hr.departure.reason`

Trong khi luồng portal hiện tại của module chủ yếu thao tác qua controller dùng `sudo()`, nên việc mở trực tiếp các quyền model này cho portal là không cần thiết và làm tăng rủi ro đọc dữ liệu ngoài phạm vi.

### 2.2. Route hoàn thành activity nhận `activity_id` trực tiếp từ form

Route:

- `/my/resignation/ops/activity/done`

Trước khi siết lại, logic chỉ kiểm tra:

- activity có tồn tại
- activity được gán cho user hiện tại

Điều này vẫn chưa đủ chặt, vì user có thể gửi tay một `activity_id` hợp lệ thuộc ngữ cảnh khác nhưng vẫn được giao cho chính họ.

### 2.3. `survey.user_input` của portal cần có ràng buộc rõ hơn

Portal vẫn cần quyền với `survey.user_input` để phục vụ luồng khảo sát, nhưng nếu không có rule giới hạn thì phạm vi nhìn thấy record sẽ quá rộng.

## 3. Thay đổi đã thực hiện

### 3.1. Bổ sung file rule security

Đã tạo file:

- `security/security.xml`

Nội dung chính:

- thêm rule `rule_psm_0213_survey_user_input_portal_own`
- giới hạn portal chỉ truy cập `survey.user_input` của chính mình theo:
  - `partner_id = user.partner_id`
  - hoặc `email = user.email`

### 3.2. Cập nhật manifest để nạp rule mới

Đã bổ sung:

- `security/security.xml`

vào danh sách `data` trong manifest.

### 3.3. Thu hẹp quyền portal không cần thiết trong `ir.model.access.csv`

Đã loại bỏ các quyền portal trên các model sau:

- `approval.request`
- `mail.activity`
- `hr.employee`
- `hr.contract.type`
- `hr.departure.reason`

Lý do:

- các luồng portal của module đang truy xuất các model này thông qua controller với `sudo()`
- không cần mở trực tiếp model access cho portal user
- giảm nguy cơ đọc dữ liệu qua ORM/RPC ngoài phạm vi luồng nghiệp vụ mong muốn

### 3.4. Siết route hoàn thành activity trên portal

Đã cập nhật `controllers/main.py`:

- thêm helper `_get_owned_resignation_request_by_id(request_id)`
- route `/my/resignation/ops/activity/done` giờ chỉ cho phép hoàn thành activity khi thỏa đồng thời:
  - activity tồn tại
  - activity thuộc `approval.request`
  - đơn `approval.request` đó thuộc chính `request_owner_id` hiện tại
  - activity được gán cho user hiện tại

Kết quả:

- chặn việc dùng `activity_id` ngoài phạm vi đơn nghỉ việc của chính user
- vẫn giữ nguyên trải nghiệm portal hiện tại đối với luồng hợp lệ

## 4. File đã tác động

- `__manifest__.py`
- `security/ir.model.access.csv`
- `security/security.xml`
- `controllers/main.py`

## 5. Kiểm tra sau thay đổi

Đã kiểm tra:

- file rule mới được tạo đúng
- manifest đã nạp `security/security.xml`
- controller compile thành công
- `py_compile` pass cho:
  - `controllers/main.py`
  - `models/resignation_request.py`
  - `models/mail_activity.py`
  - `models/survey_user_input.py`

## 6. Đánh giá kết quả

Phase 6 đã đạt các mục tiêu chính:

- giảm quyền portal trên các model nhạy cảm
- siết chặt route thao tác activity
- bổ sung ràng buộc nhìn thấy `survey.user_input` cho portal

Đây là một bước hardening thực tế, phù hợp với giả định cài mới DB và hướng thiết kế hiện tại của module.

## 7. Rủi ro còn lại / nội dung chuyển phase sau

- Chưa chạy kiểm thử cài module thực tế trên DB sạch sau thay đổi security
- Chưa xác minh end-to-end luồng survey portal dưới rule mới
- Một số đoạn model vẫn dùng `sudo()` khá nhiều; cần tiếp tục rà về nghiệp vụ và phạm vi dữ liệu ở các phase validate/regression

## 8. Kết luận

Phase 6 đã hoàn tất theo phạm vi hợp lý:

- quyền portal đã được thu hẹp đáng kể
- luồng thao tác nhạy cảm trên portal đã được siết điều kiện
- module sẵn sàng cho phase tiếp theo về dependency cleanup hoặc validate cài mới / regression test
