# Danh sách activity đang được tạo trong module `M02_P0205_00`

## Mục tiêu

Tài liệu này tổng hợp tất cả các activity đang được tạo trong code của module `0205`, để dễ nắm:

- activity nào đang tồn tại
- activity được tạo ở đâu
- activity được tạo khi nào
- activity đang phân cho ai

Lưu ý:

- Tài liệu này chỉ liệt kê các chỗ **thực sự tạo activity** trong code.
- File `models/mail_activity.py` chỉ xử lý khi activity hoàn thành, **không tạo activity mới**.

## 1. Activity trên `hr.applicant`

### 1.1. Activity cho recruiter khi có ứng viên mới từ portal / website

- File: `addons/M02_P0205_00/models/hr_applicant.py`
- Hàm: `_schedule_portal_activity()`
- Thời điểm tạo:
  - khi tạo applicant bởi user public
  - hoặc khi context có `from_website = True`
- Summary:
  - `ứng viên mới: <tên ứng viên>`
- Note:
  - thông báo ứng viên vừa nộp đơn và yêu cầu xem xét hồ sơ
- Phân cho ai:
  - `applicant.user_id`
  - nếu không có thì fallback `applicant.job_id.user_id`
- Ý nghĩa:
  - giao cho người phụ trách tuyển dụng/recruiter vào xem hồ sơ ứng viên mới

### 1.2. Activity mời xử lý phỏng vấn vòng 1 sau khi ứng viên chọn lịch

- File: `addons/M02_P0205_00/models/hr_applicant.py`
- Hàm: `write()`
- Điều kiện tạo:
  - khi field `interview_date_1` được ghi và có giá trị
- Summary:
  - `Can moi PV L1`
- Note:
  - `Ung vien da chon lich phong van Vong 1. Vui long nhan nut Moi PV L1.`
- Phân cho ai:
  - `rec.user_id`
  - nếu không có thì fallback `rec.job_id.user_id`
- Ý nghĩa:
  - nhắc người phụ trách vào bấm nút mời phỏng vấn vòng 1
- Ghi chú:
  - có check duplicate theo `applicant + user + summary`

### 1.3. Activity tham gia phỏng vấn lần 1

- File: `addons/M02_P0205_00/models/hr_applicant.py`
- Đoạn tạo activity nằm trong flow gửi email chọn lịch phỏng vấn
- Thời điểm tạo:
  - sau khi hệ thống gửi email cho ứng viên chọn slot phỏng vấn vòng 1
- Summary:
  - `Tham gia phong van lan 1`
- Note:
  - `Vui long tham gia phong van lan 1 cua <ten ung vien>.`
- Phân cho ai:
  - `self.user_id`
  - `manager_user = self._find_applicant_manager_user()`
- Ý nghĩa:
  - mời HR/recruiter và trưởng phòng cùng tham gia phỏng vấn vòng 1
- Ghi chú:
  - hiện tại đoạn này **không thấy check duplicate**

### 1.4. Activity cho trưởng phòng review CV sau khi ứng viên pass khảo sát

- File: `addons/M02_P0205_00/models/survey_ext.py`
- Thời điểm tạo:
  - khi kết quả survey là `PASS`
  - và applicant được chuyển sang stage `Screening`
- Summary:
  - `Kiểm tra CV ứng viên sau khi PASS khảo sát`
- Note:
  - yêu cầu review CV và đánh dấu đã kiểm tra
- Phân cho ai:
  - `manager_user = _find_applicant_manager_user(applicant)`
- Ý nghĩa:
  - giao cho trưởng phòng xác nhận phần CV sau khi ứng viên qua khảo sát đầu vào
- Ghi chú:
  - hiện tại **không thấy check duplicate**

### 1.5. Activity cho CEO mở vòng 2

- File: `addons/M02_P0205_00/models/hr_applicant.py`
- Hàm: `_notify_ceo_round2()`
- Thời điểm tạo:
  - khi người phỏng vấn chính kết luận `pass` ở vòng 1
- Summary:
  - `Lên lịch PV vòng 2`
- Note:
  - yêu cầu thiết lập lịch phỏng vấn vòng 2 cho ứng viên đã đạt vòng 1
