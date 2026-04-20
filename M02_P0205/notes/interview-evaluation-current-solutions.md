# Đối chiếu vướng mắc với code hiện tại trong module `M02_P0205`

## Mục đích

File này dùng để ghi lại những điểm trong `interview-evaluation-open-issues.md` mà module `0205` hiện đã có cách xử lý sẵn, cũng như những điểm vẫn chưa có lời giải trong code.

## 1. Những vướng mắc đã có pattern hoặc cách làm sẵn trong module

### 1.1. Xác định Trưởng phòng ban

Module hiện đã có pattern để tìm manager user của phòng ban:

- Hàm `_find_applicant_manager_user()` trong `models/hr_applicant.py`
- Hàm `_find_applicant_manager_user()` trong `models/survey_ext.py`

Cách làm hiện tại:

- ưu tiên lấy từ `job.department_id`
- fallback sang `department_id`
- fallback tiếp sang `recruitment.request.line.department_id`

Đây là pattern có thể tái dùng cho vòng 1 khi cần xác định Trưởng phòng ban là người phỏng vấn chính.

### 1.2. Xác định CEO

Module hiện đã có cách lấy CEO trong code:

- `company_id.ceo_id.user_id`

Đang được dùng trong:

- `_notify_ceo_round2()` tại `models/hr_applicant.py`
- một số logic tại `models/recruitment_plan.py`

Điều này cho thấy vòng 2 đã có sẵn hướng xác định người chịu trách nhiệm chính theo dữ liệu công ty.

### 1.3. Gửi activity cho một user cụ thể

Pattern này đã có trong module:

- dùng `activity_schedule()` khi đã biết `user_id`
- ví dụ đang dùng cho recruiter, manager và CEO

Các vị trí đang dùng:

- `models/hr_applicant.py`
- `models/recruitment_plan.py`

Đây là cách có thể tái sử dụng nếu sau này chốt BOD hoặc ABU theo user cụ thể thay vì theo group.

### 1.4. Gửi activity theo group

Module đã có một helper gửi activity theo group trong:

- `models/recruitment_request.py`

Hàm liên quan:

- `_schedule_activity_for_group()`

Hiện helper này:

- lấy `group.user_ids`
- sau đó tạo activity qua `activity_schedule()`

Tuy nhiên, cách hiện tại mới chỉ schedule cho `users[0]`, chưa gửi cho toàn bộ user trong group.

Nói cách khác:

- module đã có pattern xử lý theo group
- nhưng chưa đáp ứng đầy đủ yêu cầu gửi cho tất cả user trong group BOD/ABU

### 1.5. Group của BOD và ABU đã tồn tại

Module hiện đã có sẵn các group sau trong:

- `security/approval_groups.xml`

Cụ thể:

- `M02_P0205.group_bod_recruitment`
- `M02_P0205.group_abu_recruitment`

Đây là nền tảng sẵn có để triển khai activity cho BOD và ABU.

### 1.6. Field và logic đánh giá vòng phỏng vấn đã tồn tại

Module hiện đã có các field tổng hợp theo vòng:

- `eval_round_1_score` ... `eval_round_4_score`
- `eval_round_1_pass` ... `eval_round_4_pass`
- `eval_round_1_toggle` ... `eval_round_4_toggle`

Và các hàm liên quan:

- `_recommendation_score()`
- `_update_interview_round_outcome()`
- `_compute_eval_round_metrics()`

Điều này có nghĩa là:

- pipeline pass/fail theo vòng đã có sẵn cấu trúc
- chỉ cần đổi lại rule tính toán, không phải xây mới từ đầu

### 1.7. Field `recommendation` đã có sẵn 3 trạng thái

Trong model `hr.applicant.evaluation`, field `recommendation` hiện có:

- `pass`
- `fail`
- `consider`

Vì vậy:

- vấn đề không nằm ở thiếu field
- mà nằm ở cách diễn giải và dùng kết quả này trong nghiệp vụ

### 1.8. Field `interviewer_id` đã có sẵn

Trong model `hr.applicant.evaluation`, module đã có:

- `interviewer_id`

Và trên các view đánh giá cũng đã hiển thị field này.

Điều đó có nghĩa là:

- đã có nền tảng dữ liệu để biết ai là người đánh giá
- nhưng chưa có cơ chế xác định ai là “người phỏng vấn chính”

### 1.9. Điều kiện qua vòng trước rồi mới sang vòng sau đã có

Module hiện đã có logic kiểm tra vòng trước hoàn thành thông qua:

- `eval_round_X_toggle`
- `_ensure_previous_round_completed()`

Ngoài ra các button gửi lịch vòng tiếp theo trên form applicant cũng đang phụ thuộc vào:

- `eval_round_1_toggle`
- `eval_round_2_toggle`
- `eval_round_3_toggle`

Nghĩa là:

