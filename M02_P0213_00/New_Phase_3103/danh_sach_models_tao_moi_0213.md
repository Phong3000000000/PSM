# Danh sách model tạo mới trong module 0213

## Kết luận

Module `M02_P0213_00` không tạo mới model nào.

Sau khi kiểm tra các file trong thư mục `models/` và đối chiếu với `security/ir.model.access.csv`, tất cả class trong module đều sử dụng `_inherit` để mở rộng model có sẵn của Odoo, không có class nào khai báo `_name` để tạo model mới.

## Các model được mở rộng

| File | Class | Model |
| --- | --- | --- |
| `models/resignation_request.py` | `ApprovalCategory` | `approval.category` |
| `models/resignation_request.py` | `ResignationRequest` | `approval.request` |
| `models/survey_user_input.py` | `SurveyUserInput` | `survey.user_input` |
| `models/mail_activity.py` | `MailActivity` | `mail.activity` |

## Ghi chú kiểm tra

- Không tìm thấy bất kỳ khai báo `_name = '...'` nào trong `addons/M02_P0213_00`.
- File `security/ir.model.access.csv` cũng chỉ cấp quyền cho các model có sẵn như `approval.request`, `mail.activity`, `hr.employee`, `survey.user_input`, `survey.survey`, `survey.question`, `survey.question.answer`, `hr.contract.type`, `hr.departure.reason`.
- Vì vậy, phạm vi model của module 0213 là mở rộng hành vi và bổ sung field/method cho model sẵn có, không phải định nghĩa model mới.
