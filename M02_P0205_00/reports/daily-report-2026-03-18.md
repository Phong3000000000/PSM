# Daily Report

**Ngày:** 18/03/2026

**Dự án:** Odoo HR Recruitment / Interview Evaluation / Mail Activity / Calendar

**Chi tiết kỹ thuật:**
- Bổ sung field ghi nhận kết quả đánh giá phỏng vấn trong quy trình tuyển dụng, đồng thời tự động lấy giá trị người phỏng vấn theo `current user` để giảm thao tác nhập tay và đảm bảo đúng người thực hiện đánh giá.
- Tùy chỉnh form đánh giá theo từng vai trò HR và Manager, giúp phân tách nội dung nhận xét và tiêu chí đánh giá phù hợp với từng nhóm người dùng.
- Tạo `activity` gửi đến CEO khi ứng viên hoàn thành vòng 1 và đạt điều kiện pass, phục vụ bước xét duyệt và sắp xếp phỏng vấn vòng 2.
- Bổ sung logic chuyển ứng viên về trạng thái `Refuse` khi kết quả phỏng vấn là fail, đảm bảo stage phản ánh đúng trạng thái nghiệp vụ.
- Ghi nhận lịch phỏng vấn vòng 2 khi CEO tạo lịch, giúp lưu vết đầy đủ dữ liệu lịch hẹn cho các vòng phỏng vấn tiếp theo.
- Thống nhất tạm thời cách xác định đậu/rớt phỏng vấn dựa trên phiếu đánh giá ứng viên, làm cơ sở cho việc chuẩn hóa rule xử lý trạng thái trong các bước tiếp theo.

**Tình trạng:** Hoàn thành

**Kế hoạch cho ngày mai:**
- Rà soát lại logic đánh giá phỏng vấn giữa HR, Manager và CEO để đảm bảo thống nhất dữ liệu và điều kiện chuyển stage.
- Kiểm tra luồng tạo activity và lưu lịch phỏng vấn vòng 2 sau khi CEO thao tác trên hệ thống.
- Tiếp tục hoàn thiện rule xác định pass/fail từ phiếu đánh giá để áp dụng ổn định trong toàn bộ quy trình tuyển dụng.