# Phase 0 - Chốt chuẩn và mapping refactor module 0213

## 1. Mục tiêu của Phase 0

Phase 0 dùng để chốt toàn bộ chuẩn đặt tên sẽ áp dụng cho module `M02_P0213_00` trước khi bắt đầu refactor code.

Đầu ra chính của phase này:

- Chốt prefix chính thức cho module `0213`
- Lập bảng mapping field cũ -> field mới
- Lập bảng mapping `xml id` cũ -> `xml id` mới
- Ghi nhận các tham chiếu nội bộ cần sửa
- Ghi nhận các blocker và rủi ro cần xử lý trước khi bước vào refactor thực tế

## 2. Chuẩn đặt tên được chốt cho 0213

### 2.1. Field mới trên model gốc Odoo

Chuẩn chính thức:

- `x_psm_0213_ten_field`

Không dùng:

- `x_psm_0101_*`

### 2.2. Model mới

Nếu sau này phát sinh model mới, chuẩn áp dụng là:

- `x_psm_ten_model`

Hiện tại `0213` chưa có model mới.

### 2.3. View mới

Chuẩn áp dụng:

- `view_psm_0213_ten_view`

### 2.4. Action mới

Chuẩn áp dụng:

- `action_psm_0213_ten_action`

### 2.5. Template / data record / cron

Chưa có quy ước riêng trong tài liệu gốc cho từng loại record XML, vì vậy trong Phase 0 chốt thống nhất theo hướng:

- View QWeb/template giao diện: `view_psm_0213_*`
- Cron/action record: `action_psm_0213_*`
- Data record nghiệp vụ khác: `psm_0213_*`

Mục tiêu là giữ naming nhất quán, dễ tra cứu và dễ phân biệt record theo chức năng.

## 3. Mapping field cũ -> field mới

## 3.1. Trên model `approval.category`

| STT | Field hiện tại | Field sau refactor |
| --- | --- | --- |
| 1 | `is_offboarding` | `x_psm_0213_is_offboarding` |

## 3.2. Trên model `approval.request`

| STT | Field hiện tại | Field sau refactor |
| --- | --- | --- |
| 1 | `resignation_reason` | `x_psm_0213_resignation_reason` |
| 2 | `resignation_reason_id` | `x_psm_0213_resignation_reason_id` |
| 3 | `resignation_date` | `x_psm_0213_resignation_date` |
| 4 | `employee_id` | `x_psm_0213_employee_id` |
| 5 | `resignation_employee_name` | `x_psm_0213_resignation_employee_name` |
| 6 | `resignation_manager_name` | `x_psm_0213_resignation_manager_name` |
| 7 | `resignation_department` | `x_psm_0213_resignation_department` |
| 8 | `job_id` | `x_psm_0213_job_id` |
| 9 | `employee_activity_ids` | `x_psm_0213_employee_activity_ids` |
| 10 | `exit_survey_completed` | `x_psm_0213_exit_survey_completed` |
| 11 | `all_activities_completed` | `x_psm_0213_all_activities_completed` |
| 12 | `type_contract` | `x_psm_0213_type_contract` |
| 13 | `resignation_owner_email` | `x_psm_0213_resignation_owner_email` |
| 14 | `is_plan_launched` | `x_psm_0213_is_plan_launched` |
| 15 | `adecco_notification_sent` | `x_psm_0213_adecco_notification_sent` |
| 16 | `exit_survey_user_input_id` | `x_psm_0213_exit_survey_user_input_id` |
| 17 | `owner_related_activity_ids` | `x_psm_0213_owner_related_activity_ids` |
| 18 | `is_rehire` | `x_psm_0213_is_rehire` |
| 19 | `is_blacklisted` | `x_psm_0213_is_blacklisted` |

## 3.3. Trên model `mail.activity`

| STT | Field hiện tại | Đề xuất xử lý trong refactor |
| --- | --- | --- |
| 1 | `active` | Không chốt rename ở Phase 0. Cần xác minh đây là field gốc Odoo hay field custom trùng tên trước khi quyết định |
| 2 | `ops_display_state` | `x_psm_0213_ops_display_state` |

## 3.4. Field gốc được mở rộng, không đổi tên

