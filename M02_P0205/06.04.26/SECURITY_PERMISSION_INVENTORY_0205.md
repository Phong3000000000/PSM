# Tổng Hợp Các Phần Liên Quan Đến Quyền Trong Module 0205

Tài liệu này tổng hợp toàn bộ các thành phần liên quan đến quyền trong module `M02_P0205`, bao gồm:

- group được tạo mới
- access rights trong `ir.model.access.csv`
- record rule hoặc phần can thiệp vào `ir.rule`
- giới hạn theo `groups` trong view
- kiểm tra quyền trong Python
- route controller liên quan đến phân quyền hoặc public/user access

## 1. Khai báo security trong manifest

Trong [__manifest__.py](d:\odoo-19.0+e.20250918\addons\M02_P0205\__manifest__.py), module nạp các file security sau:

- `security/hr_validator_group.xml`
- `security/approval_groups.xml`
- `security/recruitment_security.xml`
- `security/ir.model.access.csv`

Điều này cho thấy lớp quyền chính của module đang nằm ở:

- group tùy biến
- ACL cho model
- sửa record rule có sẵn của Odoo

## 2. Các group được tạo mới

### 2.1. `group_hr_validator`

File: [hr_validator_group.xml](d:\odoo-19.0+e.20250918\addons\M02_P0205\security\hr_validator_group.xml)

- Tên group: `HR Validator`
- XML ID: `M02_P0205.group_hr_validator`
- `implied_ids`:
  - `hr.group_hr_manager`

Ý nghĩa:

- user thuộc group này sẽ đồng thời có quyền của `HR Manager`
- group này được dùng trong flow gửi activity cho HR validate

### 2.2. `group_ceo_recruitment`

File: [approval_groups.xml](d:\odoo-19.0+e.20250918\addons\M02_P0205\security\approval_groups.xml)

- Tên group: `CEO Recruitment Approver`
- XML ID: `M02_P0205.group_ceo_recruitment`
- `implied_ids`:
  - `hr.group_hr_manager`

Ý nghĩa:

- đại diện nhóm CEO duyệt tuyển dụng
- hiện được dùng trong code để gửi activity CEO duyệt yêu cầu tuyển dụng

### 2.3. `group_bod_recruitment`

File: [approval_groups.xml](d:\odoo-19.0+e.20250918\addons\M02_P0205\security\approval_groups.xml)

- Tên group: `BOD Recruitment Viewer`
- XML ID: `M02_P0205.group_bod_recruitment`
- `implied_ids`:
  - `hr.group_hr_manager`

Ý nghĩa:

- được dùng để cho phép thao tác hoặc hiển thị các bước phỏng vấn vòng 3

### 2.4. `group_abu_recruitment`

File: [approval_groups.xml](d:\odoo-19.0+e.20250918\addons\M02_P0205\security\approval_groups.xml)

- Tên group: `ABU Recruitment Control`
- XML ID: `M02_P0205.group_abu_recruitment`
- `implied_ids`:
  - `hr.group_hr_manager`

Ý nghĩa:

- được dùng để cho phép thao tác hoặc hiển thị các bước phỏng vấn vòng 4

## 3. Access rights trong `ir.model.access.csv`

File: [ir.model.access.csv](d:\odoo-19.0+e.20250918\addons\M02_P0205\security\ir.model.access.csv)

## 3.1. Các model custom được cấp quyền cho `base.group_user`

Nhóm `base.group_user` đang có đầy đủ quyền `read/write/create/unlink` đối với:

- `recruitment.request`
- `recruitment.plan`
- `recruitment.plan.line`
- `hr.applicant.evaluation`
- `hr.applicant.evaluation.line`
- `recruitment.batch`
- `recruitment.request.line`
- `recruitment.request.approver`

Chi tiết:

- tất cả các access tương ứng cho `base.group_user` đều đang là `1,1,1,1`

Ý nghĩa:

- bất kỳ user nội bộ nào thuộc `base.group_user` đều có toàn quyền CRUD trên các model custom này

