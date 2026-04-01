# Daily Report

**Ngày:** 17/03/2026

**Dự án:** Odoo HR Recruitment / Backbone 0200 / Flow 0205 / Mail Activity / Calendar

**Chi tiết kỹ thuật:**
- Hoàn thiện logic lấy giá trị thời gian mà ứng viên chọn từ email/survey và map trực tiếp vào lịch phỏng vấn lần 1 của ứng viên, đảm bảo dữ liệu lịch hẹn được đồng bộ đúng theo lựa chọn thực tế.
- Bổ sung `activity` gửi đến HR và Trưởng phòng khi ứng viên hoàn tất chọn lịch, giúp bộ phận liên quan theo dõi và xử lý xác nhận phỏng vấn kịp thời.
- Tạo `activity` phản hồi đến ứng viên sau khi HR xác nhận lịch, hoàn thiện vòng đời thông báo hai chiều trong flow tuyển dụng.
- Tích hợp module backbone `0200`, đồng thời điều chỉnh lại cách phân loại tuyển dụng để phù hợp với cấu trúc và logic dùng chung từ backbone.
- Kiểm thử lại flow `0205` sau tích hợp nhằm đảm bảo các bước xử lý ứng viên, lịch hẹn và thông báo không bị ảnh hưởng bởi thay đổi từ backbone.
- Fix các bug liên quan đến luồng xử lý và giao diện hiển thị, tập trung vào tính nhất quán giữa dữ liệu nghiệp vụ và trạng thái hiển thị trên màn hình.
- Sửa lỗi lẫn lộn `Stage`, đảm bảo ứng viên được chuyển đúng trạng thái theo từng bước của quy trình tuyển dụng.

**Tình trạng:** Hoàn thành

**Kế hoạch cho ngày mai:**
- Tiếp tục kiểm tra end-to-end flow tuyển dụng sau khi đã đồng bộ backbone `0200` với quy trình `0205`.
- Rà soát lại toàn bộ logic chuyển `Stage` và các điều kiện kích hoạt `activity` để tránh phát sinh trạng thái sai.
- Theo dõi thêm các lỗi giao diện hoặc sai lệch dữ liệu khi HR và Manager thao tác trên quy trình phỏng vấn.