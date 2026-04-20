# Phase 1 - Baseline nghiệp vụ và checklist test refactor module 0213

## 1. Mục tiêu của Phase 1

Phase 1 dùng để đóng băng baseline nghiệp vụ hiện tại của module `M02_P0213_00` và tạo checklist test hồi quy để dùng xuyên suốt quá trình refactor.

Do giả định hiện tại là:

- sẽ xóa database
- cài lại module từ đầu sau refactor

nên Phase 1 tập trung vào:

- xác định luồng nghiệp vụ cần còn hoạt động
- xác định các điểm vào chính của người dùng
- xác định dữ liệu nền tối thiểu cần có
- tạo checklist test tay để kiểm tra sau mỗi phase

## 2. Baseline hiện tại của module

## 2.1. Chức năng chính

Module `0213` đang phục vụ quy trình nghỉ việc với các năng lực chính:

- Nhân viên gửi yêu cầu nghỉ việc từ portal
- Tạo `approval.request` thuộc category nghỉ việc
- Manager duyệt yêu cầu
- Sau khi duyệt, hệ thống tạo các activity offboarding
- Hệ thống gửi hoặc mở luồng khảo sát Exit Interview
- Người dùng có thể đánh dấu hoàn thành activity từ portal
- Hệ thống nhắc việc quá hạn qua cron
- Khi đủ điều kiện, hệ thống gửi BHXH hoặc Adecco
- Hệ thống hoàn tất quy trình nghỉ việc
- Có thao tác đánh dấu tái tuyển hoặc blacklist sau khi hoàn tất

## 2.2. Model đang tham gia trực tiếp

- `approval.category`
- `approval.request`
- `mail.activity`
- `survey.user_input`
- `hr.employee`
- `res.users`
- `mail.template`
- `mail.activity.plan`

## 2.3. Điểm vào chính của người dùng

### Portal

- Route xem form/trạng thái:
  - `/my/resignation/ops`
- Route submit yêu cầu:
  - `/my/resignation/submit`
- Route đánh dấu hoàn thành activity từ portal:
  - `/my/resignation/ops/activity/done`

### Backoffice

- Form `approval.request`
- Form `approval.category`
- Danh sách và form `survey.user_input`
- Cron nhắc việc offboarding

## 2.4. Dữ liệu nền được module nạp

Theo `__manifest__.py`, module đang nạp các nhóm dữ liệu sau:

- `security/ir.model.access.csv`
- category nghỉ việc
- survey exit interview
- email template khảo sát
- email template Adecco
- email template BHXH
- email template reminder
- cron nhắc việc
- offboarding activity plan
- view portal
- view form approval/category

## 3. Baseline nghiệp vụ theo luồng

## 3.1. Luồng 1 - Truy cập form nghỉ việc từ portal

### Kỳ vọng

- User portal truy cập được `/my/resignation/ops`
- Nếu chưa có đơn nghỉ việc thì thấy form tạo đơn
- Nếu đã có đơn gần nhất thì thấy trạng thái đơn hiện tại

### Điều kiện đầu vào

- User có tài khoản portal hoặc user liên kết với `hr.employee`
- `approval.category` nghỉ việc đã tồn tại

## 3.2. Luồng 2 - Gửi yêu cầu nghỉ việc

### Kỳ vọng

- Hệ thống tạo bản ghi `approval.request`
- `category_id` là category nghỉ việc
- `request_owner_id` là user hiện tại
- Có `approver_ids` nếu employee có line manager
- Đơn được `action_confirm()` và sang trạng thái chờ duyệt

### Dữ liệu đầu vào tối thiểu

- `hr.employee` có liên kết `user_id` hoặc `work_contact_id`
- Có `hr.departure.reason`
- Employee có `parent_id.user_id` để sinh approver

## 3.3. Luồng 3 - Duyệt yêu cầu nghỉ việc

### Kỳ vọng

