# Bản đồ nhóm quyền module 0205

## 1. Các file security được nạp từ manifest

Tham chiếu: [__manifest__.py:35](/d:/odoo-19.0+e.20250918/addons/M02_P0205/__manifest__.py#L35)

- `security/hr_validator_group.xml`
- `security/approval_groups.xml`
- `security/recruitment_security.xml`
- `security/ir.model.access.csv`

## 2. Các nhóm quyền được định nghĩa trong 0205

| XML ID nhóm | Tên nhóm | File định nghĩa | Nhóm được imply | Mục đích sử dụng |
| --- | --- | --- | --- | --- |
| `M02_P0205.group_hr_validator` | HR Validator | [security/hr_validator_group.xml:4](/d:/odoo-19.0+e.20250918/addons/M02_P0205/security/hr_validator_group.xml#L4) | `hr.group_hr_manager` | Dùng cho vai trò HR duyệt/xác nhận trong luồng yêu cầu tuyển dụng |
| `M02_P0205.group_ceo_recruitment` | CEO Recruitment Approver | [security/approval_groups.xml:4](/d:/odoo-19.0+e.20250918/addons/M02_P0205/security/approval_groups.xml#L4) | `hr.group_hr_manager` | Dùng cho bước phê duyệt của CEO |
| `M02_P0205.group_bod_recruitment` | BOD Recruitment Viewer | [security/approval_groups.xml:8](/d:/odoo-19.0+e.20250918/addons/M02_P0205/security/approval_groups.xml#L8) | `hr.group_hr_manager` | Dùng cho nhóm BOD tham gia xem/đánh giá/phỏng vấn |
| `M02_P0205.group_abu_recruitment` | ABU Recruitment Control | [security/approval_groups.xml:12](/d:/odoo-19.0+e.20250918/addons/M02_P0205/security/approval_groups.xml#L12) | `hr.group_hr_manager` | Dùng cho nhóm ABU tham gia xem/đánh giá/phỏng vấn |

Ghi chú:
- `group_hr_validator` imply ở [security/hr_validator_group.xml:6](/d:/odoo-19.0+e.20250918/addons/M02_P0205/security/hr_validator_group.xml#L6)
- 3 group còn lại imply ở [security/approval_groups.xml:6](/d:/odoo-19.0+e.20250918/addons/M02_P0205/security/approval_groups.xml#L6), [security/approval_groups.xml:10](/d:/odoo-19.0+e.20250918/addons/M02_P0205/security/approval_groups.xml#L10), [security/approval_groups.xml:14](/d:/odoo-19.0+e.20250918/addons/M02_P0205/security/approval_groups.xml#L14)

## 3. Tổng hợp ACL trong `ir.model.access.csv`

Nguồn: [security/ir.model.access.csv](/d:/odoo-19.0+e.20250918/addons/M02_P0205/security/ir.model.access.csv)

### 3.1 Các model đang mở full CRUD cho `base.group_user`

- `recruitment.request`
- `recruitment.plan`
- `recruitment.plan.line`
- `hr.applicant.evaluation`
- `hr.applicant.evaluation.line`
- `recruitment.batch`
- `recruitment.request.line`
- `recruitment.request.approver`

Tham chiếu:
- [ir.model.access.csv:2](/d:/odoo-19.0+e.20250918/addons/M02_P0205/security/ir.model.access.csv#L2)
- [ir.model.access.csv:4](/d:/odoo-19.0+e.20250918/addons/M02_P0205/security/ir.model.access.csv#L4)
- [ir.model.access.csv:6](/d:/odoo-19.0+e.20250918/addons/M02_P0205/security/ir.model.access.csv#L6)
- [ir.model.access.csv:8](/d:/odoo-19.0+e.20250918/addons/M02_P0205/security/ir.model.access.csv#L8)
- [ir.model.access.csv:10](/d:/odoo-19.0+e.20250918/addons/M02_P0205/security/ir.model.access.csv#L10)
- [ir.model.access.csv:12](/d:/odoo-19.0+e.20250918/addons/M02_P0205/security/ir.model.access.csv#L12)
- [ir.model.access.csv:14](/d:/odoo-19.0+e.20250918/addons/M02_P0205/security/ir.model.access.csv#L14)
- [ir.model.access.csv:16](/d:/odoo-19.0+e.20250918/addons/M02_P0205/security/ir.model.access.csv#L16)

### 3.2 Các model đang mở full CRUD cho `hr_recruitment.group_hr_recruitment_manager`

- `recruitment.request`
- `recruitment.plan`
- `recruitment.plan.line`
- `hr.applicant.evaluation`
- `hr.applicant.evaluation.line`
- `recruitment.batch`
- `recruitment.request.line`
- `recruitment.request.approver`

Tham chiếu:
- [ir.model.access.csv:3](/d:/odoo-19.0+e.20250918/addons/M02_P0205/security/ir.model.access.csv#L3)
- [ir.model.access.csv:5](/d:/odoo-19.0+e.20250918/addons/M02_P0205/security/ir.model.access.csv#L5)
- [ir.model.access.csv:7](/d:/odoo-19.0+e.20250918/addons/M02_P0205/security/ir.model.access.csv#L7)
- [ir.model.access.csv:9](/d:/odoo-19.0+e.20250918/addons/M02_P0205/security/ir.model.access.csv#L9)
- [ir.model.access.csv:11](/d:/odoo-19.0+e.20250918/addons/M02_P0205/security/ir.model.access.csv#L11)
- [ir.model.access.csv:13](/d:/odoo-19.0+e.20250918/addons/M02_P0205/security/ir.model.access.csv#L13)
- [ir.model.access.csv:15](/d:/odoo-19.0+e.20250918/addons/M02_P0205/security/ir.model.access.csv#L15)
- [ir.model.access.csv:17](/d:/odoo-19.0+e.20250918/addons/M02_P0205/security/ir.model.access.csv#L17)

### 3.3 Quyền đọc `survey.survey`

- `hr_recruitment.group_hr_recruitment_manager` có quyền đọc: [ir.model.access.csv:18](/d:/odoo-19.0+e.20250918/addons/M02_P0205/security/ir.model.access.csv#L18)
- `base.group_user` có quyền đọc: [ir.model.access.csv:19](/d:/odoo-19.0+e.20250918/addons/M02_P0205/security/ir.model.access.csv#L19)

## 4. Record rule / rule bảo mật

Tham chiếu: [security/recruitment_security.xml:4](/d:/odoo-19.0+e.20250918/addons/M02_P0205/security/recruitment_security.xml#L4)

File này không tạo group mới, nhưng có chỉnh rule chuẩn `hr.hr_job_comp_rule`:
- cập nhật `domain_force`
- cho phép job có `website_published = True` được bypass một phần điều kiện company

Đây là phần liên quan đến bảo mật truy cập dữ liệu, không phải định nghĩa nhóm quyền mới.

## 5. Các view có dùng `groups=...`

### 5.1 Recruitment request

- [views/recruitment_request_views.xml:52](/d:/odoo-19.0+e.20250918/addons/M02_P0205/views/recruitment_request_views.xml#L52)
  - field `user_id` có `groups="base.group_user"`
- [views/recruitment_request_views.xml:54](/d:/odoo-19.0+e.20250918/addons/M02_P0205/views/recruitment_request_views.xml#L54)
  - field `company_id` có `groups="base.group_user"`

### 5.2 Applicant

- [views/hr_applicant_views.xml:42](/d:/odoo-19.0+e.20250918/addons/M02_P0205/views/hr_applicant_views.xml#L42)
  - `hr_recruitment.group_hr_recruitment_user`, `M02_P0205.group_bod_recruitment`
- [views/hr_applicant_views.xml:48](/d:/odoo-19.0+e.20250918/addons/M02_P0205/views/hr_applicant_views.xml#L48)
  - `hr_recruitment.group_hr_recruitment_user`, `M02_P0205.group_abu_recruitment`
- [views/hr_applicant_views.xml:63](/d:/odoo-19.0+e.20250918/addons/M02_P0205/views/hr_applicant_views.xml#L63)
  - `hr_recruitment.group_hr_recruitment_user`, `M02_P0205.group_bod_recruitment`
- [views/hr_applicant_views.xml:68](/d:/odoo-19.0+e.20250918/addons/M02_P0205/views/hr_applicant_views.xml#L68)
  - `hr_recruitment.group_hr_recruitment_user`, `M02_P0205.group_abu_recruitment`
- [views/hr_applicant_views.xml:469](/d:/odoo-19.0+e.20250918/addons/M02_P0205/views/hr_applicant_views.xml#L469)
  - `hr_recruitment.group_hr_recruitment_user`, `M02_P0205.group_bod_recruitment`
- [views/hr_applicant_views.xml:630](/d:/odoo-19.0+e.20250918/addons/M02_P0205/views/hr_applicant_views.xml#L630)
  - `hr_recruitment.group_hr_recruitment_user`, `M02_P0205.group_abu_recruitment`

## 6. Các chỗ trong Python đang dùng group

### 6.1 Luồng duyệt yêu cầu tuyển dụng

- [models/recruitment_request.py:117](/d:/odoo-19.0+e.20250918/addons/M02_P0205/models/recruitment_request.py#L117)
  - lấy group `M02_P0205.group_hr_validator`
- [models/recruitment_request.py:119](/d:/odoo-19.0+e.20250918/addons/M02_P0205/models/recruitment_request.py#L119)
  - nếu không có thì fallback sang `hr.group_hr_manager`
- [models/recruitment_request.py:129](/d:/odoo-19.0+e.20250918/addons/M02_P0205/models/recruitment_request.py#L129)
  - lấy group `M02_P0205.group_ceo_recruitment`

Bản sao trong `office/`:
- [office/models/recruitment_request.py:117](/d:/odoo-19.0+e.20250918/addons/M02_P0205/office/models/recruitment_request.py#L117)
- [office/models/recruitment_request.py:119](/d:/odoo-19.0+e.20250918/addons/M02_P0205/office/models/recruitment_request.py#L119)
- [office/models/recruitment_request.py:129](/d:/odoo-19.0+e.20250918/addons/M02_P0205/office/models/recruitment_request.py#L129)

### 6.2 Luồng interviewer / evaluation

- [models/hr_job.py:100](/d:/odoo-19.0+e.20250918/addons/M02_P0205/models/hr_job.py#L100)
  - lấy user thuộc `M02_P0205.group_bod_recruitment`
- [models/hr_job.py:101](/d:/odoo-19.0+e.20250918/addons/M02_P0205/models/hr_job.py#L101)
  - lấy user thuộc `M02_P0205.group_abu_recruitment`

- [models/hr_applicant.py:1533](/d:/odoo-19.0+e.20250918/addons/M02_P0205/models/hr_applicant.py#L1533)
  - lấy danh sách user của group BOD
- [models/hr_applicant.py:1534](/d:/odoo-19.0+e.20250918/addons/M02_P0205/models/hr_applicant.py#L1534)
  - lấy danh sách user của group ABU
- [models/hr_applicant.py:1572](/d:/odoo-19.0+e.20250918/addons/M02_P0205/models/hr_applicant.py#L1572)
  - lấy lại group BOD theo từng record
- [models/hr_applicant.py:1573](/d:/odoo-19.0+e.20250918/addons/M02_P0205/models/hr_applicant.py#L1573)
  - lấy lại group ABU theo từng record
- [models/hr_applicant.py:1662](/d:/odoo-19.0+e.20250918/addons/M02_P0205/models/hr_applicant.py#L1662)
  - dùng `group_bod_recruitment`
- [models/hr_applicant.py:1674](/d:/odoo-19.0+e.20250918/addons/M02_P0205/models/hr_applicant.py#L1674)
  - dùng `group_abu_recruitment`

Bản sao trong `office/`:
- [office/models/hr_job.py:183](/d:/odoo-19.0+e.20250918/addons/M02_P0205/office/models/hr_job.py#L183)
- [office/models/hr_job.py:184](/d:/odoo-19.0+e.20250918/addons/M02_P0205/office/models/hr_job.py#L184)
- [office/models/hr_applicant.py:1434](/d:/odoo-19.0+e.20250918/addons/M02_P0205/office/models/hr_applicant.py#L1434)
- [office/models/hr_applicant.py:1435](/d:/odoo-19.0+e.20250918/addons/M02_P0205/office/models/hr_applicant.py#L1435)
- [office/models/hr_applicant.py:1473](/d:/odoo-19.0+e.20250918/addons/M02_P0205/office/models/hr_applicant.py#L1473)
- [office/models/hr_applicant.py:1474](/d:/odoo-19.0+e.20250918/addons/M02_P0205/office/models/hr_applicant.py#L1474)
- [office/models/hr_applicant.py:1563](/d:/odoo-19.0+e.20250918/addons/M02_P0205/office/models/hr_applicant.py#L1563)
- [office/models/hr_applicant.py:1575](/d:/odoo-19.0+e.20250918/addons/M02_P0205/office/models/hr_applicant.py#L1575)

### 6.3 Check group HR chung

- [models/recruitment_plan.py:475](/d:/odoo-19.0+e.20250918/addons/M02_P0205/models/recruitment_plan.py#L475)
  - check `hr.group_hr_manager` hoặc `hr.group_hr_user`
- [office/models/recruitment_plan.py:475](/d:/odoo-19.0+e.20250918/addons/M02_P0205/office/models/recruitment_plan.py#L475)
  - check `hr.group_hr_manager` hoặc `hr.group_hr_user`

## 7. Data mẫu có gán nhóm quyền

Nguồn: [data/hr_employee_sample_data.xml](/d:/odoo-19.0+e.20250918/addons/M02_P0205/data/hr_employee_sample_data.xml)

- [hr_employee_sample_data.xml:10](/d:/odoo-19.0+e.20250918/addons/M02_P0205/data/hr_employee_sample_data.xml#L10)
  - user mẫu marketing được gán `base.group_user`, `hr.group_hr_manager`
- [hr_employee_sample_data.xml:25](/d:/odoo-19.0+e.20250918/addons/M02_P0205/data/hr_employee_sample_data.xml#L25)
  - user mẫu HR được gán `base.group_user`, `hr.group_hr_manager`
- [hr_employee_sample_data.xml:40](/d:/odoo-19.0+e.20250918/addons/M02_P0205/data/hr_employee_sample_data.xml#L40)
  - user mẫu CEO được gán `base.group_user`, `base.group_system`

## 8. Tóm tắt nhanh

- Module `0205` đang định nghĩa 4 group custom:
  - `group_hr_validator`
  - `group_ceo_recruitment`
  - `group_bod_recruitment`
  - `group_abu_recruitment`
- Cả 4 group custom hiện đều imply `hr.group_hr_manager`
- ACL hiện đang mở khá rộng cho `base.group_user` trên nhiều model custom
- View và logic interview/evaluation phụ thuộc nhiều vào `group_bod_recruitment` và `group_abu_recruitment`
- Luồng duyệt yêu cầu tuyển dụng phụ thuộc vào `group_hr_validator` và `group_ceo_recruitment`
