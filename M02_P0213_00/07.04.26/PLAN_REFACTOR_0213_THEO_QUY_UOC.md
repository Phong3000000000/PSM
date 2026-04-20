# Kế hoạch refactor module 0213 theo quy ước đặt tên và rule

## 1. Mục tiêu

Refactor module `M02_P0213_00` để tuân thủ tài liệu `QUY_UOC_DAT_TEN_VA_RULE.md`, đồng thời giữ nguyên hành vi nghiệp vụ hiện tại của quy trình nghỉ việc.

Mục tiêu cụ thể:

- Chuẩn hóa tên field mới trên model gốc theo quy ước.
- Chuẩn hóa tên `xml id` của view, action, cron, template, data record theo quy ước.
- Rà soát và siết lại phân quyền theo nguyên tắc tối thiểu.
- Tách bạch rõ phần logic business, phần giao diện, phần dữ liệu mẫu.
- Giảm rủi ro xung đột về naming với các module khác trong tương lai.

## 2. Căn cứ lập kế hoạch

### 2.1. Tài liệu đầu vào

- `DANH_SACH_MODEL_KE_THUA_VA_TAO_MOI_0213.md`
- `DANH_SACH_FIELD_KE_THUA_VA_TAO_MOI_0213.md`
- `QUY_UOC_DAT_TEN_VA_RULE.md`

### 2.2. Hiện trạng module 0213

- Module `0213` không tạo model mới bằng `_name`.
- Module chỉ mở rộng 4 model có sẵn của Odoo:
  - `approval.category`
  - `approval.request`
  - `mail.activity`
  - `survey.user_input`
- Module đang có 22 field mới trên model gốc Odoo.
- Nhiều field mới hiện chưa theo quy ước prefix.
- Nhiều `xml id` hiện đang đặt theo tên nghiệp vụ cũ, chưa thống nhất theo quy ước `view_psm_*`, `action_psm_*`.
- File phân quyền hiện đang cấp khá rộng cho nhiều model dùng chung của Odoo, cần rà lại theo rule `minimum permission`.

## 3. Nguyên tắc refactor

- Không đổi tên model gốc của Odoo.
- Không tạo model mới nếu chưa thật sự cần thiết.
- Ưu tiên giữ nguyên nghiệp vụ, chỉ đổi cấu trúc và naming.
- Refactor theo từng lớp:
  - Field và Python API
  - XML id và view/template/data
  - Security
  - Kiểm thử hồi quy
- Luôn có lớp tương thích tạm thời nếu việc đổi tên field có thể ảnh hưởng dữ liệu cũ hoặc code tham chiếu chéo.

## 4. Quy ước áp dụng chính thức cho 0213

Tài liệu quy ước đang ví dụ field mới trên model gốc là:

- `x_psm_0101_tenfield`

Tuy nhiên với module `0213`, quy ước được chốt để áp dụng là dùng đúng mã quy trình thực tế của module:

- `x_psm_0213_tenfield`

Ví dụ:

- `is_offboarding` -> `x_psm_0213_is_offboarding`
- `resignation_reason` -> `x_psm_0213_resignation_reason`

Đây là chuẩn chính thức để triển khai từ Phase 0 trở đi.

## 5. Phạm vi refactor

### 5.1. Trong phạm vi

- Python models trong `models/`
- XML views/templates/data trong `views/` và `data/`
- Security trong `security/`
- Manifest và tham chiếu nội bộ của module
- Cron, email template, survey reference, approval category record, portal template

### 5.2. Ngoài phạm vi

- Thay đổi nghiệp vụ cốt lõi của quy trình nghỉ việc
- Thiết kế lại UI/UX portal theo hướng mới
- Tạo model mới nếu không bị bắt buộc bởi yêu cầu nghiệp vụ khác
- Refactor các module khác ngoài `0213`, trừ khi cần cập nhật reference chéo

## 6. Danh mục đối tượng cần refactor

### 6.1. Model

Không có model mới cần đổi sang `x_psm_*`.

### 6.2. Field mới trên model gốc cần chuẩn hóa tên

#### Trên `approval.category`

- `is_offboarding`

#### Trên `approval.request`