| Model | Field | Cách xử lý |
| --- | --- | --- |
| `approval.request` | `request_status` | Giữ nguyên tên field, chỉ giữ logic `selection_add` cho giá trị `done` |

## 3.5. Kết luận cho nhóm field

- Chốt rename ngay: 21 field
- Chưa chốt rename: 1 field là `mail.activity.active`
- Không đổi tên: `approval.request.request_status`

## 4. Mapping `xml id` cũ -> `xml id` mới

## 4.1. View và template

| STT | `xml id` hiện tại | `xml id` sau refactor |
| --- | --- | --- |
| 1 | `approval_request_resignation_view_form` | `view_psm_0213_approval_request_form` |
| 2 | `approval_category_resignation_view_form` | `view_psm_0213_approval_category_form` |
| 3 | `resignation_portal_template` | `view_psm_0213_resignation_portal_template` |

## 4.2. Cron

| STT | `xml id` hiện tại | `xml id` sau refactor |
| --- | --- | --- |
| 1 | `ir_cron_offboarding_reminder` | `action_psm_0213_offboarding_reminder_cron` |

## 4.3. Data record nghiệp vụ

| STT | `xml id` hiện tại | `xml id` sau refactor |
| --- | --- | --- |
| 1 | `approval_category_resignation` | `psm_0213_approval_category_resignation` |
| 2 | `offboarding_activity_plan` | `psm_0213_offboarding_activity_plan` |
| 3 | `offboarding_template_asset_recovery` | `psm_0213_offboarding_template_asset_recovery` |
| 4 | `offboarding_template_damage_assessment` | `psm_0213_offboarding_template_damage_assessment` |
| 5 | `offboarding_template_deactive_email` | `psm_0213_offboarding_template_deactive_email` |
| 6 | `offboarding_template_expense_claim` | `psm_0213_offboarding_template_expense_claim` |
| 7 | `offboarding_template_exit_interview` | `psm_0213_offboarding_template_exit_interview` |

## 4.4. Email template

| STT | `xml id` hiện tại | `xml id` sau refactor |
| --- | --- | --- |
| 1 | `email_template_exit_survey` | `psm_0213_email_template_exit_survey` |
| 2 | `email_template_adecco_notification` | `psm_0213_email_template_adecco_notification` |
| 3 | `email_template_social_insurance` | `psm_0213_email_template_social_insurance` |
| 4 | `email_template_offboarding_reminder` | `psm_0213_email_template_offboarding_reminder` |
| 5 | `email_template_dept_offboarding_reminder` | `psm_0213_email_template_dept_offboarding_reminder` |

## 4.5. Survey data

| Nhóm | Chuẩn đổi tên đề xuất |
| --- | --- |
| Survey chính | `psm_0213_survey_exit_interview` |
| Section | `psm_0213_survey_exit_section_*` |
| Question | `psm_0213_survey_exit_q*` |
| Answer | `psm_0213_survey_exit_q*_a*` |

Lưu ý:

- File `survey_exit_interview_data.xml` có rất nhiều record con.
- Không nhất thiết phải đổi tên toàn bộ record survey ở ngay đợt đầu nếu muốn giảm rủi ro.
- Có thể chia làm 2 đợt:
  - Đợt 1: đổi các `xml id` được code tham chiếu trực tiếp
  - Đợt 2: đổi phần record con của survey để đồng bộ hoàn toàn

## 5. Tham chiếu nội bộ cần sửa khi refactor

## 5.1. Trong Python

### `models/resignation_request.py`

Đang tham chiếu trực tiếp các `xml id` sau:

- `M02_P0213_00.email_template_adecco_notification`
- `M02_P0213_00.email_template_social_insurance`
- `M02_P0213_00.approval_category_resignation`
- `M02_P0213_00.offboarding_activity_plan`
- `M02_P0213_00.email_template_offboarding_reminder`
- `M02_P0213_00.email_template_dept_offboarding_reminder`

Ngoài ra còn đang tham chiếu chéo sang `M02_P0214_00`:

- `M02_P0214_00.survey_exit_interview`
- `M02_P0214_00.email_template_exit_survey`

### `models/mail_activity.py`

Đang tham chiếu:

- `M02_P0213_00.approval_category_resignation`

### `models/survey_user_input.py`

Đang tham chiếu chéo sang `M02_P0214_00`:

