# Danh Sách Model Module 0205

Tài liệu này liệt kê các model mà module `M02_P0205_00` đang sử dụng, chia thành 2 nhóm:

- Các model kế thừa từ model sẵn có của Odoo
- Các model được tạo mới trong module `0205`

## 1. Các model kế thừa dùng sẵn của Odoo

### `calendar.event`

- File: `models/calendar.py`
- Mục đích: mở rộng lịch phỏng vấn.
- Bổ sung:
  - `round2_notification_sent`
  - `round3_notification_sent`
  - `round4_notification_sent`
  - `interview_round`
- Có override `default_get` để tự động thêm partner của người tạo vào cuộc họp.

### `hr.applicant`

- File: `models/hr_applicant.py`
- File: `models/recruitment_plan.py` có thêm một phần mở rộng `hr.applicant`
- Mục đích: mở rộng hồ sơ ứng viên cho quy trình tuyển dụng Văn phòng.
- Bổ sung các nhóm chức năng:
  - survey pre-interview
  - duyệt hồ sơ và tài liệu
  - sắp lịch nhiều vòng phỏng vấn
  - phiếu đánh giá phỏng vấn
  - offer, signed, chuyển trạng thái
  - nguồn ứng viên, kỹ năng, interviewer, meeting

### `hr.job`

- File: `models/hr_job.py`
- Mục đích: mở rộng Job Position phục vụ tuyển dụng Văn phòng.
- Bổ sung:
  - `survey_id`
  - `job_intro`
  - `responsibilities`
  - `must_have`
  - `nice_to_have`
  - `whats_great`
  - `current_employee_count`
  - `needed_recruitment`
  - `is_office_job`
- Có thêm logic đăng tin lên website/portal và gán interviewer mặc định.

### `hr.recruitment.stage`

- File: `models/hr_recruitment_stage.py`
- Mục đích: giữ compatibility với pipeline recruitment.
- Hiện tại file này chỉ kế thừa model, không khai báo thêm field mới.

### `mail.activity`

- File: `models/mail_activity.py`
- Mục đích: mở rộng logic khi hoàn thành activity.
- Override `action_done()` để nếu activity liên quan `hr.applicant` và có nội dung CV PASS thì tự động đánh dấu `cv_checked`.

### `res.company`

- File: `models/res_company.py`
- Mục đích: bổ sung cấu hình CEO theo công ty.
- Bổ sung field:
  - `ceo_id`

### `survey.survey`

- File: `models/survey_ext.py`
- Mục đích: đánh dấu survey được dùng cho pre-interview.
- Bổ sung field:
  - `is_pre_interview`

### `survey.question.answer`

- File: `models/survey_ext.py`
- Mục đích: đánh dấu đáp án/kiểu tiêu chí trong bài test.
- Bổ sung field:
  - `is_must_have`
  - `is_nice_to_have`

## 2. Các model được tạo mới trong module 0205

### `recruitment.request.approver`

- File: `models/recruitment_request.py`
- Mục đích: lưu danh sách manager/người duyệt cho Yêu cầu tuyển dụng.
- Vai trò:
  - liên kết với `recruitment.request`
  - lưu phòng ban, manager, user, trạng thái duyệt, ngày duyệt, ghi chú

### `recruitment.request`

- File: `models/recruitment_request.py`
- Mục đích: quản lý Yêu cầu tuyển dụng.
- Vai trò:
  - lưu nhu cầu cần tuyển
  - đi qua các bước `draft -> hr_validation -> ceo_approval -> in_progress -> done/cancel`
  - gửi activity cho HR/CEO
  - publish job lên website

### `recruitment.request.line`

- File: `models/recruitment_request.py`
- Mục đích: lưu từng dòng vị trí cần tuyển trong Yêu cầu.
- Vai trò:
  - tách theo phòng ban, job, số lượng, thời gian dự kiến, lý do

### `recruitment.plan`

- File: `models/recruitment_plan.py`
- Mục đích: quản lý Kế hoạch tuyển dụng tổng và Kế hoạch con.
- Vai trò:
  - lập kế hoạch tổng
  - tách kế hoạch con theo phòng ban
  - duyệt qua manager, HR, CEO
  - liên kết với đợt tuyển dụng
  - theo dõi số lượng vị trí và tiến độ

### `recruitment.plan.line`

- File: `models/recruitment_plan.py`
- Mục đích: lưu chi tiết từng vị trí trong Kế hoạch.
- Vai trò:
  - lưu job, phòng ban, số lượng, thời gian cần tuyển
  - lưu trạng thái dòng
  - tính funnel:
    - `applicant_count`
    - `interview_count`
    - `hired_count`

### `recruitment.batch`

- File: `models/recruitment_plan.py`
- Mục đích: quản lý Đợt tuyển dụng.
- Vai trò:
  - gom các vị trí đã duyệt vào một đợt
  - gửi CEO duyệt đợt
  - mở đợt, đóng đợt, xem ứng viên trong đợt
  - auto publish khi đến ngày bắt đầu

### `hr.applicant.evaluation`

- File: `models/hr_applicant.py`
- Mục đích: phiếu đánh giá phỏng vấn theo từng vòng.
- Vai trò:
  - lưu người phỏng vấn, vòng phỏng vấn, tổng điểm, nhận xét
  - đồng bộ kết quả về `hr.applicant`
  - hỗ trợ quyết định ứng viên qua vòng

### `hr.applicant.evaluation.line`

- File: `models/hr_applicant.py`
- Mục đích: các dòng tiêu chí chấm điểm trong một phiếu đánh giá.
- Vai trò:
  - lưu nhóm tiêu chí, mã tiêu chí, điểm, ghi chú
  - hỗ trợ mẫu đánh giá có cấu trúc

## 3. Tóm tắt nhanh

### Model kế thừa của Odoo

- `calendar.event`
- `hr.applicant`
- `hr.job`
- `hr.recruitment.stage`
- `mail.activity`
- `res.company`
- `survey.survey`
- `survey.question.answer`

### Model tạo mới trong module 0205

- `recruitment.request.approver`
- `recruitment.request`
- `recruitment.request.line`
- `recruitment.plan`
- `recruitment.plan.line`
- `recruitment.batch`
- `hr.applicant.evaluation`
- `hr.applicant.evaluation.line`
