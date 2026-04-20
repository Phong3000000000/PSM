# Rà soát activity trong module `M02_P0205`

## Mục tiêu

Tài liệu này ghi lại kết quả rà soát activity trong module `0205` theo 2 hướng:

- activity nào đang có dấu hiệu phân bổ sai người
- activity nào đáng ra nên có nhưng hiện tại còn thiếu

Phạm vi rà:

- `models/hr_applicant.py`
- `models/survey_ext.py`
- `models/recruitment_request.py`
- `models/recruitment_plan.py`

## Kết luận ngắn

Hiện tại có 1 vấn đề rõ ràng về phân activity sai người và một số chỗ luồng nghiệp vụ có khả năng bị thiếu activity handoff.

Mức độ ưu tiên:

- Cao:
  - `recruitment.request` đang gửi activity cho group nhưng thực tế chỉ giao cho `user` đầu tiên của group
- Trung bình:
  - nhánh `CONSIDER` của survey đưa hồ sơ vào `Screening` nhưng không tạo activity follow-up
  - sau khi pass vòng 4 chưa có activity bàn giao sang bước Offer
- Thấp:
  - tại stage `Offer` chưa có activity follow-up nội bộ cho bước gửi offer / xác nhận ký

## 1. Activity đang phân sai người

### 1.1. `recruitment.request` chỉ giao cho user đầu tiên của group

File:

- `addons/M02_P0205/models/recruitment_request.py`

Các hàm liên quan:

- `_send_activity_to_hr()`
- `_send_activity_to_ceo()`
- `_schedule_activity_for_group()`

Chi tiết:

- `_send_activity_to_hr()` gọi helper `_schedule_activity_for_group()` để gửi activity cho HR
- `_send_activity_to_ceo()` cũng dùng chính helper này để gửi activity cho CEO group
- Nhưng trong `_schedule_activity_for_group()`, code hiện tại lấy:
  - `users = group.user_ids`
  - sau đó gọi `activity_schedule(... user_id=users[0].id, ...)`

Điều này có nghĩa:

- activity không được phân cho toàn bộ user trong group
- chỉ `user` đầu tiên trong danh sách group nhận activity

Rủi ro:

- các HR khác trong group không thấy task
- các CEO/user khác trong group CEO Recruitment cũng không thấy task
- tên hàm và ý nghĩa nghiệp vụ đang gây hiểu nhầm là “gửi cho group”, nhưng hành vi thực tế là “gửi cho 1 người đại diện đầu tiên”

Đánh giá:

- Đây là lỗi phân bổ activity sai người rõ ràng nhất trong module hiện tại

## 2. Các chỗ có khả năng thiếu activity

### 2.1. Nhánh `CONSIDER` của survey chưa có activity follow-up

File:

- `addons/M02_P0205/models/survey_ext.py`

Hiện trạng:

- Nếu applicant không fail phần must-have nhưng không đạt nice-to-have, code gán:
  - `status_label = "CONSIDER (Xem xét)"`
  - `target_stage = stage_screening`
- Applicant vẫn được đưa vào `Screening`

Nhưng phần tạo activity phía dưới chỉ chạy khi:

- `status_label == "PASS (Đạt)"`

Nên kết quả là:

- applicant nhánh `PASS` vào `Screening` có activity cho trưởng phòng review CV
- applicant nhánh `CONSIDER` cũng vào `Screening` nhưng không có activity nào follow tiếp

Rủi ro:

- hồ sơ có thể nằm ở `Screening` mà không có ai được giao xử lý
- về mặt vận hành dễ bị quên hoặc phải theo dõi bằng tay

Ghi chú:

- Điểm này chỉ còn đúng nếu nghiệp vụ survey vẫn còn dùng nhánh `CONSIDER`
- Hiện tại trong code `survey_ext.py`, nhánh này vẫn đang tồn tại

### 2.2. Sau khi pass vòng 4 chưa có activity bàn giao sang bước Offer

File:

- `addons/M02_P0205/models/hr_applicant.py`

Hiện trạng:

- Khi pass vòng 1:
  - tạo activity cho CEO mở vòng 2
- Khi pass vòng 2:
  - tạo activity cho group BOD mở vòng 3