- flow điều hướng qua vòng đã có
- chỉ cần sửa tiêu chí để `toggle` phản ánh đúng kết luận của người phỏng vấn chính

## 2. Module hiện đang giải quyết các vướng mắc này như thế nào

### 2.1. Kết quả vòng đang được tính theo tổng hợp nhiều người

Hiện tại module không dùng người phỏng vấn chính.

Thay vào đó:

- lấy toàn bộ bản đánh giá trong cùng một vòng
- cộng/trừ điểm theo `recommendation`

Rule hiện tại:

- `pass` = `+1`
- `consider` = `0`
- `fail` = `-1`

Vòng được xem là đạt nếu tổng điểm `>= 0`.

Điều này đang được xử lý trong:

- `_update_interview_round_outcome()`
- `_compute_eval_round_metrics()`

### 2.2. `consider` hiện đang được coi là trung tính

Module hiện không có flow riêng cho `consider`.

Cách xử lý hiện tại:

- `consider` được map thành `0`
- tức là không kéo kết quả về `pass`, cũng không kéo về `fail`

Điều này có nghĩa:

- `consider` vẫn còn sống trong code
- nhưng chỉ đang đóng vai trò trung tính trong phép cộng điểm

### 2.3. Activity cho CEO đã có, nhưng BOD và ABU thì chưa

Hiện module đã có logic:

- khi ứng viên đạt vòng 1 thì tạo activity cho CEO để lên lịch vòng 2

Được xử lý trong:

- `_notify_ceo_round2()` tại `models/hr_applicant.py`

Nhưng hiện chưa có logic tương tự cho:

- BOD ở vòng 3
- ABU ở vòng 4

### 2.4. Nút gửi lịch vòng 3 và 4 đã có, nhưng vẫn theo flow hiện tại của HR

Module đã có:

- `action_send_interview_round3_notification()`
- `action_send_interview_round4_notification()`

Và trên form applicant cũng đã có button tương ứng.

Tuy nhiên:

- các button này hiện vẫn đang thuộc flow chung
- chưa gắn riêng với trách nhiệm thực thi của group BOD hoặc ABU
- trên view hiện vẫn chủ yếu dùng group `hr_recruitment.group_hr_recruitment_user`

## 3. Những vướng mắc hiện vẫn chưa có lời giải sẵn trong code

### 3.1. Chưa có `is_primary_interviewer`

Hiện module chưa có:

- field đánh dấu người phỏng vấn chính
- constraint đảm bảo mỗi vòng chỉ có một người chính

### 3.2. Chưa có cách xác định BOD/ABU nào là người chính nếu group có nhiều user

Module có group BOD và ABU, nhưng chưa có rule nào trả lời:

- nếu group có nhiều user thì ai là người phỏng vấn chính thực sự

### 3.3. Chưa có activity cho toàn bộ group BOD và ABU

Pattern gửi theo group đã có, nhưng:

- chưa gửi cho toàn bộ user trong group
- chưa có cơ chế chống duplicate theo `applicant + round + user`
- chưa có flow cụ thể cho vòng 3 và vòng 4

### 3.4. Chưa có cơ chế migrate dữ liệu cũ

Hiện module chưa có logic nào để:

- đánh dấu lại bản đánh giá cũ theo “người phỏng vấn chính”
- chuyển các applicant cũ sang logic mới

### 3.5. Chưa có cảnh báo UI cho trạng thái “chưa có kết luận từ người chính”

Hiện trên applicant:

- có các field tổng hợp vòng
- có button theo điều kiện toggle

Nhưng chưa có:

- cảnh báo rõ ràng rằng vòng hiện tại chưa có đánh giá từ người phỏng vấn chính

### 3.6. Chưa có quyền hiển thị hoặc quyền thao tác riêng cho BOD/ABU theo flow mới

Các group BOD và ABU đã tồn tại, nhưng:

- `ir.model.access.csv` hiện chưa có rule riêng theo 2 group này
- các button vòng 3/4 hiện chưa được chuyển sang cơ chế quyền riêng cho BOD/ABU

## 4. Kết luận

Module `0205` hiện đã có khá nhiều nền tảng sẵn để triển khai plan:

- có cách tìm Trưởng phòng ban
- có cách lấy CEO
- có pattern tạo activity
- có group BOD/ABU
- có sẵn các field và flow pass/fail theo vòng

Nhưng phần cốt lõi của yêu cầu mới vẫn chưa tồn tại trong code:

- chưa có người phỏng vấn chính
- chưa có rule pass/fail theo người chính
- chưa có activity đầy đủ cho BOD/ABU
- chưa có cơ chế xử lý rõ cho `consider`

Vì vậy, khi triển khai plan này, phần nên tái sử dụng là các helper hiện có, còn phần phải xây mới là rule nghiệp vụ quyết định kết quả vòng và cơ chế phân vai người phỏng vấn chính.