- `resignation_reason`
- `resignation_reason_id`
- `resignation_date`
- `employee_id`
- `resignation_employee_name`
- `resignation_manager_name`
- `resignation_department`
- `job_id`
- `employee_activity_ids`
- `exit_survey_completed`
- `all_activities_completed`
- `type_contract`
- `resignation_owner_email`
- `is_plan_launched`
- `adecco_notification_sent`
- `exit_survey_user_input_id`
- `owner_related_activity_ids`
- `is_rehire`
- `is_blacklisted`

#### Trên `mail.activity`

- `active`
- `ops_display_state`

### 6.3. Field gốc được mở rộng

- `approval.request.request_status`

Field này không đổi tên, nhưng cần rà logic liên quan vì đang thêm giá trị `done`.

### 6.4. XML id và tài nguyên cần chuẩn hóa

Nhóm đối tượng cần rà và đổi tên:

- View id
- Template id
- Cron id
- Data record id
- Có thể cả tên method action nội bộ nếu muốn thống nhất thêm một lớp naming

Ví dụ các id hiện tại cần xem xét đổi:

- `approval_request_resignation_view_form`
- `approval_category_resignation_view_form`
- `approval_category_resignation`
- `ir_cron_offboarding_reminder`
- `resignation_portal_template`

## 7. Kế hoạch refactor theo phase

## Phase 0. Khảo sát và chốt chuẩn

### Mục tiêu

Chốt phạm vi đổi tên, quy tắc prefix và chiến lược migration trước khi sửa code.

### Công việc

- Xác nhận prefix chính thức cho field mới của module:
  - `x_psm_0213_*`
- Lập bảng mapping tên cũ -> tên mới cho toàn bộ 22 field mới.
- Lập bảng mapping `xml id` cũ -> `xml id` mới.
- Xác định các tham chiếu chéo từ module khác tới `0213`.
- Kiểm tra dữ liệu production/staging có bản ghi đang dùng các field hiện tại hay chưa.

### Đầu ra

- Tài liệu mapping hoàn chỉnh cho field, xml id, method, record id.
- Danh sách rủi ro migration.

### Rủi ro chính

- Đổi tên field trên model gốc sẽ ảnh hưởng dữ liệu hiện có.
- Đổi `xml id` có thể làm gãy `env.ref(...)`, inherited view và email template reference.
- Trong module đang tồn tại dấu hiệu logic controller bị sao chép giữa `controllers/main.py` và `views/main.py`, đồng thời tham chiếu survey không đồng nhất giữa `0213` và `0214`. Điểm này cần khóa sớm ngay ở Phase 0.

## Phase 1. Đóng băng nghiệp vụ và thiết lập đường kiểm thử

### Mục tiêu

Có baseline rõ ràng để so sánh trước và sau refactor.

### Công việc

- Xác định các luồng chính cần chạy hồi quy:
  - Gửi đơn nghỉ việc từ portal
  - Manager approve
  - Sinh activity offboarding
  - Gửi exit survey
  - Mark done activity
  - Gửi BHXH/Adecco
  - Hoàn tất nghỉ việc
  - Tái tuyển / blacklist
  - Cron reminder
- Ghi nhận các màn hình, action, template, cron đang hoạt động.
- Nếu có thể, bổ sung test hoặc checklist test tay theo các luồng trên.

### Đầu ra

- Checklist regression test.
- Bộ dữ liệu test tối thiểu.

## Phase 2. Chuẩn hóa field trên model gốc

### Mục tiêu

Đưa toàn bộ field mới trên model gốc về đúng quy ước naming.

### Công việc

- Đổi tên toàn bộ 22 field mới theo prefix `x_psm_0213_`.
- Cập nhật tất cả chỗ tham chiếu field trong:
  - Python
  - XML view
  - QWeb template
  - domain
  - context
  - compute
  - related
  - search
  - write/create
  - cron
  - mail template nếu có
- Rà riêng field `active` trên `mail.activity`.

### Lưu ý đặc biệt