## 3.2. Các model custom được cấp quyền cho `hr_recruitment.group_hr_recruitment_manager`

Nhóm `hr_recruitment.group_hr_recruitment_manager` cũng đang có đầy đủ quyền `read/write/create/unlink` đối với cùng các model trên:

- `recruitment.request`
- `recruitment.plan`
- `recruitment.plan.line`
- `hr.applicant.evaluation`
- `hr.applicant.evaluation.line`
- `recruitment.batch`
- `recruitment.request.line`
- `recruitment.request.approver`

## 3.3. Quyền đọc trên `survey.survey`

Trong module có thêm:

- `access_survey_manager`: `hr_recruitment.group_hr_recruitment_manager` có `read` trên `survey.survey`
- `access_survey_user`: `base.group_user` có `read` trên `survey.survey`

Không có:

- `write`
- `create`
- `unlink`

Ý nghĩa:

- module chỉ mở quyền đọc survey từ ACL riêng trong chính module này

## 4. Record rule và phần can thiệp vào `ir.rule`

### 4.1. Sửa rule chuẩn của Odoo cho `hr.job`

File: [recruitment_security.xml](d:\odoo-19.0+e.20250918\addons\M02_P0205\security\recruitment_security.xml)

Module không tạo record rule mới riêng cho model custom, nhưng có sửa rule chuẩn của Odoo:

- rule bị sửa: `hr.hr_job_comp_rule`
- model tác động: `ir.rule`
- nội dung `domain_force` mới:
  - cho phép thấy `hr.job` nếu:
    - `website_published = True`
    - hoặc `company_id in company_ids + [False]`

Tên rule sau khi sửa:

- `Job multi company rule (Published bypass)`

Ý nghĩa:

- job được publish website có thể vượt qua một phần ràng buộc multi-company mặc định
- đây là thay đổi quan trọng liên quan trực tiếp đến phạm vi nhìn thấy dữ liệu tuyển dụng

### 4.2. Logic Python tiếp tục củng cố rule trên `hr.job`

Trong [models/hr_job.py](d:\odoo-19.0+e.20250918\addons\M02_P0205\models\hr_job.py), module còn có logic cập nhật thêm `domain_force` của rule nếu cần.

Điều này cho thấy:

- module không chỉ sửa rule bằng XML
- mà còn có code Python đảm bảo rule “published bypass” tiếp tục tồn tại

## 5. Giới hạn theo `groups` trong view

## 5.1. `recruitment.request_views.xml`

File: [recruitment_request_views.xml](d:\odoo-19.0+e.20250918\addons\M02_P0205\views\recruitment_request_views.xml)

Các field có `groups`:

- `user_id`:
  - `groups="base.group_user"`
- `company_id`:
  - `groups="base.group_user"`

Nhận xét:

- hầu hết các nút action trong form không có `groups`, chỉ bị khống chế bởi `state` và logic giao diện
- vì vậy lớp bảo vệ chính ở đây không nằm ở view groups mà chủ yếu nằm ở ACL và logic code

## 5.2. `hr.applicant_views.xml`

File: [hr_applicant_views.xml](d:\odoo-19.0+e.20250918\addons\M02_P0205\views\hr_applicant_views.xml)

Đây là file có nhiều giới hạn theo `groups` nhất.

### Các action chỉ cho `hr_recruitment.group_hr_recruitment_user`

- `action_send_interview_slot_survey`
- `action_send_interview_round2_notification`
- `action_invite_interview_l1`
- `action_invite_interview_l2`
- `action_ready_for_offer`
- `action_send_offer`
- `action_confirm_signed`

### Các action cho `hr_recruitment.group_hr_recruitment_user` và `group_bod_recruitment`

- `action_send_interview_round3_notification`
- `action_invite_interview_l3`
- `action_start_eval_l3`

### Các action cho `hr_recruitment.group_hr_recruitment_user` và `group_abu_recruitment`

- `action_send_interview_round4_notification`
- `action_invite_interview_l4`
- `action_start_eval_l4`

