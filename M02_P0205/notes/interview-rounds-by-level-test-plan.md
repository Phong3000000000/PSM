# Test Plan: Interview Rounds by Level

## Mục tiêu

Kiểm thử lại toàn bộ thay đổi đã triển khai qua 5 phase của tính năng:

- xác định số vòng phỏng vấn theo `job.level_id.code`
- chặn backend với các vòng vượt quá mức cho phép
- ẩn/hiện UI đúng theo số vòng hiệu lực
- activity bám đúng vòng cuối theo level
- mail notification chỉ gửi cho các vòng còn hiệu lực

## Phạm vi kiểm thử

- Module: `M02_P0205`
- Dependency liên quan: `M02_P0200`
- Flow áp dụng: tuyển dụng khối văn phòng

## Mapping business cần kiểm

- `employee` -> `2` vòng
- `assistant` -> `2` vòng
- `coordinator` -> `2` vòng
- `specialist` -> `3` vòng
- `consultant` -> `3` vòng
- `manager` -> `4` vòng
- `head_of_department` -> `4` vòng

## Chuẩn bị dữ liệu test

### 1. Job position

Chuẩn bị ít nhất 3 job office:

- Job A: `level_id.code = employee`
- Job B: `level_id.code = specialist`
- Job C: `level_id.code = manager`

### 2. Applicant

Tạo ít nhất 1 applicant cho mỗi job:

- Applicant A cho job `employee`
- Applicant B cho job `specialist`
- Applicant C cho job `manager`

### 3. User/Group

Đảm bảo có đủ user nội bộ trong các nhóm:

- HR Recruitment
- BOD Recruitment
- ABU Recruitment
- CEO trên company của applicant

### 4. Dữ liệu bổ trợ

Đảm bảo các applicant có:

- `user_id` hoặc `job_id.user_id` để nhận activity offer
- email hợp lệ để test gửi mail
- có thể tạo meeting cho từng vòng

## Test theo phase

## Phase 1. Kiểm thử mapping level -> max interview round

### Mục tiêu

Xác nhận applicant đọc đúng `job.level_id.code` và map đúng `max_interview_round`.

### Bước test

1. Mở Applicant A, B, C.
2. Kiểm tra job của từng applicant đã gán đúng level.
3. Kiểm tra behavior thực tế của flow:
- Applicant A chỉ cho phép đi tối đa vòng 2
- Applicant B chỉ cho phép đi tối đa vòng 3
- Applicant C cho phép đi đủ vòng 4

### Kỳ vọng

- `employee` dừng ở vòng 2
- `specialist` dừng ở vòng 3
- `manager` dừng ở vòng 4
- nếu job không có level hoặc level lạ, hệ thống fallback như thiết kế hiện tại

## Phase 2. Kiểm thử core flow theo số vòng hiệu lực

### Mục tiêu

Xác nhận backend chặn đúng các thao tác vượt quá số vòng.

### Case 2.1: Applicant level 2 vòng

1. Dùng Applicant A.
2. Hoàn thành vòng 1 và vòng 2 với kết quả `pass`.
3. Thử mở hoặc gọi các action liên quan đến vòng 3:
- mời PV L3
- thêm đánh giá vòng 3
- gửi notification vòng 3
4. Bấm `Sẵn sàng Offer`.

### Kỳ vọng

- applicant không đi tiếp sang vòng 3
- các action vòng 3 bị chặn ở backend
- `Sẵn sàng Offer` dùng được ngay sau khi pass vòng 2

### Case 2.2: Applicant level 3 vòng

1. Dùng Applicant B.
2. Hoàn thành vòng 1, 2, 3 với kết quả `pass`.
3. Thử gọi action vòng 4.
4. Bấm `Sẵn sàng Offer`.

### Kỳ vọng

- applicant không đi tiếp sang vòng 4
- action vòng 4 bị chặn ở backend
- applicant được vào Offer ngay sau vòng 3

### Case 2.3: Applicant level 4 vòng

1. Dùng Applicant C.
2. Hoàn thành vòng 1, 2, 3, 4 với kết quả `pass`.
3. Bấm `Sẵn sàng Offer`.

### Kỳ vọng

- flow 4 vòng vẫn chạy như cũ
- chỉ vào Offer sau khi pass vòng 4

## Phase 3. Kiểm thử UI

### Mục tiêu

Xác nhận giao diện chỉ hiển thị các vòng còn hiệu lực.

### Case 3.1: Applicant level 2 vòng

1. Mở form Applicant A.
2. Kiểm tra header buttons.
3. Kiểm tra tab evaluation.
4. Kiểm tra group tổng hợp evaluation.
5. Kiểm tra phần lịch phỏng vấn tiếp theo.
6. Kiểm tra field người phỏng vấn chính.

### Kỳ vọng

- không thấy `Mời PV L3`
- không thấy `Mời PV L4`
- không thấy tab `PV Vòng 3`
- không thấy tab `PV Vòng 4`
- không thấy group tổng hợp vòng 3, 4
- không thấy `interview_date_3`, `interview_date_4`
- không thấy `primary_interviewer_l3_user_id`, `primary_interviewer_l4_user_id`
- thấy nút `Sẵn sàng Offer` ở đúng thời điểm sau vòng 2

