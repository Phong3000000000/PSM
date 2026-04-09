# Office Job Actions File Map

Tài liệu này liệt kê các file trong module `M02_P0205_00` liên quan đến các thao tác trong luồng job office:

- mở `/office-jobs`
- bấm `Xem chi tiết và ứng tuyển`
- vào trang apply `/jobs/apply/<job_id>`
- gửi hồ sơ từ form ứng tuyển

## 1. File chính cho luồng public office jobs

### `controllers/job_portal.py`

- Route `/office-jobs`
- Route `/jobs/detail/<int:line_id>`
- Route `/jobs/request/detail/<int:request_id>`
- Route `/jobs/apply/<int:job_id>`
- Route `/jobs/submit`
- Tạo `office_job_public_list`
- Render trang apply `office_job_apply_custom`
- Gắn `line_id` / `request_id` để biết hồ sơ đến từ plan line hay recruitment request

Đây là file controller quan trọng nhất cho toàn bộ luồng trong ảnh.

### `views/job_portal_templates.xml`

- Template `office_job_public_list`
- Template `job_apply_template`
- Nút `Xem chi tiết và ứng tuyển`
- Form legacy gửi hồ sơ qua `/jobs/submit`

File này chứa giao diện danh sách job public và một form ứng tuyển cũ/legacy vẫn còn trong module.

### `views/website_hr_recruitment_templates.xml`

- Template `office_job_apply_custom`
- Template `office_job_apply_field_renderer`
- Form apply chính cho office job
- Hiển thị các block:
  - thông tin vị trí
  - lưu ý
  - nguồn tuyển dụng
  - các section form động
  - survey questions
- Nút `Gửi hồ sơ ứng tuyển`

Đây là template đang được controller `job_portal.py` render cho trang apply office job.

### `controllers/website_jobs_redirect.py`

- Route `/jobs`
- Nếu user public thì redirect sang `/office-jobs`

File này đảm bảo người ngoài vào `/jobs` sẽ thấy luồng office jobs thay vì website recruitment chuẩn.

## 2. File hỗ trợ nộp hồ sơ và tạo applicant

### `controllers/website_recruitment.py`

- Override `insert_record`
- Khi tạo `hr.applicant`, inject context `from_website=True`
- Lưu `job_id` vào session để thank-you page / survey có thể đọc lại đúng job

File này liên quan trực tiếp đến bước nộp hồ sơ website.

### `models/hr_applicant.py`

- Model mở rộng `hr.applicant`
- Logic create/write cho applicant
- Các field phục vụ survey, interview, trạng thái ứng viên
- Là nơi nhận dữ liệu sau khi hồ sơ được tạo

### `models/hr_job.py`

- Bổ sung/điều chỉnh hành vi `hr.job`
- Có các logic liên quan tới website job, survey, và dữ liệu hiển thị trên job detail/apply

File này là nền cho dữ liệu job được hiển thị ở front-end.

## 3. File liên quan đến thank-you và flow sau submit

### `views/website_thankyou_inherit.xml`

- Tùy biến trang thank-you của website recruitment

### `views/job_portal_templates.xml`

- Template `job_thankyou_template`

Trang cảm ơn sau khi gửi hồ sơ có thể đi qua một trong hai template trên, tùy nhánh controller đang chạy.

## 4. File cấu hình nạp module

### `__manifest__.py`

- Khai báo dependency:
  - `M02_P0204_00`
  - `hr_recruitment`
  - `portal`
  - `survey`
- Nạp các file controller/view phía trên

Nếu thiếu file này hoặc thiếu dependency, luồng office jobs sẽ không lên đúng trên website.

## 5. File portal liên quan nếu cần xem luồng đăng nhập

### `views/portal_templates.xml`

- Có các link tới `/jobs/detail/<line_id>` và `/jobs/request/detail/<request_id>`
- Liên quan đến khu vực portal cho user đăng nhập

### `controllers/portal.py`

- Route `/my/jobs`
- Route `/my/recruitment_requests`

File này không phải luồng public chính trong ảnh, nhưng liên quan nếu bạn kiểm tra phiên bản portal đã đăng nhập.

## 6. Tóm tắt nhanh theo thao tác

- Vào `/jobs` hoặc `/office-jobs`: `controllers/website_jobs_redirect.py`, `controllers/job_portal.py`, `views/job_portal_templates.xml`
- Xem card job và bấm chi tiết: `views/job_portal_templates.xml`, `controllers/job_portal.py`
- Mở trang apply: `controllers/job_portal.py`, `views/website_hr_recruitment_templates.xml`
- Bấm gửi hồ sơ: `views/website_hr_recruitment_templates.xml`, `controllers/job_portal.py`, `controllers/website_recruitment.py`
- Xử lý applicant sau khi submit: `controllers/website_recruitment.py`, `models/hr_applicant.py`