- `active` là tên field gốc phổ biến của Odoo. Nếu model `mail.activity` ở hệ hiện tại đã có `active`, cần tránh coi đây là field mới cần rename một cách máy móc.
- Cần xác minh lại trên instance hoặc source chuẩn trước khi đổi.
- Nếu `active` vốn là field chuẩn đã có sẵn, thì phần refactor đúng là:
  - bỏ khai báo trùng lặp nếu không cần
  - giữ dùng field gốc Odoo
  - không rename thành `x_psm_0213_active`

### Đầu ra

- Bộ field đã được chuẩn hóa tên.
- Code compile được và không còn reference cũ trong module.

## Phase 3. Validate cài mới trên DB sạch

### Mục tiêu

Xác nhận module có thể cài mới trên database sạch sau khi đã refactor field ở Phase 2.

### Công việc

- Tạo DB mới hoặc reset DB hiện có.
- Cài mới module `M02_P0213_00`.
- Kiểm tra toàn bộ XML, field, view, access rule được nạp thành công.
- Kiểm tra các data file chính:
  - category nghỉ việc
  - survey exit interview
  - email template
  - cron
  - offboarding activity plan
- Kiểm tra không còn lỗi `field not found`, `external id not found`, `view validation`.
- Chạy smoke test mức cài đặt:
  - mở form `approval.request`
  - mở form `approval.category`
  - mở route portal nghỉ việc

### Đầu ra

- Biên bản cài mới thành công trên DB sạch.
- Danh sách lỗi cài đặt nếu còn.

## Phase 4. Chuẩn hóa XML id, view, template, data record

### Mục tiêu

Đưa tên tài nguyên XML về đúng quy ước và làm sạch tham chiếu nội bộ.

### Công việc

- Đổi tên view theo mẫu:
  - `view_psm_*`
- Đổi tên action nếu có action mới theo mẫu:
  - `action_psm_*`
- Đổi tên template portal theo quy ước thống nhất.
- Đổi tên cron, category record, template data, survey data nếu cần theo chuẩn chung.
- Cập nhật toàn bộ chỗ dùng:
  - `env.ref(...)`
  - `ref="..."`
  - inherited view
  - mail template external id
  - cron code

### Gợi ý tên đích

- `approval_request_resignation_view_form` -> `view_psm_0213_approval_request_form`
- `approval_category_resignation_view_form` -> `view_psm_0213_approval_category_form`
- `resignation_portal_template` -> `view_psm_0213_resignation_portal_template`
- `ir_cron_offboarding_reminder` -> `action_psm_0213_offboarding_reminder_cron`

### Đầu ra

- Toàn bộ XML id chính trong module được đặt tên thống nhất.

## Phase 5. Tách bạch logic theo rule

### Mục tiêu

Giảm chồng chéo logic và tăng khả năng bảo trì.

### Công việc

- Tách logic trong `models/resignation_request.py` thành các nhóm rõ ràng:
  - field definitions
  - compute helpers
  - business actions
  - notification/email
  - offboarding activity logic
  - cron/manual reminder logic
- Xem xét tách file nếu cần:
  - `approval_category.py`
  - `approval_request.py`
  - `mail_activity.py`
  - `survey_user_input.py`
- Tách rõ controller portal và phần view/template portal.
- Hạn chế hard-code text hoặc logic lặp lại.

### Đầu ra

- Cấu trúc file rõ ràng hơn.
- Giảm độ dài và độ rối của file model chính.

## Phase 6. Rà soát phân quyền theo nguyên tắc tối thiểu

### Mục tiêu

Đưa security về đúng nhu cầu thực tế, tránh cấp quyền dư thừa.

### Công việc

- Kiểm tra lại từng dòng trong `ir.model.access.csv`.
- Xác định model nào thật sự cần portal create/write.
- Giảm quyền nội bộ không cần thiết trên:
  - `mail.activity`
  - `survey.user_input`
  - `survey.question`
  - `survey.question.answer`
  - `hr.employee`
  - `hr.contract.type`
  - `hr.departure.reason`
- Nếu cần, chuyển bớt logic sang `sudo()` có kiểm soát thay vì cấp quyền rộng.
- Xem xét bổ sung rule/group riêng nếu quy trình yêu cầu.

### Đầu ra

