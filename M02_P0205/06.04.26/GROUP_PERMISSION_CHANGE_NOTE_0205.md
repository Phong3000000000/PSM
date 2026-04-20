# Ghi chú chỉnh sửa nhóm quyền module 0205

## 1. Kết luận ngắn

Có, module `M02_P0205` nên được chỉnh lại một phần về nhóm quyền và phân quyền.

Lý do chính:
- ACL hiện đang mở quá rộng cho `base.group_user` trên nhiều model custom
- các group custom hiện đều `imply` `hr.group_hr_manager`, dễ làm quyền bị nở quá mức
- nhiều chỗ đang dựa vào `groups` ở view hoặc điều hướng activity, nhưng chưa siết đủ ở tầng backend
- chưa thấy record rule riêng cho các model custom quan trọng

Tuy nhiên, không nên sửa một lần theo kiểu “siết hết” vì có thể làm gãy flow nghiệp vụ hiện tại. Nên sửa theo từng lớp, ưu tiên lớp rủi ro cao trước.

## 2. Những phần nên sửa

### 2.1 Siết ACL cho `base.group_user`

Hiện trạng:
- `base.group_user` đang có full CRUD trên nhiều model custom như:
  - `recruitment.request`
  - `recruitment.plan`
  - `recruitment.plan.line`
  - `hr.applicant.evaluation`
  - `hr.applicant.evaluation.line`
  - `recruitment.batch`
  - `recruitment.request.line`
  - `recruitment.request.approver`

Rủi ro:
- bất kỳ user nội bộ nào cũng có thể tạo/sửa/xóa dữ liệu nghiệp vụ tuyển dụng
- phạm vi quyền không phản ánh đúng vai trò thực tế của HR, CEO, BOD, ABU, requester

Hướng sửa:
- giảm quyền của `base.group_user` xuống mức tối thiểu cần thiết
- chỉ giữ `read` hoặc `read/create` ở các model thật sự cần cho user nội bộ phổ thông
- chuyển quyền `write/unlink` sang các group chuyên trách hơn

Gợi ý mức ưu tiên:
- ưu tiên rà trước các model:
  - `recruitment.request`
  - `recruitment.plan`
  - `hr.applicant.evaluation`
  - `recruitment.batch`

## 2.2 Rà lại việc `imply` từ group custom sang `hr.group_hr_manager`

Hiện trạng:
- `group_hr_validator`
- `group_ceo_recruitment`
- `group_bod_recruitment`
- `group_abu_recruitment`

đều đang imply `hr.group_hr_manager`.

Rủi ro:
- user chỉ cần được gán vai trò CEO/BOD/ABU trong flow tuyển dụng nhưng lại tự động có thêm quyền HR Manager
- dễ phát sinh quyền ngoài ý định, nhất là với màn hình và nghiệp vụ thuộc HR

Hướng sửa:
- xem lại từng group custom có thật sự cần imply `hr.group_hr_manager` hay không
- nhiều khả năng nên bỏ imply đối với:
  - `group_ceo_recruitment`
  - `group_bod_recruitment`
  - `group_abu_recruitment`
- `group_hr_validator` có thể vẫn giữ hoặc thay bằng group HR phù hợp hơn, cần xác nhận nghiệp vụ

Lưu ý:
- đây là thay đổi nhạy cảm, cần test lại các view, button và luồng activity sau khi bỏ imply

## 2.3 Bổ sung record rule cho model custom

Hiện trạng:
- chưa thấy record rule riêng rõ ràng cho các model custom chính

Rủi ro:
- nếu ACL vẫn mở rộng, user có thể thấy và thao tác bản ghi không thuộc phạm vi của mình
- hệ thống đang phụ thuộc nhiều vào giao diện và domain trong code hơn là rule dữ liệu chuẩn

Hướng sửa:
- bổ sung record rule cho các model chính theo phạm vi nghiệp vụ
- ví dụ các hướng rule có thể cần:
  - user chỉ thấy request do mình tạo hoặc thuộc phạm vi phụ trách
  - HR thấy các bản ghi tuyển dụng trong phạm vi HR
  - BOD/ABU chỉ thấy phần liên quan vòng phỏng vấn của họ

Lưu ý:
- phần này cần xác nhận kỹ với nghiệp vụ trước khi code, vì record rule ảnh hưởng rất mạnh đến khả năng nhìn dữ liệu

## 2.4 Bổ sung check quyền ở backend cho các action quan trọng

Hiện trạng:
- một số action đang bị khống chế chủ yếu bằng `groups` ở view hoặc `state`
- note security cũ cũng chỉ ra rằng lớp bảo vệ backend chưa nhất quán ở tất cả action

Rủi ro:
- nếu gọi method trực tiếp từ RPC/server action/import script thì vẫn có thể đi qua
- view ẩn nút không đồng nghĩa với việc backend đã chặn quyền

Hướng sửa:
- thêm kiểm tra quyền/nhóm trong các method action quan trọng
- ưu tiên các action liên quan:
  - chuyển bước phỏng vấn
  - gửi thư / gửi khảo sát / gửi lịch phỏng vấn
  - tạo đánh giá interview
  - xác nhận offer / hired