- `M02_P0214_00.survey_exit_interview`
- `M02_P0214_00.approval_category_resignation`

### `controllers/main.py`

Đang tham chiếu:

- `M02_P0213_00.approval_category_resignation`
- `M02_P0213_00.resignation_portal_template`
- `M02_P0214_00.survey_exit_interview`

## 5.2. Trong XML

### `views/resignation_request_views.xml`

Đang tham chiếu:

- `M02_P0213_00.approval_category_resignation`

### `data/offboarding_activity_plan_data.xml`

Đang tham chiếu nội bộ tới:

- `offboarding_activity_plan`

### `data/survey_exit_interview_data.xml`

Đang tham chiếu nội bộ tới:

- `survey_exit_interview`

## 6. Blocker và rủi ro phải khóa trước khi vào refactor sâu

## 6.1. Blocker 1: Field `mail.activity.active`

Hiện trong `models/mail_activity.py` có khai báo:

- `active = fields.Boolean(...)`

Nhưng `active` là tên field rất phổ biến trong Odoo.

Việc cần làm trước Phase 2:

- Xác minh trên version Odoo đang chạy xem `mail.activity` gốc đã có `active` hay chưa
- Nếu đã có sẵn:
  - không xem đây là field mới của `0213`
  - không rename
  - xem xét bỏ khai báo nếu chỉ là định nghĩa trùng
- Nếu chưa có sẵn:
  - mới đưa vào mapping rename chính thức

## 6.2. Blocker 2: Tham chiếu chéo không đồng nhất giữa `0213` và `0214`

Hiện tại module `0213` có tham chiếu chéo sang `M02_P0214_00` tại nhiều chỗ:

- survey exit interview
- approval category resignation
- email template exit survey

Trong khi đó dữ liệu survey và email template cũng đang tồn tại ngay trong `0213`.

Điều này cho thấy đang có trạng thái không đồng nhất:

- một phần code dùng tài nguyên của `0213`
- một phần code lại gọi sang `0214`

Việc cần làm trước Phase 2:

- Chốt tài nguyên chuẩn sẽ dùng ở đâu:
  - giữ trong `0213`
  - hay tách hẳn sang module dùng chung khác
- Sau khi chốt, thay toàn bộ reference cho nhất quán

## 6.3. Blocker 3: Trùng logic controller

Hiện có hai file:

- `controllers/main.py`
- `views/main.py`

Cả hai đang chứa class controller gần như trùng nhau.

Đây là dấu hiệu code dư thừa hoặc file đặt sai vị trí.

Việc cần làm trước hoặc trong Phase 1:

- Xác nhận file nào thực sự được nạp và sử dụng
- Loại bỏ file thừa hoặc gộp logic về một nơi duy nhất

## 6.4. Blocker 4: Đổi tên `xml id` survey có độ lan rất lớn

File survey có số lượng record con nhiều.

Rủi ro:

- gãy reference giữa question, answer, section, survey
- tăng khối lượng kiểm thử mà chưa tạo nhiều giá trị ngay trong vòng đầu

Khuyến nghị:

- Vòng refactor đầu chỉ đổi `xml id` survey chính nếu cần
- Các record con của survey có thể để phase sau, sau khi luồng nghiệp vụ chính đã ổn định

## 7. Danh sách quyết định đã chốt ở cuối Phase 0

- Dùng mã quy trình thực tế `0213`, không dùng `0101`
- Field mới trên model gốc đổi theo chuẩn `x_psm_0213_*`
- View đổi theo chuẩn `view_psm_0213_*`
- Cron/action đổi theo chuẩn `action_psm_0213_*`
- Data record nghiệp vụ đổi theo chuẩn `psm_0213_*`
- Tạm thời chưa chốt rename field `mail.activity.active`
- Cần xử lý dứt điểm việc tham chiếu chéo `0213` / `0214` trước khi đổi tên diện rộng

## 8. Đầu ra đề xuất cho bước tiếp theo

Sau Phase 0, bước nên làm tiếp là:

1. Tạo bảng implementation checklist theo từng file
2. Xác minh field `mail.activity.active`
3. Chốt tài nguyên chuẩn giữa `0213` và `0214`
4. Bắt đầu Phase 1 hoặc đi thẳng vào Phase 2 nếu các blocker đã được khóa
