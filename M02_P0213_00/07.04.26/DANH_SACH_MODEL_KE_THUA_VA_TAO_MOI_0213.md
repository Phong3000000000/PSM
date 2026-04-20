# Danh sách model kế thừa và model tạo mới của 0213

## Phạm vi kiểm tra

- Module: `M02_P0213_00`
- Thư mục đã quét: `models/`
- Đối chiếu thêm: `security/ir.model.access.csv`
- Tiêu chí:
  - Model kế thừa: class sử dụng `_inherit = '...'`
  - Model tạo mới hoàn toàn: class sử dụng `_name = '...'`

## 1. Các model được kế thừa/mở rộng từ Odoo

| STT | File | Class | Model được kế thừa | Module gốc tham chiếu |
| --- | --- | --- | --- | --- |
| 1 | `models/resignation_request.py` | `ApprovalCategory` | `approval.category` | `approvals` |
| 2 | `models/resignation_request.py` | `ResignationRequest` | `approval.request` | `approvals` |
| 3 | `models/mail_activity.py` | `MailActivity` | `mail.activity` | `mail` |
| 4 | `models/survey_user_input.py` | `SurveyUserInput` | `survey.user_input` | `survey` |

## 2. Các model được tạo mới hoàn toàn trong 0213

Không có model nào được tạo mới hoàn toàn trong module `M02_P0213_00`.

## 3. Kết luận

- Module `0213` hiện tại chỉ mở rộng model sẵn có của Odoo.
- Không tìm thấy bất kỳ khai báo `_name = '...'` nào trong các file Python của module.
- File `security/ir.model.access.csv` cũng không cho thấy dấu hiệu có model custom mới của `0213`.

## 4. Nguồn xác nhận

- `addons/M02_P0213_00/models/resignation_request.py`
- `addons/M02_P0213_00/models/mail_activity.py`
- `addons/M02_P0213_00/models/survey_user_input.py`
- `addons/M02_P0213_00/security/ir.model.access.csv`