- Phân cho ai:
  - `self.company_id.ceo_id.user_id`
- Ý nghĩa:
  - giao CEO vào sắp lịch/vận hành vòng 2
- Ghi chú:
  - dùng helper `_schedule_round_activity_for_users()`
  - có check duplicate theo `applicant + user + summary`

### 1.6. Activity cho group BOD mở vòng 3

- File: `addons/M02_P0205_00/models/hr_applicant.py`
- Hàm: `_notify_bod_round3()`
- Thời điểm tạo:
  - khi người phỏng vấn chính kết luận `pass` ở vòng 2
- Summary:
  - `Lên lịch PV vòng 3`
- Note:
  - yêu cầu tạo lịch và gửi lịch phỏng vấn vòng 3
- Phân cho ai:
  - toàn bộ user trong group `M02_P0205_00.group_bod_recruitment`
- Ý nghĩa:
  - thông báo toàn bộ BOD liên quan để xử lý vòng 3
- Ghi chú:
  - dùng helper `_schedule_round_activity_for_group()`
  - mỗi user trong group nhận một activity riêng
  - có check duplicate theo `applicant + user + summary`

### 1.7. Activity cho group ABU mở vòng 4

- File: `addons/M02_P0205_00/models/hr_applicant.py`
- Hàm: `_notify_abu_round4()`
- Thời điểm tạo:
  - khi người phỏng vấn chính kết luận `pass` ở vòng 3
- Summary:
  - `Lên lịch PV vòng 4`
- Note:
  - yêu cầu tạo lịch và gửi lịch phỏng vấn vòng 4
- Phân cho ai:
  - toàn bộ user trong group `M02_P0205_00.group_abu_recruitment`
- Ý nghĩa:
  - thông báo toàn bộ ABU liên quan để xử lý vòng 4
- Ghi chú:
  - dùng helper `_schedule_round_activity_for_group()`
  - mỗi user trong group nhận một activity riêng
  - có check duplicate theo `applicant + user + summary`

## 2. Activity trên `recruitment.request`

### 2.1. Activity cho HR khi request được submit

- File: `addons/M02_P0205_00/models/recruitment_request.py`
- Hàm: `action_submit()` -> `_send_activity_to_hr()`
- Thời điểm tạo:
  - khi user submit yêu cầu tuyển dụng
- Summary:
  - `Kiểm tra Yêu cầu tuyển dụng: <mã request>`
- Note:
  - yêu cầu HR kiểm tra request vừa tạo
- Phân cho ai:
  - group `M02_P0205_00.group_hr_validator`
  - nếu không có thì fallback `hr.group_hr_manager`
- Ghi chú rất quan trọng:
  - helper `_schedule_activity_for_group()` hiện chỉ lấy `users[0]`
  - nghĩa là **chỉ user đầu tiên của group nhận activity**, không phải toàn bộ group

### 2.2. Activity cho CEO group khi HR validate request

- File: `addons/M02_P0205_00/models/recruitment_request.py`
- Hàm: `action_hr_validate()` -> `_send_activity_to_ceo()`
- Thời điểm tạo:
  - khi HR validate xong request
- Summary:
  - `Phê duyệt yêu cầu tuyển dụng: <mã request>`
- Note:
  - yêu cầu CEO duyệt request đã được HR xác nhận
- Phân cho ai:
  - group `M02_P0205_00.group_ceo_recruitment`
- Ghi chú rất quan trọng:
  - do helper `_schedule_activity_for_group()` chỉ dùng `users[0]`
  - thực tế **chỉ user đầu tiên trong group CEO Recruitment nhận activity**

## 3. Activity trên `recruitment.plan`

### 3.1. Activity duyệt kế hoạch tuyển dụng cho managers và TP

- File: `addons/M02_P0205_00/models/recruitment_plan.py`
- Thời điểm tạo:
  - khi plan được gửi đi cho các bên cần duyệt
- Summary:
  - `Duyệt kế hoạch tuyển dụng`
- Note:
  - `Vui lòng xem xét và duyệt kế hoạch tuyển dụng <tên plan>.`
- Phân cho ai:
  - tập `all_users = managers | tp_users`
  - tức là các manager và các TP được gom từ logic của plan