- Manager duyệt đơn
- Nếu đúng category nghỉ việc:
  - hệ thống gọi luồng gửi khảo sát exit survey
  - hệ thống lấy plan offboarding
  - sinh các activity tương ứng
  - đánh dấu đã launch plan

### Điểm kiểm tra

- Có activity mới trên `approval.request`
- Có đúng số lượng task từ activity plan
- User phụ trách task được gán đúng

## 3.4. Luồng 4 - Khảo sát Exit Interview

### Kỳ vọng

- Khi đơn ở trạng thái `approved` hoặc `done` và chưa hoàn thành khảo sát:
  - portal có thể hiển thị link khảo sát
- Khi gửi khảo sát:
  - có `survey.user_input`
  - có thể lấy `start_url`
- Khi khảo sát hoàn thành:
  - hệ thống ghi nhận trạng thái hoàn thành
  - activity “Hoàn thành Exit Interview” được xử lý

### Rủi ro hiện tại cần nhớ khi test

- Code đang tham chiếu lẫn giữa tài nguyên `0213` và `0214`

## 3.5. Luồng 5 - Checklist offboarding trên portal

### Kỳ vọng

- Portal hiển thị các activity của đơn
- Hiển thị cả activity đang active và activity đã hoàn tất
- Người phụ trách đúng activity có thể bấm xác nhận hoàn thành
- Sau khi xác nhận:
  - activity được mark done
  - trạng thái checklist được cập nhật

## 3.6. Luồng 6 - Gửi BHXH / Adecco

### Kỳ vọng

- Nếu đủ điều kiện theo loại hợp đồng và trạng thái checklist:
  - có thể gửi BHXH hoặc Adecco
- Sau khi gửi:
  - các cờ trạng thái tương ứng được cập nhật
  - có thông báo thành công hoặc lỗi rõ ràng

### Điều kiện logic cần test

- `type_contract`
- `all_activities_completed`
- `exit_survey_completed`
- `adecco_notification_sent`

## 3.7. Luồng 7 - Hoàn tất nghỉ việc

### Kỳ vọng

- Chỉ hoàn tất được khi:
  - đã hoàn thành khảo sát
  - đã hoàn thành toàn bộ activity
- Sau khi hoàn tất:
  - `request_status` chuyển sang `done`
  - tài khoản user liên quan bị vô hiệu hóa nếu phù hợp
  - các activity To Do còn lại của request owner được hoàn tất

## 3.8. Luồng 8 - Tái tuyển / Blacklist

### Kỳ vọng

- Chỉ thao tác được khi đơn đã `done`
- Có thể đánh dấu:
  - tái tuyển
  - blacklist
- Sau thao tác:
  - field trạng thái được cập nhật
  - có notification hiển thị

## 3.9. Luồng 9 - Cron nhắc việc quá hạn

### Kỳ vọng

- Cron tìm các đơn nghỉ việc đã `approved`
- Tìm activity quá hạn còn active
- Gửi reminder theo đúng người phụ trách
- Gia hạn deadline thêm 4 ngày

### Điểm kiểm tra

- cron không lỗi khi không có dữ liệu
- cron không gửi cho user không có email
- deadline được cập nhật đúng

## 4. Dữ liệu test tối thiểu cần có sau khi cài mới DB

## 4.1. Master data

- Ít nhất 1 `approval.category` nghỉ việc
- Ít nhất 1 `hr.departure.reason`
- Ít nhất 1 survey exit interview
- Các email template của module
- Activity plan offboarding

## 4.2. User và employee

- 1 user nhân viên portal hoặc internal
- 1 employee liên kết với user trên
- 1 line manager có user
- 1 HR/internal user để thao tác backoffice

## 4.3. Điều kiện dữ liệu khuyến nghị

- Employee có:
  - `parent_id`
  - `job_id`
  - `department_id`
  - `work_contact_id`
  - `work_email`

## 5. Checklist test hồi quy

## 5.1. Checklist smoke test sau mỗi lần refactor

