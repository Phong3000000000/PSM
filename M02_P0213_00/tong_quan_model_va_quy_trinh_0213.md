# Tổng quan model và luồng quy trình module 0213

## 1. Các model được sử dụng

### Model có sẵn của Odoo (built-in)
- `hr.employee`: Thông tin nhân viên.
- `approval.category`: Danh mục loại phê duyệt.
- `approval.request`: Yêu cầu phê duyệt (được kế thừa để làm yêu cầu nghỉ việc).
- `mail.activity`: Hoạt động/checklist (được kế thừa để quản lý checklist offboarding).
- `mail.activity.plan`, `mail.activity.plan.template`: Kế hoạch và template checklist hoạt động.
- `survey.survey`, `survey.question`, `survey.question.answer`: Bộ câu hỏi khảo sát.
- `survey.user_input`: Kết quả khảo sát của từng nhân viên.
- `hr.departure.reason`: Danh mục lý do nghỉ việc.
- `ir.cron`: Định nghĩa các cron job nhắc nhở.

### Model được mở rộng/định nghĩa mới trong module
- `approval.category` (thêm field `is_offboarding`)
- `approval.request` (thêm các trường về nghỉ việc, compute, liên kết employee, trạng thái, v.v.)
- `mail.activity` (thêm logic trạng thái, ngăn xóa, archive thay vì xóa)
- `survey.user_input` (thêm logic đánh dấu hoàn thành exit interview)

---

## 2. Luồng đi và tương tác giữa các model

### Bước 1: Nhân viên tạo yêu cầu nghỉ việc
- Model: `approval.request` (được mở rộng)
- Tạo mới bản ghi yêu cầu nghỉ việc, chọn lý do (`hr.departure.reason`), ngày nghỉ dự kiến, v.v.
- Liên kết với `hr.employee` (người nghỉ việc).

### Bước 2: Duyệt yêu cầu nghỉ việc
- Model: `approval.request`, `approval.category`
- Yêu cầu được duyệt qua các bước phê duyệt (manager, HR, ...).

### Bước 3: Sinh checklist offboarding
- Khi yêu cầu nghỉ việc được duyệt, hệ thống sinh các hoạt động/checklist offboarding cho nhân viên.
- Model: `mail.activity.plan`, `mail.activity.plan.template` (master data checklist)
- Tạo các bản ghi `mail.activity` gắn với nhân viên và yêu cầu nghỉ việc.

### Bước 4: Thực hiện và theo dõi checklist
- Model: `mail.activity`
- Các bộ phận thực hiện từng hoạt động (thu hồi tài sản, bàn giao, ...).
- Trạng thái hoạt động được cập nhật (pending, overdue, done).

### Bước 5: Khảo sát exit interview
- Khi gần hoàn thành checklist, hệ thống gửi khảo sát exit interview cho nhân viên.
- Model: `survey.survey` (bộ câu hỏi), `survey.user_input` (kết quả khảo sát).
- Khi nhân viên hoàn thành khảo sát, hệ thống đánh dấu đã hoàn thành exit interview.

### Bước 6: Kết thúc quy trình
- Khi tất cả checklist hoàn thành và khảo sát đã làm, yêu cầu nghỉ việc chuyển trạng thái hoàn tất.

---

## 3. Công dụng của các model chính

| Model                    | Công dụng chính                                                                 |
|--------------------------|--------------------------------------------------------------------------------|
| approval.request         | Lưu trữ yêu cầu nghỉ việc, trạng thái, liên kết nhân viên, lý do nghỉ, ...     |
| approval.category        | Định nghĩa loại phê duyệt (ở đây là nghỉ việc/offboarding)                     |
| mail.activity            | Quản lý các hoạt động/checklist offboarding cho từng yêu cầu nghỉ việc         |
| mail.activity.plan/template | Định nghĩa các checklist mẫu cho offboarding                              |
| hr.employee              | Thông tin nhân viên liên quan đến yêu cầu nghỉ việc                            |
| hr.departure.reason      | Danh mục lý do nghỉ việc                                                       |
| survey.survey            | Bộ câu hỏi khảo sát exit interview                                             |
| survey.user_input        | Kết quả khảo sát exit interview của từng nhân viên                             |
| ir.cron                  | Tự động gửi nhắc nhở các hoạt động chưa hoàn thành                            |

---

## 4. Phân loại model

| Model                    | Loại           | Ghi chú                                  |
|--------------------------|----------------|------------------------------------------|
| approval.request         | Built-in + mở rộng | Kế thừa, thêm trường, logic nghỉ việc   |
| approval.category        | Built-in + mở rộng | Thêm field is_offboarding               |
| mail.activity            | Built-in + mở rộng | Thêm logic trạng thái, archive          |
| mail.activity.plan       | Built-in       | Master checklist                        |
| mail.activity.plan.template | Built-in    | Master checklist template               |
| hr.employee              | Built-in       | Nhân viên                               |
| hr.departure.reason      | Built-in       | Lý do nghỉ việc                         |
| survey.survey            | Built-in       | Bộ câu hỏi khảo sát                     |
| survey.user_input        | Built-in + mở rộng | Thêm logic đánh dấu hoàn thành khảo sát |
| ir.cron                  | Built-in       | Cron job nhắc nhở                       |