- Ý nghĩa:
  - giao từng user liên quan vào duyệt plan
- Ghi chú:
  - mỗi user nhận một activity riêng
  - có check duplicate theo `plan + user + summary`

### 3.2. Activity cho toàn bộ HR validate kế hoạch tuyển dụng

- File: `addons/M02_P0205_00/models/recruitment_plan.py`
- Hàm: `_send_activity_to_hr_for_validation()`
- Thời điểm tạo:
  - khi tất cả sub-plan đã được manager duyệt
  - hoặc parent plan không có sub-plan và manager đã duyệt xong
- Summary:
  - `HR Validate KHTN: <tên plan>`
- Note:
  - yêu cầu HR kiểm tra và validate kế hoạch tuyển dụng
- Phân cho ai:
  - toàn bộ user nội bộ đang active thuộc:
    - `hr.group_hr_manager`
    - hoặc `hr.group_hr_user`
- Ý nghĩa:
  - giao cho toàn bộ HR liên quan vào validate kế hoạch
- Ghi chú:
  - mỗi user nhận một activity riêng
  - có check duplicate theo `plan + user + summary like 'HR Validate KHTN'`

### 3.3. Activity cho CEO duyệt kế hoạch tuyển dụng

- File: `addons/M02_P0205_00/models/recruitment_plan.py`
- Hàm: `_send_activity_to_ceo_for_approval()`
- Thời điểm tạo:
  - khi HR validate xong kế hoạch tuyển dụng
- Summary:
  - `CEO duyệt KHTN: <tên plan>`
- Note:
  - yêu cầu CEO xem xét và phê duyệt kế hoạch đã được HR validate
- Phân cho ai:
  - `self.company_id.ceo_id.user_id`
- Ý nghĩa:
  - giao CEO thực hiện bước duyệt cuối cho recruitment plan
- Ghi chú:
  - có check duplicate theo `plan + ceo_user + summary like 'CEO duyệt KHTN'`

## 4. File không tạo activity mới nhưng có liên quan

### 4.1. Hook hoàn thành activity để auto tick CV checked

- File: `addons/M02_P0205_00/models/mail_activity.py`
- Chức năng:
  - khi activity thuộc `hr.applicant` được mark done
  - nếu `summary` chứa cả `CV` và `PASS`
  - thì applicant sẽ được set `cv_checked = True`
- Kết luận:
  - file này **không tạo activity mới**
  - chỉ phản ứng sau khi người dùng hoàn tất activity

## 5. Tổng hợp nhanh theo người nhận

### HR / Recruiter

- Nhận activity `ứng viên mới: <tên ứng viên>`
- Nhận activity `Can moi PV L1`
- Có thể nhận activity `Tham gia phong van lan 1` nếu là `applicant.user_id`
- Nhận activity `Kiểm tra Yêu cầu tuyển dụng: <mã request>` nếu là user đầu tiên của group HR validator / fallback HR manager
- Nhận activity `HR Validate KHTN: <tên plan>` nếu thuộc HR group

### Trưởng phòng / Manager

- Nhận activity `Tham gia phong van lan 1`
- Nhận activity `Kiểm tra CV ứng viên sau khi PASS khảo sát`
- Có thể nhận activity `Duyệt kế hoạch tuyển dụng`

### CEO

- Nhận activity `Lên lịch PV vòng 2`
- Có thể nhận activity `Phê duyệt yêu cầu tuyển dụng: <mã request>` nếu là user đầu tiên trong group CEO Recruitment
- Nhận activity `CEO duyệt KHTN: <tên plan>`

### BOD

- Nhận activity `Lên lịch PV vòng 3`

### ABU

- Nhận activity `Lên lịch PV vòng 4`

## 6. Điểm cần lưu ý khi đọc flow activity

- `hr.applicant` đang có cả activity tạo bằng `self.env['mail.activity'].create()` và bằng `activity_schedule()`
- Một số flow có chống duplicate, nhưng một số flow chưa có
- `recruitment.request` hiện có tên helper là gửi cho group, nhưng thực tế chỉ giao cho `users[0]`
- `recruitment.plan` là phần có phân activity rõ nhất theo từng user
