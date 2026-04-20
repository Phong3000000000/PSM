# Daily Report

**Ngày:** 19/03/2026

**Dự án:** Odoo Recruitment Plan / Backbone Department Structure / Module 0204 / Module 0205 / Mail Activity

**Chi tiết kỹ thuật:**
- Điều chỉnh logic lọc phòng ban dựa trên thông tin `Khối` được chứa trong cấu trúc `Department` của backbone, giúp đồng bộ dữ liệu tổ chức với luồng tuyển dụng.
- Bổ sung filter vị trí công việc theo phòng ban, đảm bảo danh sách vị trí hiển thị đúng theo phạm vi đơn vị đang thao tác.
- Thực hiện phần `Yêu cầu tuyển dụng được giao làm` để dùng chung cho cả hai module `0204` và `0205`, hướng đến tái sử dụng logic nghiệp vụ và giảm trùng lặp dữ liệu.
- Tách biệt phạm vi xử lý giữa module `0205` và `0204`, giúp hạn chế phụ thuộc chéo và dễ kiểm soát từng flow riêng biệt.
- Thiết lập mặc định phòng ban theo người quản lý hiện tại khi thao tác trên kế hoạch/yêu cầu tuyển dụng, giảm thao tác chọn thủ công và tăng tính chính xác dữ liệu đầu vào.
- Bổ sung filter vị trí công việc theo phòng ban của người quản lý hiện tại để đảm bảo người dùng chỉ thao tác trên dữ liệu đúng quyền và đúng ngữ cảnh.
- Loại bỏ các `Stage` dư thừa trong Kế hoạch tuyển dụng nhằm đơn giản hóa quy trình và tránh phát sinh trạng thái không cần thiết.
- Sau khi HR validate hoàn tất, hệ thống tạo `activity` cho CEO thực hiện bước phê duyệt Kế hoạch tuyển dụng, hoàn thiện luồng phê duyệt nhiều cấp.

**Tình trạng:** Hoàn thành

**Kế hoạch cho ngày mai:**
- Kiểm tra lại tính đúng đắn của logic lọc phòng ban và vị trí công việc theo dữ liệu backbone và người quản lý hiện tại.
- Tiếp tục rà soát sự tách biệt nghiệp vụ giữa `0204` và `0205` để tránh ảnh hưởng chéo khi mở rộng tính năng.
- Theo dõi luồng validate và phê duyệt Kế hoạch tuyển dụng, đặc biệt là activity chuyển tiếp từ HR sang CEO.