### Các vùng giao diện bị giới hạn cho `hr_recruitment.group_hr_recruitment_user`

- group `Người phỏng vấn chính`

Ý nghĩa:

- view đang dùng `groups` để khóa các thao tác nghiệp vụ theo vòng phỏng vấn
- BOD và ABU được gắn vào các nút/luồng của vòng 3 và vòng 4

## 5.3. Các view khác

Các file sau không thấy có giới hạn `groups` đáng chú ý:

- [recruitment_plan_views.xml](d:\odoo-19.0+e.20250918\addons\M02_P0205\views\recruitment_plan_views.xml)
- [recruitment_request_approver_views.xml](d:\odoo-19.0+e.20250918\addons\M02_P0205\views\recruitment_request_approver_views.xml)
- [calendar_event_views.xml](d:\odoo-19.0+e.20250918\addons\M02_P0205\views\calendar_event_views.xml)
- [hr_job_views.xml](d:\odoo-19.0+e.20250918\addons\M02_P0205\views\hr_job_views.xml)
- [res_company_views.xml](d:\odoo-19.0+e.20250918\addons\M02_P0205\views\res_company_views.xml)
- [survey_views.xml](d:\odoo-19.0+e.20250918\addons\M02_P0205\views\survey_views.xml)

Điều này có nghĩa:

- nhiều thao tác trong các màn hình này hiện không bị chặn bằng `groups` ở giao diện
- quyền truy cập thực tế chủ yếu phụ thuộc vào ACL hoặc logic Python

## 6. Kiểm tra quyền trong code Python

## 6.1. `models/recruitment_request.py`

File: [recruitment_request.py](d:\odoo-19.0+e.20250918\addons\M02_P0205\models\recruitment_request.py)

Module dùng group XML ID để gửi activity:

- `M02_P0205.group_hr_validator`
- fallback sang `hr.group_hr_manager`
- `M02_P0205.group_ceo_recruitment`

Ý nghĩa:

- đây không phải kiểm tra chặn quyền trực tiếp
- nhưng là cơ chế điều hướng công việc theo group

## 6.2. `models/hr_job.py`

File: [hr_job.py](d:\odoo-19.0+e.20250918\addons\M02_P0205\models\hr_job.py)

Module lấy user mặc định theo group:

- `M02_P0205.group_bod_recruitment`
- `M02_P0205.group_abu_recruitment`

Ý nghĩa:

- group ở đây được dùng để xác định người phỏng vấn mặc định cho job office

## 6.3. `models/recruitment_plan.py`

File: [recruitment_plan.py](d:\odoo-19.0+e.20250918\addons\M02_P0205\models\recruitment_plan.py)

Có logic xác định HR users bằng:

- `u.has_group('hr.group_hr_manager')`
- `u.has_group('hr.group_hr_user')`

Mục đích:

- gửi activity cho HR validate kế hoạch tuyển dụng

## 6.4. `models/hr_applicant.py`

File: [hr_applicant.py](d:\odoo-19.0+e.20250918\addons\M02_P0205\models\hr_applicant.py)

Các điểm liên quan đến quyền:

- kiểm tra creator:
  - `creator._is_public()`
  - `creator.has_group('base.group_portal')`
- dùng group XML ID để:
  - lấy user BOD
  - lấy user ABU
  - schedule activity theo group

Ý nghĩa:

- phân biệt applicant được tạo từ public/portal với user nội bộ
- dùng group để luân chuyển activity và xác định người tham gia quy trình

## 7. Route controller và mức truy cập

## 7.1. `controllers/portal.py`

File: [portal.py](d:\odoo-19.0+e.20250918\addons\M02_P0205\controllers\portal.py)

Các route:

- `/my/jobs`
- `/my/jobs/page/<int:page>`
- `/my/recruitment_requests`
- `/my/recruitment_requests/page/<int:page>`

Tất cả đều dùng:

- `auth="user"`

Ý nghĩa:

- chỉ user đã đăng nhập mới truy cập được

Lưu ý:

