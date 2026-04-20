# Plan triển khai cập nhật activity trong module `M02_P0205`

## Mục tiêu

Cập nhật lại logic activity của module `0205` để:

- phân activity đúng người nhận
- bổ sung activity ở các bước đang thiếu handoff
- tránh tạo task bị rơi hoặc khó theo dõi trong vận hành

## Phạm vi triển khai

Dựa trên kết quả rà soát tại:

- `addons/M02_P0205/notes/activity-review-findings.md`

Các nhóm việc cần làm gồm:

1. Sửa chỗ đang phân activity sai người
2. Bổ sung activity cho các bước còn thiếu
3. Rà lại duplicate rule và tính nhất quán
4. Kiểm tra end-to-end các flow chính

## Phase 1. Sửa lỗi phân activity sai người

### 1.1. Sửa `recruitment.request` đang chỉ giao cho `users[0]`

File:

- `addons/M02_P0205/models/recruitment_request.py`

Việc cần làm:

- refactor `_schedule_activity_for_group()`
- thay vì chỉ dùng `users[0]`, loop qua toàn bộ `group.user_ids`
- tạo activity riêng cho từng user
- bổ sung check duplicate theo:
  - `res_model`
  - `res_id`
  - `user_id`
  - `summary`

Kết quả mong muốn:

- HR activity được giao đúng cho toàn bộ user cần nhận
- CEO group activity cũng được giao đúng cho toàn bộ user cần nhận, nếu nghiệp vụ vẫn muốn dùng group

### 1.2. Chốt lại rule nghiệp vụ cho CEO request

Điểm cần xác nhận khi code:

- request approval của `recruitment.request` thực sự muốn giao cho:
  - toàn bộ user trong `group_ceo_recruitment`
  - hay chỉ 1 CEO cụ thể

Nếu muốn giao cho 1 người duy nhất:

- nên đổi từ group sang user cụ thể

Nếu muốn giao cho group:

- phải loop toàn bộ group users

## Phase 2. Bổ sung activity cho các bước đang thiếu

### 2.1. Bổ sung activity cho nhánh `CONSIDER` của survey

File:

- `addons/M02_P0205/models/survey_ext.py`

Việc cần làm:

- rà lại xem nhánh `CONSIDER` còn được giữ hay sẽ bỏ

Nếu vẫn giữ:

- khi applicant vào `Screening` theo nhánh `CONSIDER`, tạo activity follow-up
- người nhận đề xuất:
  - trưởng phòng
  - hoặc recruiter/HR owner

Nội dung activity đề xuất:

- review hồ sơ ứng viên thuộc nhánh cần xem xét
- quyết định bước tiếp theo cho applicant

### 2.2. Bổ sung activity sau khi pass vòng 4

File:

- `addons/M02_P0205/models/hr_applicant.py`

Việc cần làm:

- sau khi kết luận vòng 4 là `pass`, bổ sung activity handoff sang bước Offer
- activity này nên được tạo ở thời điểm đủ điều kiện sang Offer, không chờ người dùng tự nhớ thao tác

Người nhận đề xuất:

- `applicant.user_id`
- nếu không có thì fallback `job_id.user_id`

Nội dung activity đề xuất:

- chuẩn bị offer
- chuyển hồ sơ sang bước đề xuất chính thức

### 2.3. Bổ sung activity follow-up tại stage `Offer`

File:

- `addons/M02_P0205/models/hr_applicant.py`

Các điểm có thể bổ sung:

- sau `action_send_offer()`
  - tạo activity nhắc theo dõi phản hồi offer
- khi offer đã gửi nhưng chưa xác nhận ký
  - có thể cần activity nhắc HR follow-up

Người nhận đề xuất:

- recruiter/HR owner của applicant

Lưu ý:

- phần này nên làm tối giản trước, tránh sinh quá nhiều activity không cần thiết

## Phase 3. Chuẩn hóa duplicate rule

File chính:

- `addons/M02_P0205/models/hr_applicant.py`
- `addons/M02_P0205/models/survey_ext.py`
- `addons/M02_P0205/models/recruitment_request.py`

Việc cần làm:

- rà các flow đang tạo activity bằng `create()` trực tiếp
- bổ sung check duplicate ở các chỗ chưa có

Các chỗ cần ưu tiên:

- `Tham gia phong van lan 1`
- `Kiểm tra CV ứng viên sau khi PASS khảo sát`
- các activity mới sẽ thêm ở phase 2

Mục tiêu:

- tránh spam activity khi người dùng thao tác lặp
- giữ rule tạo activity nhất quán giữa các flow

## Phase 4. Kiểm thử nghiệp vụ

### 4.1. Flow `recruitment.request`

- submit request
- kiểm tra đúng user HR nhận activity
- HR validate request
- kiểm tra đúng user CEO nhận activity

### 4.2. Flow survey

- applicant `PASS`
- applicant `CONSIDER` nếu nhánh này còn giữ
- applicant `FAIL`
- kiểm tra activity có được tạo đúng người và đúng lúc

### 4.3. Flow interview office

- pass vòng 1 => CEO nhận activity vòng 2
- pass vòng 2 => BOD nhận activity vòng 3
- pass vòng 3 => ABU nhận activity vòng 4
- pass vòng 4 => HR/recruiter nhận activity chuẩn bị Offer

### 4.4. Flow offer

- gửi offer
- kiểm tra activity follow-up sau offer
- xác nhận đã ký
- kiểm tra không còn activity treo sai logic

## Thứ tự triển khai đề xuất

Để an toàn và dễ kiểm soát, nên làm theo 3 đợt:

1. Sửa lỗi `recruitment.request` phân sai người
2. Bổ sung activity còn thiếu trong `hr.applicant` và `survey_ext`
3. Chuẩn hóa duplicate check và test lại end-to-end

## Kết quả mong muốn sau cập nhật

- không còn chỗ gọi “gửi cho group” nhưng thực tế chỉ giao cho 1 người
- các bước chuyển trạng thái quan trọng đều có activity handoff
- flow tuyển dụng ít phụ thuộc vào người dùng nhớ thủ công
- activity trong module nhất quán hơn và ít bị duplicate hơn