### Case 3.2: Applicant level 3 vòng

1. Mở form Applicant B.
2. Kiểm tra các thành phần UI liên quan vòng 4.

### Kỳ vọng

- vẫn thấy UI của vòng 3
- không thấy các thành phần của vòng 4
- `Sẵn sàng Offer` xuất hiện sau vòng 3

### Case 3.3: Applicant level 4 vòng

1. Mở form Applicant C.

### Kỳ vọng

- toàn bộ UI 4 vòng vẫn hiển thị đầy đủ

## Phase 4. Kiểm thử activity

### Mục tiêu

Xác nhận activity bám đúng vòng cuối theo level, không tạo activity cho vòng thừa.

### Case 4.1: Applicant level 2 vòng

1. Dùng Applicant A.
2. Pass vòng 1.
3. Kiểm tra activity `Lên lịch PV vòng 2`.
4. Pass vòng 2.
5. Kiểm tra activity sau vòng cuối.

### Kỳ vọng

- có activity mở vòng 2
- không có activity `Lên lịch PV vòng 3`
- có activity `Chuẩn bị Offer`

### Case 4.2: Applicant level 3 vòng

1. Dùng Applicant B.
2. Pass vòng 1.
3. Pass vòng 2.
4. Pass vòng 3.

### Kỳ vọng

- có activity mở vòng 2
- có activity mở vòng 3
- không có activity `Lên lịch PV vòng 4`
- có activity `Chuẩn bị Offer` sau vòng 3

### Case 4.3: Applicant level 4 vòng

1. Dùng Applicant C.
2. Pass lần lượt 4 vòng.

### Kỳ vọng

- có activity mở đúng từng vòng 2, 3, 4
- chỉ tạo `Chuẩn bị Offer` sau vòng 4

### Case 4.4: Duplicate check

1. Lưu lại evaluation `pass` nhiều lần hoặc cập nhật record cùng kết luận.
2. Kiểm tra chatter/activity.

### Kỳ vọng

- không phát sinh duplicate activity cùng `applicant + user + summary`

## Phase 5. Kiểm thử mail notification

### Mục tiêu

Xác nhận không thể gửi mail cho vòng vượt quá `max_interview_round`.

### Case 5.1: Applicant level 2 vòng

1. Dùng Applicant A.
2. Hoàn thành vòng 1.
3. Tạo meeting vòng 2 và gửi mail vòng 2.
4. Thử tạo hoặc gọi action gửi mail vòng 3.

### Kỳ vọng

- gửi mail vòng 2 thành công
- không thể gửi mail vòng 3
- hệ thống báo rõ job này chỉ áp dụng tối đa 2 vòng

### Case 5.2: Applicant level 3 vòng

1. Dùng Applicant B.
2. Hoàn thành vòng 1 và 2.
3. Gửi mail vòng 2, vòng 3.
4. Thử gửi mail vòng 4.

### Kỳ vọng

- gửi được mail vòng 2 và 3
- không thể gửi mail vòng 4

### Case 5.3: Applicant level 4 vòng

1. Dùng Applicant C.
2. Tạo đủ meeting cho các vòng.
3. Gửi mail vòng 2, 3, 4.

### Kỳ vọng

- toàn bộ mail vòng 2, 3, 4 gửi bình thường

## Test hồi quy cần chạy thêm

### 1. Flow fail

1. Ở mỗi level, cho applicant fail ở một vòng đang hiệu lực.

### Kỳ vọng

- applicant chuyển reject đúng như cũ
- không có activity mở vòng sau
- không có handoff Offer

### 2. Flow offer

1. Sau khi applicant vào Offer, bấm `Gửi Offer`.
2. Kiểm tra activity follow-up.

### Kỳ vọng

- luôn có activity `Theo dõi phản hồi Offer`
- người nhận là recruiter/owner phụ trách

### 3. Flow level thay đổi giữa chừng

1. Tạo applicant với job level 4 vòng.
2. Đi đến giữa flow.
3. Đổi job sang level 2 hoặc 3 vòng.
4. Mở lại form applicant.

### Kỳ vọng

- UI cập nhật theo level mới
- các action vòng vượt mức bị chặn
- không nên tiếp tục mở flow cho vòng không còn hiệu lực

## Thứ tự chạy test khuyến nghị

1. Upgrade module `M02_P0205`
2. Test smoke với Applicant A (`employee`)
3. Test smoke với Applicant B (`specialist`)
4. Test smoke với Applicant C (`manager`)
5. Test hồi quy flow fail
6. Test hồi quy offer
7. Test duplicate activity

## Tiêu chí pass

- mapping level -> số vòng đúng theo chốt business
- backend không cho thao tác vòng vượt mức
- UI không hiển thị vòng thừa
- activity mở vòng sau và handoff Offer đúng thời điểm
- mail notification chỉ gửi cho vòng còn hiệu lực
- flow 4 vòng cũ không bị vỡ

## Ghi chú

- nếu phát hiện lỗi, nên note theo mẫu:
  - applicant
  - job level
  - bước test
  - kết quả thực tế
  - kết quả mong đợi
  - screenshot hoặc log lỗi
