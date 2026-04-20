# Phân loại Data trong module M02_P0213_00

## 1. Master Data (Dữ liệu danh mục chính)
- **approval_category_data.xml**: Tạo bản ghi cho `approval.category` (ví dụ: "Yêu cầu nghỉ việc").
  - Model: `approval.category`
  - Loại: Master data (danh mục loại phê duyệt, dùng lâu dài, ít thay đổi).

- **offboarding_activity_plan_data.xml**: Tạo bản ghi cho `mail.activity.plan` và các template hoạt động offboarding.
  - Model: `mail.activity.plan`, `mail.activity.plan.template`
  - Loại: Master data (kế hoạch hoạt động mẫu cho offboarding).

- **survey_exit_interview_data.xml**: Tạo survey mẫu cho exit interview.
  - Model: `survey.survey`, `survey.question`, `survey.question.answer`
  - Loại: Master data (bộ câu hỏi khảo sát mẫu).

## 2. Ref Data (Dữ liệu tham chiếu)
- Không có file ref data riêng biệt trong các file data, nhưng có thể có các trường Many2one tham chiếu đến các model khác như `hr.employee`, `hr.departure.reason` (danh mục lý do nghỉ việc),...
  - Các trường Many2one trong model là ref data (ví dụ: `resignation_reason_id`).

## 3. Transaction Data (Dữ liệu giao dịch/nghiệp vụ)
- **resignation_request.py**: Model `approval.request` (được kế thừa và mở rộng) lưu các yêu cầu nghỉ việc của nhân viên.
  - Model: `approval.request`
  - Loại: Transaction data (mỗi bản ghi là một giao dịch nghỉ việc).

- **mail_activity.py**: Model `mail.activity` (được kế thừa) lưu các hoạt động/checklist liên quan đến offboarding.
  - Model: `mail.activity`
  - Loại: Transaction data (các hoạt động thực tế phát sinh theo từng yêu cầu nghỉ việc).

- **survey_user_input.py**: Model `survey.user_input` lưu kết quả khảo sát exit interview của từng nhân viên.
  - Model: `survey.user_input`
  - Loại: Transaction data (kết quả khảo sát thực tế).

## 4. Các data khác
- **email_template_*.xml**: Các mẫu email (`mail.template`) dùng để gửi thông báo, nhắc nhở.
  - Model: `mail.template`
  - Loại: Master data (mẫu dùng chung, không thay đổi thường xuyên).

- **ir_cron_data.xml**: Định nghĩa cron job nhắc nhở offboarding.
  - Model: `ir.cron`
  - Loại: Master data (cấu hình hệ thống).

---

## Tổng hợp mapping model ↔ loại data

| Model                    | Loại data         | File tạo data mẫu           |
|--------------------------|-------------------|-----------------------------|
| approval.category        | Master data       | approval_category_data.xml  |
| mail.activity.plan       | Master data       | offboarding_activity_plan_data.xml |
| mail.activity.plan.template | Master data    | offboarding_activity_plan_data.xml |
| survey.survey            | Master data       | survey_exit_interview_data.xml |
| survey.question          | Master data       | survey_exit_interview_data.xml |
| survey.question.answer   | Master data       | survey_exit_interview_data.xml |
| mail.template            | Master data       | email_template_*.xml        |
| ir.cron                  | Master data       | ir_cron_data.xml            |
| approval.request         | Transaction data  | (do người dùng tạo qua UI)  |
| mail.activity            | Transaction data  | (phát sinh theo quy trình)  |
| survey.user_input        | Transaction data  | (phát sinh khi nhân viên làm khảo sát) |
| hr.departure.reason      | Ref data          | (tham chiếu, không tạo ở đây)|

Nếu cần chi tiết về từng trường hoặc logic sinh data, có thể xem sâu hơn vào từng file model hoặc data.
