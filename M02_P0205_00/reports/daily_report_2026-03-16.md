# Daily Report

**Ngày:** 16/03/2026

**Dự án:** Odoo HR Recruitment / Calendar / Survey / Mail Activity

**Chi tiết kỹ thuật:**
- Xây dựng và hoàn thiện luồng xử lý ứng viên trong module tuyển dụng, bao gồm cập nhật `Stage` sang `Refuse`, gửi email kết quả kèm nội dung cảm ơn, và lưu trữ hồ sơ ứng viên phục vụ tra cứu về sau.
- Thiết kế cấu trúc survey sơ bộ ứng viên, chuẩn hóa danh sách câu hỏi và bổ sung trường email để phục vụ việc gửi khảo sát và định danh ứng viên.
- Tích hợp quy trình đặt lịch phỏng vấn qua `Calendar/Meeting`, bao gồm tạo sẵn 3 lịch hẹn, lưu dữ liệu lịch và gửi survey để ứng viên chủ động lựa chọn khung giờ phù hợp.
- Xử lý luồng nhận kết quả từ survey, lấy giá trị phản hồi của ứng viên và tạo `activity` thông báo đến `Line Manager` theo phòng ban của vị trí tuyển dụng tương ứng.
- Bổ sung logic tự động xử lý `Stage` khi ứng viên nộp đơn và hoàn thành khảo sát sơ bộ.
- Tạo `activity` thông báo cho HR và Manager kiểm tra hồ sơ ngay khi có ứng viên ứng tuyển, đảm bảo quy trình follow-up được kích hoạt kịp thời.

**Tình trạng:** Hoàn thành

**Kế hoạch cho ngày mai:**
- Rà soát lại toàn bộ flow tuyển dụng sau khi ứng viên apply, làm survey và chọn lịch phỏng vấn.
- Kiểm tra tính ổn định của các activity, email template và mapping Line Manager theo phòng ban.
- Tiếp tục tối ưu logic lịch hẹn phỏng vấn để hạn chế trùng lịch và cải thiện trải nghiệm chọn lịch của ứng viên.
