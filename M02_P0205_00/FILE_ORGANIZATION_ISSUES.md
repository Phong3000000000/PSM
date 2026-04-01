# Danh sách file sai vị trí & trùng lặp trong module M02_P0205_00

**Ngày kiểm tra:** 2026-03-20

## 1. File nằm sai thư mục
- `views/recruitment_plan.py` (đúng ra phải nằm ở `models/` hoặc bị xóa nếu đã có ở models)

## 2. Cặp file trùng lặp nội dung
- `models/recruitment_plan.py`  
- `views/recruitment_plan.py`

**So sánh nội dung:**
- Nội dung hai file này là giống nhau (đều là định nghĩa model Odoo, không phải view XML).

## 3. Đề xuất xử lý
- **Giữ lại:** `models/recruitment_plan.py` (chuẩn Odoo)
- **Xóa:** `views/recruitment_plan.py` (sai vị trí, gây nhầm lẫn)

---
Nếu cần kiểm tra thêm các file khác hoặc thực hiện xóa file, hãy xác nhận lại yêu cầu.