Nguyên tắc:
- view dùng để hỗ trợ UX
- backend mới là nơi chặn quyền thật sự

## 2.5 Rà lại phân quyền ở `hr_applicant_views.xml`

Hiện trạng:
- file này đang là nơi dùng `groups` nhiều nhất
- đặc biệt liên quan tới:
  - `hr_recruitment.group_hr_recruitment_user`
  - `group_bod_recruitment`
  - `group_abu_recruitment`

Rủi ro:
- nếu group custom bị đổi hoặc bỏ imply, các nút hiện tại có thể biến mất hoặc lệch quyền
- nếu chỉ chặn ở view, logic backend vẫn có thể chưa đủ chặt

Hướng sửa:
- giữ `groups` ở view để phân tách thao tác theo vai trò
- nhưng phải đồng bộ lại với:
  - ACL mới
  - record rule mới
  - check quyền ở Python

## 2.6 Rà lại data mẫu liên quan đến group

Hiện trạng:
- data mẫu vẫn đang gán:
  - `base.group_user`
  - `hr.group_hr_manager`
  - `base.group_system`

Rủi ro:
- dễ làm người test hiểu sai mô hình quyền thật
- data mẫu vô tình cấp quyền quá mạnh

Hướng sửa:
- giữ data mẫu đơn giản, chỉ gán group nếu thực sự phục vụ test flow
- tránh dùng `base.group_system` nếu không thật sự cần cho demo
- nếu cần user demo cho CEO/BOD/ABU thì nên gán đúng group custom thay vì mượn quyền HR/System

## 3. Những phần chưa nên sửa ngay

### 3.1 `recruitment_security.xml`

File này đang sửa rule `hr.hr_job_comp_rule` để phục vụ job publish trên website.

Đánh giá:
- có liên quan đến security
- nhưng không phải trọng tâm của bài toán “group quyền nội bộ”

Kết luận:
- chưa nên đụng vào nếu mục tiêu hiện tại là rà nhóm quyền và ACL nội bộ
- chỉ rà lại nếu có bug về nhìn thấy job giữa các company hoặc public website

### 3.2 Controller public dùng `sudo()`

Đây là vấn đề security thật, nhưng là nhánh riêng.

Kết luận:
- nên tạo workstream riêng để rà controller
- không nên gộp chung với đợt chỉnh group/ACL nội bộ đầu tiên

## 4. Đề xuất thứ tự sửa

### Pha 1: Sửa an toàn, ít phá flow

- lập ma trận vai trò thực tế cho:
  - requester
  - HR user
  - HR validator
  - CEO approver
  - BOD interviewer
  - ABU interviewer
- giảm ACL của `base.group_user`
- giữ nguyên view trước, chưa thay mạnh phần button

### Pha 2: Sửa cấu trúc group

- rà từng group custom có còn cần imply `hr.group_hr_manager` hay không
- bỏ imply ở các group không cần quyền HR thật sự
- cập nhật lại user test / sample data nếu cần

### Pha 3: Sửa backend chắc chắn hơn

- bổ sung check quyền trong các method action chính
- thêm record rule cho các model quan trọng
- test lại các flow end-to-end

## 5. Danh sách file dự kiến sẽ sửa

### Security

- [security/ir.model.access.csv](/d:/odoo-19.0+e.20250918/addons/M02_P0205/security/ir.model.access.csv)
- [security/hr_validator_group.xml](/d:/odoo-19.0+e.20250918/addons/M02_P0205/security/hr_validator_group.xml)
- [security/approval_groups.xml](/d:/odoo-19.0+e.20250918/addons/M02_P0205/security/approval_groups.xml)

### Views

- [views/hr_applicant_views.xml](/d:/odoo-19.0+e.20250918/addons/M02_P0205/views/hr_applicant_views.xml)
- [views/recruitment_request_views.xml](/d:/odoo-19.0+e.20250918/addons/M02_P0205/views/recruitment_request_views.xml)

### Python

- [models/recruitment_request.py](/d:/odoo-19.0+e.20250918/addons/M02_P0205/models/recruitment_request.py)
- [models/hr_applicant.py](/d:/odoo-19.0+e.20250918/addons/M02_P0205/models/hr_applicant.py)
- [models/hr_job.py](/d:/odoo-19.0+e.20250918/addons/M02_P0205/models/hr_job.py)
- [models/recruitment_plan.py](/d:/odoo-19.0+e.20250918/addons/M02_P0205/models/recruitment_plan.py)

### Data mẫu

- [data/hr_employee_sample_data.xml](/d:/odoo-19.0+e.20250918/addons/M02_P0205/data/hr_employee_sample_data.xml)

## 6. Kết luận hành động

Nếu chỉ trả lời câu hỏi “có cần chỉnh không”, thì câu trả lời là: có.

Nếu hỏi “nên bắt đầu từ đâu”, thì nên bắt đầu từ:
- siết `base.group_user` trong ACL
- rà lại việc các group custom đang imply `hr.group_hr_manager`
- sau đó mới đến record rule và backend permission check
