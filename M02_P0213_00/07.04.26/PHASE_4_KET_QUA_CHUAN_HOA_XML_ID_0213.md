# PHASE 4 - KẾT QUẢ CHUẨN HÓA XML ID MODULE 0213

## 1. Mục tiêu Phase 4

Phase 4 tập trung chuẩn hóa `xml id` của module `0213` theo định hướng dùng mã quy trình thực tế `0213`, đồng bộ với naming convention đã chốt ở các phase trước.

Trong bối cảnh triển khai trên DB sạch:

- Không cần giữ tương thích `xml id` cũ để phục vụ upgrade dữ liệu.
- Có thể đổi trực tiếp sang bộ `xml id` mới.
- Mọi tham chiếu nội bộ trong Python/XML phải được cập nhật đồng bộ để module cài mới không phát sinh lỗi `External ID not found`.

## 2. Phạm vi đã thực hiện

### 2.1. Chuẩn hóa `record id` dữ liệu

Đã đổi các `xml id` chính như sau:

- `approval_category_resignation` -> `psm_0213_approval_category_resignation`
- `offboarding_activity_plan` -> `psm_0213_offboarding_activity_plan`
- `offboarding_template_asset_recovery` -> `psm_0213_offboarding_template_asset_recovery`
- `offboarding_template_damage_assessment` -> `psm_0213_offboarding_template_damage_assessment`
- `offboarding_template_deactive_email` -> `psm_0213_offboarding_template_deactive_email`
- `offboarding_template_expense_claim` -> `psm_0213_offboarding_template_expense_claim`
- `offboarding_template_exit_interview` -> `psm_0213_offboarding_template_exit_interview`
- `email_template_exit_survey` -> `psm_0213_email_template_exit_survey`
- `email_template_adecco_notification` -> `psm_0213_email_template_adecco_notification`
- `email_template_social_insurance` -> `psm_0213_email_template_social_insurance`
- `email_template_offboarding_reminder` -> `psm_0213_email_template_offboarding_reminder`
- `email_template_dept_offboarding_reminder` -> `psm_0213_email_template_dept_offboarding_reminder`
- `survey_exit_interview` -> `psm_0213_survey_exit_interview`
- `ir_cron_offboarding_reminder` -> `action_psm_0213_offboarding_reminder_cron`

### 2.2. Chuẩn hóa `view id` và `template id`

Đã đổi:

- `approval_request_resignation_view_form` -> `view_psm_0213_approval_request_form`
- `approval_category_resignation_view_form` -> `view_psm_0213_approval_category_form`
- `resignation_portal_template` -> `view_psm_0213_resignation_portal_template`

### 2.3. Cập nhật tham chiếu nội bộ

Đã cập nhật đồng bộ các chỗ gọi:

- `env.ref("M02_P0213_00....")`
- `request.render("M02_P0213_00....")`
- `%(M02_P0213_00....)d`
- `ref="..."`

Các nhóm file đã được đồng bộ:

- Python model/controller
- XML data
- XML view
- Portal template

## 3. File đã tác động trong Phase 4

### 3.1. Data XML

- `data/approval_category_data.xml`
- `data/offboarding_activity_plan_data.xml`
- `data/email_template_exit_survey.xml`
- `data/email_template_adecco_notification.xml`
- `data/email_template_social_insurance.xml`
- `data/email_template_offboarding_reminder.xml`
- `data/email_template_dept_offboarding_reminder.xml`
- `data/survey_exit_interview_data.xml`
- `data/ir_cron_data.xml`

### 3.2. View XML

- `views/resignation_request_views.xml`
- `views/resignation_portal_template.xml`

### 3.3. Python

- `models/resignation_request.py`
- `models/mail_activity.py`
- `models/survey_user_input.py`
- `controllers/main.py`

## 4. Kết quả kiểm tra sau refactor

Đã kiểm tra và xác nhận:

- Không còn tham chiếu nội bộ nào dùng các `xml id` cũ trong module `M02_P0213_00`.
- Không còn `record id`, `template id`, `view id` cũ trong các file XML đã rà soát.
- `py_compile` pass cho các file Python chính của module sau khi cập nhật tham chiếu.

## 5. Lưu ý vận hành

- Vì hướng triển khai là xóa DB và cài mới module, việc đổi `xml id` trong Phase 4 là phù hợp.
- Nếu sau này phát sinh nhu cầu upgrade trên DB cũ, cần bổ sung chiến lược alias/migration cho `xml id`.
- Phase 4 mới xử lý chuẩn hóa tên định danh kỹ thuật; chưa thay đổi logic nghiệp vụ ngoài phạm vi cần thiết để cập nhật reference.

## 6. Kết luận

Phase 4 đã hoàn tất theo mục tiêu:

- Bộ `xml id` của module `0213` đã được chuẩn hóa theo mã quy trình thực tế `0213`.
- Toàn bộ tham chiếu nội bộ quan trọng đã được đồng bộ.
- Module đã sẵn sàng cho các phase tiếp theo: tách logic, rà security, làm sạch dependency và kiểm thử cài mới trên DB sạch.