- trong route `/my/jobs`, code dùng nhiều `sudo()` để đọc:
  - `recruitment.plan.line`
  - `recruitment.request`

Điều này làm phạm vi đọc dữ liệu dựa vào domain thủ công trong controller nhiều hơn là ACL chuẩn.

## 7.2. `controllers/job_portal.py`

File: [job_portal.py](d:\odoo-19.0+e.20250918\addons\M02_P0205\controllers\job_portal.py)

Các route chính:

- `/my/jobs`
  - `auth='user'`
- `/jobs/detail/<int:line_id>`
  - `auth='public'`
- `/jobs/request/detail/<int:request_id>`
  - `auth='public'`
- `/jobs/apply/<int:job_id>`
  - `auth='public'`
- `/jobs/apply/<model("hr.job"):job>`
  - `auth='public'`
- `/jobs/submit`
  - `auth='public'`
- `/jobs/thankyou`
  - `auth='public'`

Đặc điểm đáng chú ý:

- controller dùng `sudo()` ở rất nhiều điểm để đọc:
  - `recruitment.plan.line`
  - `recruitment.request`
  - `hr.job`
  - `survey`
- quyền truy cập thực tế được kiểm soát bằng:
  - `auth='public'` hoặc `auth='user'`
  - các điều kiện domain trong code
  - trạng thái `is_published`, `website_published`, `active`, `is_office_job`

## 7.3. `controllers/interview_slot.py`

File: [interview_slot.py](d:\odoo-19.0+e.20250918\addons\M02_P0205\controllers\interview_slot.py)

Route:

- `/interview/choose/<string:token>/<int:event_id>`
- `auth='public'`

Đặc điểm:

- dùng `sudo()` để tìm applicant và event
- kiểm tra applicant bằng `interview_slot_token`
- kiểm tra event có thuộc applicant đó hay không

Ý nghĩa:

- đây là route public nhưng được bảo vệ bằng token nghiệp vụ
- không phụ thuộc vào user login

## 8. Dữ liệu mẫu có gán quyền

File: [hr_employee_sample_data.xml](d:\odoo-19.0+e.20250918\addons\M02_P0205\data\hr_employee_sample_data.xml)

Trong dữ liệu mẫu, module tạo một số user với group như sau:

- `user_marketing_head`
  - `base.group_user`
  - `hr.group_hr_manager`
- `user_hr_head`
  - `base.group_user`
  - `hr.group_hr_manager`
- `user_ceo`
  - `base.group_user`
  - `base.group_system`

Ý nghĩa:

- đây là dữ liệu phục vụ demo/sample
- không phải security definition cốt lõi, nhưng vẫn là phần liên quan đến quyền

## 9. Những gì chưa thấy trong module

Trong module `0205`, hiện chưa thấy:

- record rule riêng cho các model custom như `recruitment.plan`, `recruitment.request`, `recruitment.batch`
- menu bị giới hạn `groups` rõ ràng trong XML
- kiểm tra chặn quyền nhất quán ở tất cả action Python

Điều này có nghĩa:

- quyền hiện tại đang thiên nhiều về ACL model và điều kiện giao diện
- các model custom phần lớn đang mở khá rộng cho `base.group_user`

## 10. Kết luận ngắn

Các lớp quyền chính của module `0205` hiện gồm:

- group tùy biến:
  - `group_hr_validator`
  - `group_ceo_recruitment`
  - `group_bod_recruitment`
  - `group_abu_recruitment`
- ACL model trong `ir.model.access.csv`
- sửa rule chuẩn `hr.hr_job_comp_rule`
- giới hạn `groups` trong `hr_applicant_views.xml`
- logic `has_group(...)`, `auth=...`, và `sudo()` trong Python/controller

Nếu muốn siết quyền kỹ hơn ở bước sau, các điểm cần ưu tiên rà tiếp là:

- ACL quá rộng cho `base.group_user`
- thiếu record rule cho model custom
- nhiều controller public đang dùng `sudo()`
- nhiều action trong form không có kiểm tra quyền ở backend

