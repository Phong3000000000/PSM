# PHASE 5 - KẾT QUẢ TÁCH LOGIC VÀ LÀM SẠCH CẤU TRÚC MODULE 0213

## 1. Mục tiêu Phase 5

Phase 5 tập trung xử lý các bất hợp lý về cấu trúc và logic trùng lặp trong module `0213`, nhằm:

- giảm trùng code
- đưa mã nguồn về đúng vị trí chức năng
- giảm rủi ro bảo trì và nhầm lẫn khi tiếp tục refactor các phase sau

## 2. Vấn đề được xác định

Qua rà soát module, phát hiện điểm bất hợp lý lớn nhất:

- `controllers/main.py` và `views/main.py` là hai file Python có nội dung trùng nhau gần như hoàn toàn
- `views/main.py` là controller Python nhưng lại nằm trong thư mục `views/`, không đúng vai trò kỹ thuật
- logic lấy employee, category, request hiện tại và link survey đang lặp lại trong cùng một controller

## 3. Thay đổi đã thực hiện

### 3.1. Loại bỏ file Python đặt sai vị trí

Đã xóa file:

- `views/main.py`

Lý do:

- file này không phải XML view
- nội dung trùng hoàn toàn với controller portal
- giữ lại sẽ làm tăng nguy cơ hiểu sai cấu trúc module và dễ bị chỉnh lệch giữa hai nơi

### 3.2. Chuẩn hóa controller portal

Đã refactor file:

- `controllers/main.py`

Theo hướng tách helper nội bộ cho các logic lặp:

- `_get_portal_employee()`
- `_get_resignation_category()`
- `_get_latest_resignation_request(category)`
- `_get_resignation_types()`
- `_get_resignation_activities(resignation_request)`
- `_get_or_create_exit_survey_url(resignation_request)`

Kết quả:

- route portal ngắn gọn hơn
- logic đọc dễ hơn
- giảm lặp code giữa luồng hiển thị form và luồng submit
- việc bảo trì các truy vấn portal trong phase sau sẽ tập trung tại một nơi

## 4. Phạm vi file bị tác động

- `controllers/main.py`
- xóa `views/main.py`

## 5. Kiểm tra sau refactor

Đã kiểm tra:

- `controllers/main.py` còn tồn tại và là nơi duy nhất chứa portal controller
- `views/main.py` không còn tồn tại
- `py_compile` pass cho:
  - `controllers/main.py`
  - `models/resignation_request.py`
  - `models/mail_activity.py`
  - `models/survey_user_input.py`

## 6. Đánh giá kết quả

Phase 5 đã xử lý xong bất hợp lý cấu trúc rõ ràng nhất của module:

- bỏ trùng controller giữa `controllers/` và `views/`
- gom logic dùng chung trong portal controller
- giữ nguyên hành vi nghiệp vụ hiện tại, chỉ làm sạch cấu trúc và điểm lặp

## 7. Tồn đọng chuyển phase sau

Một số nội dung vẫn nên tiếp tục xử lý ở các phase kế tiếp:

- rà lại permission và access cho các luồng portal
- rà chất lượng comment/log/message trong code
- đánh giá tiếp khả năng tách thêm một phần nghiệp vụ từ controller sang model/service nếu cần
- kiểm tra cài mới module trên DB sạch và chạy smoke test end-to-end