| STT | Hạng mục | Kết quả mong đợi |
| --- | --- | --- |
| 1 | Cài module thành công | Không lỗi loading XML, field, view, access |
| 2 | Mở portal nghỉ việc | Route `/my/resignation/ops` hoạt động |
| 3 | Submit đơn nghỉ việc | Tạo được `approval.request` |
| 4 | Mở form đơn ở backoffice | View không lỗi, field hiển thị đúng |
| 5 | Manager approve đơn | Không lỗi, activity được tạo |
| 6 | Mở lại portal sau approve | Thấy checklist và/hoặc link khảo sát |
| 7 | Mark done một activity từ portal | Activity đổi trạng thái đúng |
| 8 | Hoàn thành khảo sát | Hệ thống ghi nhận hoàn tất khảo sát |
| 9 | Gửi BHXH hoặc Adecco | Action chạy đúng theo điều kiện |
| 10 | Hoàn tất nghỉ việc | Đơn sang `done`, không lỗi nghiệp vụ |

## 5.2. Checklist chi tiết theo màn hình

### Portal nghỉ việc

- Mở được form khi chưa có đơn
- Hiển thị đúng thông tin employee
- Submit xong redirect về trang trạng thái
- Khi có đơn `pending`, hiển thị thông báo chờ duyệt
- Khi có đơn `approved`, hiển thị checklist
- Khi có đơn `done`, hiển thị thông báo hoàn tất

### Form `approval.request`

- Không lỗi inherited view
- Các nút hiển thị đúng điều kiện
- Các tab thông tin nghỉ việc và activity hiển thị đúng
- Field boolean/status hiển thị đúng giá trị

### Form `approval.category`

- Hiển thị field custom của module
- Không lỗi view inheritance

## 5.3. Checklist chi tiết theo logic

### Logic duyệt và tạo activity

- Approve đúng category thì mới sinh plan
- Plan sinh đủ task
- Task gán đúng user theo loại responsible

### Logic khảo sát

- Có thể tạo `survey.user_input`
- Có thể lấy được URL khảo sát
- Hoàn thành khảo sát thì cờ hoàn thành được cập nhật

### Logic hoàn tất

- Không cho `done` nếu chưa đủ điều kiện
- Cho `done` khi đủ điều kiện
- User liên quan bị disable đúng rule

### Logic reminder

- Cron chỉ lấy đơn `approved`
- Chỉ xử lý task quá hạn
- Gia hạn đúng 4 ngày

## 6. Rủi ro kỹ thuật phát hiện trong Phase 1

## 6.1. Tham chiếu survey không đồng nhất

Code hiện tại đang dùng lẫn:

- `M02_P0213_00.*`
- `M02_P0214_00.*`

Điều này là rủi ro lớn nhất của baseline hiện tại.

## 6.2. Trùng controller

Đang tồn tại cả:

- `controllers/main.py`
- `views/main.py`

Cần xử lý sớm để tránh baseline bị hiểu sai.

## 6.3. Khả năng có lỗi runtime hiện hữu

Qua đọc code có một số điểm cần lưu ý khi test thực tế:

- `action_send_social_insurance()` đang kiểm tra `self.resignation_employee_id`, trong khi field nhìn thấy trong model là `employee_id`
- Có sử dụng `timedelta(days=4)` nhưng chưa thấy import `timedelta` trong file model
- Các điểm này có thể gây lỗi runtime ngay cả trước khi bắt đầu refactor naming

## 7. Kết luận Phase 1

Phase 1 được xem là hoàn tất khi:

- đã có checklist test tay rõ ràng
- đã chốt được baseline nghiệp vụ hiện tại
- đã ghi nhận các điểm rủi ro cần theo dõi ở những phase sau

Với giả định cài mới DB sau refactor, checklist ở tài liệu này là đủ để dùng làm chuẩn kiểm tra cho các vòng refactor tiếp theo mà chưa cần xây migration test.