- File security tinh gọn hơn.
- Ma trận phân quyền rõ ràng theo vai trò.

## Phase 7. Làm sạch phụ thuộc và tham chiếu module

### Mục tiêu

Đảm bảo module bám đúng rule “ưu tiên dùng cái sẵn có” và “tách bạch rõ ràng”.

### Công việc

- Kiểm tra các tham chiếu đang gọi sang `M02_P0214_00`.
- Xác định phần nào là dùng chung hợp lý, phần nào đang coupling quá chặt.
- Chuẩn hóa cách dùng `approvals` và `survey` theo module chuẩn Odoo.
- Rà soát manifest để bổ sung hoặc loại bỏ dependency không cần.

### Đầu ra

- Danh sách phụ thuộc sạch hơn.
- Giảm phụ thuộc chéo không cần thiết giữa `0213` và module khác.

## Phase 8. Kiểm thử hồi quy và ổn định hóa trên DB sạch

### Mục tiêu

Xác nhận refactor không làm thay đổi hành vi nghiệp vụ trong kịch bản cài mới module trên database sạch.

### Công việc

- Cài mới lại module trên DB sạch sau các phase refactor tiếp theo.
- Chạy lại checklist regression test của Phase 1.
- Kiểm tra:
  - form approval.request
  - category form
  - portal resignation page
  - activity checklist
  - exit survey flow
  - cron reminder
  - email template rendering
- Kiểm tra log warning/error liên quan `env.ref`, field not found, view validation.

### Đầu ra

- Biên bản test pass/fail.
- Danh sách bug còn sót để xử lý vòng cuối.

## Phase 9. Chốt tài liệu và bàn giao

### Mục tiêu

Hoàn thiện tài liệu sau refactor để dễ bảo trì.

### Công việc

- Cập nhật lại:
  - danh sách model
  - danh sách field
  - mapping tên cũ/tên mới
  - security matrix
  - checklist test
- Ghi chú các breaking change nếu có.
- Soạn hướng dẫn cài mới module trên DB sạch theo cấu trúc sau refactor.

### Đầu ra

- Bộ tài liệu bàn giao đầy đủ.

## 8. Thứ tự ưu tiên thực hiện thực tế

Đề xuất thứ tự thực hiện:

1. Phase 0
2. Phase 1
3. Phase 2
4. Phase 3
5. Phase 4
6. Phase 5
7. Phase 6
8. Phase 7
9. Phase 8
10. Phase 9

## 9. Rủi ro lớn nhất cần khóa sớm

- Đổi tên field vẫn là phần rủi ro cao vì ảnh hưởng toàn bộ XML/Python reference, dù không còn áp lực migrate dữ liệu cũ khi dùng DB sạch.
- Đổi `xml id` sẽ ảnh hưởng dữ liệu đã `noupdate`, inherited view, `env.ref` và các module tham chiếu chéo.
- `mail.activity.active` cần xác minh kỹ trước khi refactor vì có khả năng là field gốc của hệ hoặc đã bị module khác mở rộng trước.
- Các tham chiếu sang `M02_P0214_00` cần kiểm tra để tránh gãy luồng khảo sát và category reference.

## 10. Đề xuất chiến lược triển khai an toàn

- Thực hiện refactor theo nhánh riêng.
- Chia merge theo từng phase lớn thay vì sửa tất cả trong một lần.
- Ưu tiên hoàn thành:
  - mapping
  - kiểm tra cài mới trên DB sạch
  - regression test
trước khi đưa lên môi trường dùng thật.

## 11. Kết luận

Module `0213` phù hợp để refactor theo quy ước vì hiện chưa có model mới, phạm vi chủ yếu nằm ở:

- đổi tên field mới trên model gốc
- chuẩn hóa `xml id`
- siết security
- tách logic cho rõ ràng hơn

Đây là một đợt refactor có rủi ro trung bình, trọng tâm nằm ở reference code và XML nhiều hơn là migration dữ liệu, vì giả định triển khai hiện tại là reset DB và cài mới module. Do đó, các phase sau cần ưu tiên kiểm tra cài mới, chuẩn hóa `xml id`, và test hồi quy trên DB sạch.