- Khi pass vòng 3:
  - tạo activity cho group ABU mở vòng 4

Nhưng sau khi pass vòng 4:

- không có activity tương ứng để bàn giao bước tiếp theo cho HR/recruiter
- bước `action_ready_for_offer()` chỉ kiểm tra điều kiện và chuyển stage sang `Offer`

Rủi ro:

- nếu người chấm vòng 4 không phải người trực tiếp làm Offer, hồ sơ thiếu handoff rõ ràng
- phải phụ thuộc vào người dùng tự nhớ bấm nút hoặc tự theo dõi stage

Đề xuất nghiệp vụ nên cân nhắc:

- tạo activity cho `applicant.user_id`
- hoặc cho HR/recruiter phụ trách hồ sơ
- với nội dung kiểu:
  - chuẩn bị offer
  - chuyển hồ sơ sang bước đề xuất chính thức

### 2.3. Tại stage `Offer` chưa có activity follow-up nội bộ

File:

- `addons/M02_P0205/models/hr_applicant.py`

Các hàm liên quan:

- `action_send_offer()`
- `action_confirm_signed()`

Hiện trạng:

- `action_send_offer()` gửi email offer cho ứng viên và set `offer_status = 'proposed'`
- `action_confirm_signed()` chuyển applicant sang `Hired` và set `offer_status = 'accepted'`

Nhưng chưa có activity nội bộ cho các việc như:

- theo dõi ứng viên đã phản hồi offer chưa
- nhắc HR xác nhận đã ký
- nhắc xử lý nếu offer bị treo lâu

Rủi ro:

- bước offer phụ thuộc nhiều vào người dùng nhớ thao tác thủ công
- thiếu dấu vết task rõ ràng trong hệ thống

Mức độ:

- thấp hơn hai điểm trên vì luồng vẫn chạy được
- nhưng sẽ dễ phát sinh thiếu follow-up trong thực tế vận hành

## 3. Điểm chưa kết luận là lỗi

### 3.1. Activity `Tham gia phong van lan 1` đang giao cho `self.user_id` và manager

File:

- `addons/M02_P0205/models/hr_applicant.py`

Hiện trạng:

- sau khi gửi email chọn lịch phỏng vấn vòng 1, hệ thống tạo activity:
  - cho `self.user_id`
  - cho manager tìm được từ `_find_applicant_manager_user()`

Nhận xét:

- nếu `self.user_id` đúng là recruiter/HR owner thì cách phân này hợp lý
- tuy nhiên code comment ghi là tạo cho “HR và Manager”, còn thực tế dùng `self.user_id`
- nếu `self.user_id` không phải HR mà là một owner khác thì activity có thể lệch vai trò mong muốn

Kết luận:

- chưa đủ dữ kiện để chốt là bug
- nhưng đây là điểm nên xác nhận lại với nghiệp vụ

## 4. Tóm tắt khuyến nghị

### Ưu tiên 1

- sửa `recruitment_request._schedule_activity_for_group()` để gửi cho đúng người nhận mong muốn
- nếu nghiệp vụ là gửi cho cả group, cần loop qua toàn bộ users thay vì lấy `users[0]`

### Ưu tiên 2

- quyết định rõ nhánh `CONSIDER` của survey còn dùng hay bỏ
- nếu còn dùng, cần có activity follow-up tương ứng khi applicant vào `Screening`

### Ưu tiên 3

- bổ sung activity handoff sau khi pass vòng 4 để chuyển sang bước Offer

### Ưu tiên 4

- cân nhắc thêm activity follow-up tại stage `Offer`
- ví dụ:
  - đã gửi offer, chờ phản hồi
  - cần xác nhận đã ký

## 5. Kết luận

Hiện tại lỗi rõ nhất là:

- `recruitment.request` đang phân activity sai người do chỉ giao cho `user` đầu tiên của group

Các điểm còn lại chủ yếu là thiếu activity để đảm bảo handoff trọn vẹn giữa các bước, đặc biệt ở:

- nhánh `CONSIDER` của survey
- bước chuyển từ vòng 4 sang Offer
- bước follow-up trong stage Offer
