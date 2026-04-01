# Plan: Dùng Interviewers mặc định theo Job Position

## Mục tiêu

Thiết lập `Interviewers` trên `Job Position` như một danh sách mặc định có sẵn từ đầu cho từng job office.

Danh sách này sẽ được dùng để:

- xác định pool interviewer mặc định của job
- tự đẩy xuống applicant khi applicant ứng tuyển vào job đó
- tận dụng cơ chế phân quyền applicant theo `interviewer_ids` có sẵn của Odoo

## Quy tắc business đã chốt

`Interviewers` mặc định của job office gồm:

- trưởng phòng ban của job
- CEO của company
- toàn bộ user trong group `BOD Recruitment`
- toàn bộ user trong group `ABU Recruitment`

Hiểu theo nghiệp vụ:

- `Interviewers` là pool mặc định có sẵn trước các vòng phỏng vấn
- `primary interviewer` từng vòng vẫn là lớp riêng để chốt người phỏng vấn chính
- không dùng `Interviewers` để thay thế `primary_interviewer_l1..l4`

## Hướng triển khai

## Phase 1. Tạo mặc định Interviewers trên Job

### Mục tiêu

Khi tạo job office, field `interviewer_ids` được tự fill từ dữ liệu tổ chức.

### File chính

- `addons/M02_P0205_00/models/hr_job.py`

### Việc cần làm

- thêm helper lấy:
  - department manager user
  - company CEO user
  - user của group BOD
  - user của group ABU
- union các user trên thành danh sách `interviewer_ids`
- chỉ áp dụng cho `recruitment_type = office`

### Kết quả mong muốn

- job office mới tạo ra đã có `Interviewers`
- user không cần tự maintain tay danh sách này từ đầu

## Phase 2. Tự fill Interviewers khi chỉnh Job trên UI

### Mục tiêu

Khi user đổi `department`, `company` hoặc `recruitment_type` trên form job, hệ thống có thể fill `Interviewers` mặc định ngay trong UI.

### Việc cần làm

- thêm `onchange`
- chỉ fill khi `interviewer_ids` đang trống

### Kết quả mong muốn

- người dùng thấy ngay danh sách interviewer mặc định khi tạo job
- tránh ghi đè nếu đã chỉnh tay danh sách riêng

## Phase 3. Sync từ Job sang Applicant

### Mục tiêu

Applicant mới phải kế thừa `interviewer_ids` từ job.

### File chính

- `addons/M02_P0205_00/models/hr_applicant.py`

### Việc cần làm

- `onchange('job_id')`:
  - nếu applicant chưa có `interviewer_ids` thì fill từ `job.interviewer_ids`
- `create()`:
  - nếu tạo applicant từ backend/website mà chưa có `interviewer_ids`, tự copy từ job
- `write()`:
  - nếu đổi job mà applicant đang trống interviewer, tự copy từ job mới

### Kết quả mong muốn

- applicant nhìn thấy ngay danh sách interviewer của job
- không cần add tay từng hồ sơ

## Phase 4. Giữ nguyên flow primary interviewer

### Mục tiêu

Không làm vỡ flow phỏng vấn nhiều vòng hiện tại của `0205`.

### Giữ nguyên

- `primary_interviewer_l1_user_id`
- `primary_interviewer_l2_user_id`
- `primary_interviewer_l3_user_id`
- `primary_interviewer_l4_user_id`

### Ý nghĩa sau thay đổi

- `interviewer_ids` = pool mặc định có quyền và có thể tham gia
- `primary interviewer` = người chịu trách nhiệm chính cho từng vòng

## Phase 5. Rà UI và regression

### Mục tiêu

Đảm bảo dữ liệu mới hiển thị đúng và không ảnh hưởng flow cũ.

### Cần test

1. Tạo job office mới
- `Interviewers` phải tự có:
  - manager
  - CEO
  - BOD
  - ABU

2. Tạo applicant mới từ job đó
- applicant phải nhận `interviewer_ids` từ job

3. Tạo applicant khi job đã có interviewer
- không cần add tay interviewer ở applicant

4. Đổi job trên applicant đang trống interviewer
- applicant nhận interviewer của job mới

5. Flow nhiều vòng
- primary interviewer vẫn hoạt động như cũ
- không ảnh hưởng offer/activity/mail hiện tại

## Rủi ro cần lưu ý

- group BOD/ABU có thể đông, nên `Interviewers` của job có thể dài
- vì `interviewer_ids` gắn với quyền truy cập applicant, số user thấy được applicant sẽ rộng hơn trước
- nếu sau này business muốn chỉ một số BOD/ABU tham gia từng job, cần phase riêng để tùy biến sâu hơn

## Kết luận

Hướng này hợp lý hơn việc bắt user tự gán `Interviewers` cho từng job vì:

- có ý nghĩa rõ ràng
- có dữ liệu sẵn từ đầu
- applicant lấy được danh sách interviewer ngay khi gắn job
- không làm vỡ cơ chế `primary interviewer` đang chạy ổn trong `0205`
