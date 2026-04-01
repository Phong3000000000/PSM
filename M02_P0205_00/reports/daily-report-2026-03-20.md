# Daily Report

**Ngày:** 20/03/2026

**Dự án:** Odoo HR Recruitment / Interview Flow / Mail Template / Calendar

**Chi tiết kỹ thuật:**
- Tùy chỉnh lại các `Stage` sau từng vòng phỏng vấn để trạng thái ứng viên phản ánh đúng tiến trình xử lý và hỗ trợ phân tách rõ giữa các mốc đánh giá.
- Fix lỗi liên quan đến email template, đảm bảo nội dung và dữ liệu truyền vào email hiển thị đúng trong các bước gửi thông báo phỏng vấn.
- Kiểm tra và rà soát lại điều kiện hiển thị/thực thi của các button trong quá trình phỏng vấn, nhằm đảm bảo người dùng chỉ thao tác được đúng theo trạng thái nghiệp vụ hiện tại.
- Sửa lỗi truyền field giữa các vòng phỏng vấn, giúp dữ liệu ứng viên và thông tin xử lý được đồng bộ chính xác xuyên suốt các bước.
- Fix bug button gửi lịch theo trạng thái vòng phỏng vấn, đảm bảo thao tác gửi lịch chỉ được kích hoạt đúng tại thời điểm và đúng vòng tương ứng.
- Thiết lập lịch phỏng vấn tách biệt giữa các vòng, tránh chồng chéo dữ liệu lịch hẹn và hỗ trợ quản lý độc lập cho từng vòng phỏng vấn.

**Tình trạng:** Hoàn thành

**Kế hoạch cho ngày mai:**
- Kiểm tra lại toàn bộ flow phỏng vấn nhiều vòng, đặc biệt là mối liên kết giữa `Stage`, button action và lịch hẹn.
- Rà soát thêm email template và dữ liệu truyền field ở từng bước để tránh phát sinh lỗi hiển thị hoặc sai thông tin.
- Theo dõi tính ổn định của cơ chế tách lịch phỏng vấn giữa các vòng khi vận hành thực tế.