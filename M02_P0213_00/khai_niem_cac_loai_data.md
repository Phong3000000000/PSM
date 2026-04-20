# Khái niệm các loại Data trong Odoo module

## 1. Master Data (Dữ liệu danh mục chính)
- **Định nghĩa:**
  - Là các dữ liệu nền tảng, dùng để tham chiếu hoặc cấu hình cho các nghiệp vụ trong hệ thống.
  - Thường là các danh mục, bảng tra cứu, cấu hình mẫu, không thay đổi thường xuyên.
  - Được tạo ra bởi admin hoặc qua file data khi cài đặt module.
- **Ví dụ:**
  - Danh mục loại phê duyệt (`approval.category`)
  - Kế hoạch hoạt động offboarding (`mail.activity.plan`)
  - Bộ câu hỏi khảo sát mẫu (`survey.survey`)
  - Mẫu email (`mail.template`)

## 2. Ref Data (Dữ liệu tham chiếu)
- **Định nghĩa:**
  - Là các dữ liệu dùng để liên kết, tham chiếu giữa các bảng/model với nhau.
  - Thường xuất hiện ở các trường Many2one, One2many, Many2many.
  - Có thể là master data hoặc transaction data của module khác, nhưng đóng vai trò tham chiếu ở module hiện tại.
- **Ví dụ:**
  - Tham chiếu nhân viên (`hr.employee`) trong yêu cầu nghỉ việc
  - Tham chiếu lý do nghỉ việc (`hr.departure.reason`)
  - Tham chiếu đến các bản ghi survey, activity, ...

## 3. Transaction Data (Dữ liệu giao dịch/nghiệp vụ)
- **Định nghĩa:**
  - Là các dữ liệu phát sinh trong quá trình vận hành, phản ánh các nghiệp vụ thực tế.
  - Được tạo ra bởi người dùng hoặc hệ thống khi thực hiện các thao tác nghiệp vụ.
  - Thường xuyên thay đổi, cập nhật, có thể bị xóa hoặc lưu trữ lâu dài.
- **Ví dụ:**
  - Yêu cầu nghỉ việc của nhân viên (`approval.request`)
  - Các hoạt động/checklist offboarding thực tế (`mail.activity`)
  - Kết quả khảo sát exit interview của từng nhân viên (`survey.user_input`)

---

## Tóm tắt
- **Master Data:** Dữ liệu nền tảng, cấu hình, danh mục dùng chung.
- **Ref Data:** Dữ liệu dùng để liên kết/tham chiếu giữa các model.
- **Transaction Data:** Dữ liệu phát sinh từ nghiệp vụ thực tế, phản ánh hoạt động của hệ thống.
