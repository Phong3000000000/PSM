# Plan chỉnh sửa logic đánh giá phỏng vấn

## Mục tiêu

Điều chỉnh lại cách xác định kết quả từng vòng phỏng vấn trong module `M02_P0205` theo nguyên tắc:

- Nếu `Đánh giá / Kết luận = Đạt` thì vòng phỏng vấn đó được xem là `pass` ngay.
- Nếu `Đánh giá / Kết luận = Không đạt` thì vòng phỏng vấn đó được xem là `fail` ngay.

Lưu ý nghiệp vụ:

- Một vòng phỏng vấn có thể có nhiều người tham gia phỏng vấn.
- Tuy nhiên chỉ có một người là người phỏng vấn chính, và kết luận của người này sẽ quyết định kết quả cuối cùng của vòng phỏng vấn.

## Quy ước người phỏng vấn chính theo từng vòng

Chốt nghiệp vụ theo từng vòng như sau:

- Vòng 1: Trưởng phòng ban
- Vòng 2: CEO
- Vòng 3: BOD
- Vòng 4: ABU

Ý nghĩa triển khai:

- Khi phát sinh nhiều người tham gia đánh giá trong cùng một vòng, hệ thống vẫn phải xác định rõ ai là người phỏng vấn chính theo mapping trên.
- Kết luận của người phỏng vấn chính mới là kết luận quyết định pass/fail cho vòng đó.
- Các đánh giá còn lại chỉ mang tính tham khảo.

## Hiện trạng trong code

Logic hiện tại đang nằm chủ yếu trong file `addons/M02_P0205/models/hr_applicant.py`:

- `_update_interview_round_outcome()`
- `_compute_eval_round_metrics()`
- model `hr.applicant.evaluation`

Cách xử lý hiện tại:

- Hệ thống lấy tất cả các bản ghi đánh giá của cùng một vòng.
- Sau đó cộng/trừ điểm theo `recommendation`:
  - `pass` = `+1`
  - `consider` = `0`
  - `fail` = `-1`
- Kết quả cuối cùng đang phụ thuộc vào tổng hợp của nhiều người đánh giá.

Điều này chưa đúng với yêu cầu mới vì nghiệp vụ cần dựa vào người phỏng vấn chính, không phải tổng hợp điểm của toàn bộ người tham gia.

## Những gì đã có sẵn để tái sử dụng

### 1. Xác định Trưởng phòng ban

Module đã có pattern để tìm manager user của phòng ban qua:

- `_find_applicant_manager_user()` trong `models/hr_applicant.py`
- `_find_applicant_manager_user()` trong `models/survey_ext.py`

Pattern hiện tại:

- ưu tiên `job.department_id`
- fallback `department_id`
- fallback `recruitment.request.line.department_id`

Có thể tái sử dụng cho vòng 1.

### 2. Xác định CEO

Module đã có cách lấy CEO qua:

- `company_id.ceo_id.user_id`

Đang dùng trong:

- `_notify_ceo_round2()` tại `models/hr_applicant.py`
- một số logic tại `models/recruitment_plan.py`

Có thể tái sử dụng cho vòng 2.

### 3. Pattern gửi activity cho một user cụ thể

Module đã có nhiều chỗ dùng `activity_schedule()` khi đã biết `user_id`, ví dụ cho recruiter, manager, CEO.

Có thể tái sử dụng nếu một số vòng được chốt theo user cụ thể.

### 4. Pattern gửi activity theo group

Module đã có helper `_schedule_activity_for_group()` trong `models/recruitment_request.py`.

Tuy nhiên helper hiện tại mới chỉ schedule cho `users[0]`, chưa gửi cho toàn bộ user trong group.

Điều này có nghĩa là:

- pattern theo group đã có
- nhưng cần mở rộng thêm để phù hợp với BOD và ABU

### 5. Group của BOD và ABU đã tồn tại

Đã có sẵn trong `security/approval_groups.xml`:

- `M02_P0205.group_bod_recruitment`
- `M02_P0205.group_abu_recruitment`

### 6. Field và flow đánh giá theo vòng đã tồn tại

Đã có sẵn các field:

- `eval_round_1_score` ... `eval_round_4_score`
- `eval_round_1_pass` ... `eval_round_4_pass`
- `eval_round_1_toggle` ... `eval_round_4_toggle`

Đã có sẵn các hàm:

- `_recommendation_score()`
- `_update_interview_round_outcome()`
- `_compute_eval_round_metrics()`
- `_ensure_previous_round_completed()`

Điều này cho phép sửa rule tính toán mà không phải dựng lại toàn bộ flow qua vòng.

### 7. `recommendation` và `interviewer_id` đã có sẵn

Trong model `hr.applicant.evaluation`, module đã có sẵn:

- `interviewer_id`
- `recommendation` với các giá trị `pass`, `fail`, `consider`

Nghĩa là nền tảng dữ liệu đã có, chỉ thiếu rule nghiệp vụ mới.

## Các quyết định đã chốt để triển khai

### 1. Cách xác định người phỏng vấn chính cho BOD và ABU

Chốt như sau:

- BOD và ABU được quản lý theo `group` để nhận activity và gom danh sách người liên quan.
- Nhưng người phỏng vấn chính phải là một `user` cụ thể, không xác định mơ hồ theo group.

Định hướng triển khai:

- Thêm field kiểu `Many2one(res.users)` để lưu người phỏng vấn chính cho vòng 3 và vòng 4.
- Activity vẫn gửi cho toàn bộ group tương ứng.
- Chỉ user được chọn là người phỏng vấn chính mới quyết định kết luận cuối cùng của vòng.

### 2. Có cho phép chọn tay người phỏng vấn chính hay không

Chốt như sau:

- Hệ thống được phép auto gợi ý hoặc auto gán mặc định.
- Nhưng vẫn cho phép người dùng chỉnh tay người phỏng vấn chính.

Định hướng triển khai:

- Vòng 1: auto gợi ý theo Trưởng phòng ban.
- Vòng 2: auto gợi ý theo CEO.
- Vòng 3 và 4: HR chọn người chính trong group tương ứng.
- Chỉ user có quyền phù hợp mới được chỉnh tay.

### 3. Nếu chưa có đánh giá của người chính thì xử lý thế nào

Chốt như sau:

- Giữ trạng thái chưa kết luận.
- Không pass/fail tự động.
- Không mở vòng tiếp theo.

Định hướng triển khai:

- `eval_round_X_toggle = False`
- Không tự động chuyển luồng sang vòng kế tiếp.
- Có thể hiển thị cảnh báo trên applicant rằng vòng hiện tại chưa có kết luận từ người phỏng vấn chính.

### 4. `consider` sẽ xử lý thế nào

Chốt như sau:

- Giữ `consider`.
- Diễn giải lại thành trạng thái trung gian: “chưa kết luận / cần xem xét thêm”.
- `consider` không được xem là pass.
- `consider` cũng không tự động reject.

Định hướng triển khai:

- Với người phỏng vấn chính:
  - `pass` => qua vòng
  - `fail` => fail vòng
  - `consider` => giữ nguyên, chưa kết luận
- Không dùng `consider` trong phép cộng điểm quyết định nghiệp vụ nữa.

### 5. `eval_round_X_score` còn vai trò gì

Chốt như sau:

- Giữ `eval_round_X_score` nhưng chỉ để tham khảo hoặc phục vụ báo cáo.
- Không dùng score để quyết định pass/fail nghiệp vụ.

Định hướng triển khai:

- `eval_round_X_score` vẫn có thể tính từ toàn bộ đánh giá trong vòng.
- `eval_round_X_pass` và `eval_round_X_toggle` chỉ lấy theo kết luận của người phỏng vấn chính.

### 6. Cách xử lý dữ liệu cũ

Chốt như sau:

- Không migrate cứng toàn bộ dữ liệu cũ ở đợt đầu.
- Chấp nhận rằng applicant cũ có thể rơi vào trạng thái “chưa kết luận” nếu chưa xác định được người phỏng vấn chính.
- Chỉ migrate khi có quy tắc đủ rõ và an toàn.

Định hướng triển khai:

- Dữ liệu mới áp dụng full rule mới.
- Dữ liệu cũ được rà soát dần nếu cần.
- Có thể bổ sung bộ lọc hoặc báo cáo để HR xử lý các applicant cũ chưa có primary interviewer.

### 7. Quyền của group BOD và ABU

Chốt như sau:

- Không mở quyền rộng ngay từ đầu.
- Rà quyền hiện tại trên applicant, evaluation, calendar event.
- Chỉ bổ sung đúng quyền còn thiếu để BOD/ABU thao tác trong flow mới.

Định hướng triển khai:

- Kiểm tra `approval_groups.xml` và `ir.model.access.csv`.
- Nếu button vòng 3/4 chuyển cho BOD/ABU thao tác trực tiếp, sẽ cấp thêm quyền tối thiểu cần thiết.

## Hướng chỉnh sửa đề xuất

### 1. Bổ sung khái niệm người phỏng vấn chính

Tại model `hr.applicant.evaluation`, thêm một cờ để xác định bản đánh giá nào là bản đánh giá chính, ví dụ:

- `is_primary_interviewer = fields.Boolean(...)`

Ý nghĩa:

- Mỗi vòng phỏng vấn chỉ nên có tối đa 1 bản đánh giá được đánh dấu là chính.
- Nếu có nhiều người tham gia phỏng vấn, các bản đánh giá phụ chỉ mang tính tham khảo.
- Kết luận cuối cùng của vòng sẽ đọc từ bản đánh giá chính.

### 2. Ràng buộc dữ liệu

Thêm ràng buộc để đảm bảo:

- Với mỗi `applicant_id + interview_round`, chỉ có tối đa 1 bản ghi có `is_primary_interviewer = True`.

Ưu tiên dùng Python constraint trong model `hr.applicant.evaluation` để dễ kiểm soát thông báo lỗi nghiệp vụ.

### 3. Tự động xác định người phỏng vấn chính theo vòng

Ngoài việc có cờ `is_primary_interviewer`, bổ sung logic xác định người phỏng vấn chính theo đúng nghiệp vụ:

- Vòng 1: người phỏng vấn chính là Trưởng phòng ban
- Vòng 2: người phỏng vấn chính là CEO
- Vòng 3: người phỏng vấn chính là BOD
- Vòng 4: người phỏng vấn chính là ABU

Hướng xử lý đề xuất:

- Vòng 1: tái sử dụng pattern `_find_applicant_manager_user()`
- Vòng 2: tái sử dụng `company_id.ceo_id.user_id`
- Vòng 3 và 4: dùng group để gửi activity, nhưng lưu người chính bằng `user` cụ thể

### 4. Đổi logic tính kết quả vòng phỏng vấn

Sửa `_update_interview_round_outcome()` theo hướng:

- Tìm bản đánh giá chính của đúng vòng phỏng vấn.
- Nếu `recommendation = 'pass'`:
  - đánh dấu vòng đó là đạt
  - cho phép đi tiếp vòng sau
- Nếu `recommendation = 'fail'`:
  - đánh dấu vòng đó là không đạt
  - chuyển ứng viên sang `stage_office_reject`
- Nếu `recommendation = 'consider'`:
  - giữ trạng thái chưa kết luận
  - không pass/fail
- Nếu chưa có bản đánh giá chính:
  - chưa kết luận vòng
  - không tự động pass/fail

Điểm quan trọng:

- Không dùng tổng điểm của nhiều người đánh giá để kết luận nữa.
- Không dùng rule `total_score >= 0` như hiện tại.

### 5. Đổi logic compute hiển thị trên applicant

Sửa `_compute_eval_round_metrics()` để:

- Lấy kết quả từ bản đánh giá chính của từng vòng.
- Đồng bộ các field:
  - `eval_round_X_pass`
  - `eval_round_X_toggle`
  - `eval_round_X_score`

Định hướng:

- `eval_round_X_pass = 'pass'` khi bản đánh giá chính có `recommendation = 'pass'`
- `eval_round_X_pass = 'fail'` khi bản đánh giá chính có `recommendation = 'fail'`
- `eval_round_X_pass` để rỗng hoặc ở trạng thái chưa kết luận khi người chính chọn `consider` hoặc chưa có đánh giá chính
- `eval_round_X_toggle = True` chỉ khi bản đánh giá chính là `pass`
- `eval_round_X_score` chỉ còn ý nghĩa tham khảo nếu vẫn giữ lại

### 6. Cập nhật giao diện đánh giá

Tại view của `hr.applicant.evaluation` và/hoặc list đánh giá theo vòng:

- Hiển thị thêm cột hoặc field đánh dấu người phỏng vấn chính
- Hiển thị rõ `interviewer_id`
- Có thể bổ sung cảnh báo nếu vòng hiện tại chưa có kết luận từ người phỏng vấn chính

Nếu cần hạn chế sai thao tác, có thể:

- chỉ cho một số nhóm quyền chỉnh field này
- hoặc auto gợi ý rồi cho phép chỉnh lại

### 7. Giữ nguyên flow qua vòng, nhưng đổi rule quyết định `toggle`

Hiện module đã có:

- `_ensure_previous_round_completed()`
- các button phụ thuộc `eval_round_1_toggle`, `eval_round_2_toggle`, `eval_round_3_toggle`

Vì vậy hướng triển khai là:

- giữ nguyên khung flow qua vòng
- chỉ đổi tiêu chí tính `eval_round_X_toggle` để phản ánh đúng kết luận của người phỏng vấn chính

### 8. Bổ sung activity cho BOD và ABU khi tới vòng của họ

Hiện trạng cần bổ sung:

- Khi hoàn tất vòng trước và ứng viên chuyển tới vòng 3 hoặc vòng 4, hiện chưa có activity thông báo đầy đủ cho BOD và ABU để họ vào tạo lịch phỏng vấn và gửi lịch cho vòng của mình.

Yêu cầu triển khai:

- Khi đến vòng 3:
  - hệ thống tạo activity cho toàn bộ user trong group `BOD`
  - mục tiêu là nhắc vào tạo lịch và gửi lịch vòng 3
- Khi đến vòng 4:
  - hệ thống tạo activity cho toàn bộ user trong group `ABU`
  - mục tiêu là nhắc vào tạo lịch và gửi lịch vòng 4

Nguyên tắc gửi activity:

- Mở rộng pattern gửi theo group hiện có.
- Không chỉ gửi cho `users[0]`.
- Có kiểm tra tránh tạo activity trùng lặp.
- Ưu tiên chống duplicate theo `applicant + round + user`.

### 9. Rà soát button và quyền thao tác cho vòng 3 và 4

Hiện module đã có:

- `action_send_interview_round3_notification()`
- `action_send_interview_round4_notification()`
- các button tương ứng trên form applicant

Do đó cần rà:

- Button gửi lịch vòng 3 và 4 có còn do HR thao tác hay chuyển cho BOD/ABU?
- Có cần đổi `groups` hiển thị button trên view không?
- Có cần phân quyền riêng cho BOD/ABU trong flow mới không?

## Các file dự kiến cần sửa

- `addons/M02_P0205/models/hr_applicant.py`
- `addons/M02_P0205/views/hr_applicant_views.xml`
- `addons/M02_P0205/security/approval_groups.xml`

Có thể cần thêm:

- `addons/M02_P0205/security/ir.model.access.csv`
- dữ liệu migrate hoặc báo cáo rà soát dữ liệu cũ nếu cần

## Kết quả mong muốn sau chỉnh sửa

- Mỗi vòng phỏng vấn có thể có nhiều người đánh giá.
- Nhưng chỉ một người được xác định là người phỏng vấn chính.
- Người phỏng vấn chính được xác định theo nghiệp vụ:
  - Vòng 1: Trưởng phòng ban
  - Vòng 2: CEO
  - Vòng 3: BOD
  - Vòng 4: ABU
- Kết luận của người phỏng vấn chính quyết định trực tiếp pass/fail của vòng.
- `Đạt` thì qua vòng ngay.
- `Không đạt` thì fail vòng ngay.
- `consider` được giữ như trạng thái chờ kết luận, không tự động qua hoặc loại.
- Các đánh giá phụ vẫn được lưu để tham khảo, nhưng không quyết định kết quả vòng.
- `eval_round_X_score` vẫn còn để tham khảo hoặc báo cáo, nhưng không quyết định nghiệp vụ.
- Khi đến vòng 3 hoặc vòng 4, hệ thống sẽ tạo activity thông báo cho toàn bộ user trong group BOD hoặc ABU tương ứng để họ vào tạo lịch và gửi lịch phỏng vấn cho vòng của mình.
- Các flow cũ có thể tái sử dụng sẽ được giữ lại, chỉ thay đổi phần rule nghiệp vụ và phân vai thực thi.

## Kết luận triển khai

Module `0205` hiện đã có khá nhiều nền tảng sẵn để triển khai plan:

- có cách tìm Trưởng phòng ban
- có cách lấy CEO
- có pattern tạo activity
- có group BOD/ABU
- có sẵn các field và flow pass/fail theo vòng

Vì vậy hướng triển khai phù hợp là:

1. Tái sử dụng các helper hiện có để xác định user và gửi activity.
2. Xây mới rule nghiệp vụ xác định người phỏng vấn chính.
3. Đổi cách tính pass/fail từ “tổng hợp nhiều người” sang “kết luận của người chính”.
4. Giữ `consider` như trạng thái trung gian chưa kết luận.
5. Giữ score cho mục đích tham khảo/báo cáo.
6. Rà quyền của BOD/ABU theo nguyên tắc cấp đủ dùng.
7. Không migrate cứng dữ liệu cũ ở bước đầu; ưu tiên triển khai an toàn cho dữ liệu mới trước.

## Từng bước triển khai

### Bước 1. Rà và chuẩn bị dữ liệu người phỏng vấn chính

- Xác nhận lại các nguồn dữ liệu để lấy:
  - Trưởng phòng ban
  - CEO
  - group BOD
  - group ABU
- Quyết định chính xác field nào sẽ lưu người phỏng vấn chính cho từng vòng.
- Chốt nơi nào được quyền chỉnh tay các field này.

#### Kết quả rà soát và chốt triển khai cho Bước 1

##### 1. Nguồn dữ liệu đã xác nhận trong module hiện tại

- Vòng 1 - Trưởng phòng ban:
  - tái sử dụng helper `_find_applicant_manager_user()` trong `models/hr_applicant.py`
  - thứ tự fallback hiện có:
    - `job_id.department_id.manager_id.user_id`
    - `department_id.manager_id.user_id`
    - `recruitment.request.line.department_id.manager_id.user_id`
- Vòng 2 - CEO:
  - tái sử dụng field `company_id.ceo_id.user_id`
  - field `ceo_id` đang được khai báo tại `models/res_company.py`
  - hiện đã có view cấu hình tại `views/res_company_views.xml`
- Vòng 3 - BOD:
  - lấy danh sách ứng viên người phỏng vấn chính từ group `M02_P0205.group_bod_recruitment`
  - source data thực tế là `res.groups.users`
- Vòng 4 - ABU:
  - lấy danh sách ứng viên người phỏng vấn chính từ group `M02_P0205.group_abu_recruitment`
  - source data thực tế là `res.groups.users`

##### 2. Cách lưu người phỏng vấn chính

- Chốt lưu người phỏng vấn chính theo từng vòng ngay trên `hr.applicant`, không lưu rải rác chỉ trong từng dòng đánh giá.
- Lý do:
  - applicant là nơi điều phối flow qua vòng
  - các button, activity, và điều kiện mở vòng sau đều đang bám applicant
  - cần một nguồn dữ liệu duy nhất để biết “ai là người quyết định kết quả vòng”
- Đề xuất field sẽ bổ sung ở Bước 2:
  - `primary_interviewer_l1_user_id`
  - `primary_interviewer_l2_user_id`
  - `primary_interviewer_l3_user_id`
  - `primary_interviewer_l4_user_id`
- Kiểu field:
  - `Many2one('res.users')`
- Vai trò từng field:
  - vòng 1: lưu user Trưởng phòng ban của applicant
  - vòng 2: lưu user CEO của công ty
  - vòng 3: lưu user chính được chọn trong group BOD
  - vòng 4: lưu user chính được chọn trong group ABU

##### 3. Quan hệ giữa applicant và evaluation

- `interviewer_id` trên `hr.applicant.evaluation` vẫn được giữ để biết ai là người thực hiện bản đánh giá cụ thể.
- Kết quả vòng sẽ không đọc trực tiếp từ “mọi evaluation”.
- Thay vào đó:
  - applicant giữ user phỏng vấn chính của từng vòng
  - evaluation nào có `interviewer_id` trùng với user chính của vòng đó thì được xem là bản đánh giá quyết định
- Ở bước sau có thể bổ sung thêm cờ hỗ trợ hiển thị như:
  - `is_primary_interviewer`
  - hoặc compute/helper tương đương
- Nhưng nguồn quyết định gốc vẫn là field trên applicant, không phải checkbox nhập tay phân tán trên từng evaluation.

##### 4. Quy tắc auto gán và chỉnh tay

- Vòng 1:
  - hệ thống auto gán từ `_find_applicant_manager_user()`
  - vẫn cho phép HR chỉnh tay khi cần
- Vòng 2:
  - hệ thống auto gán từ `company_id.ceo_id.user_id`
  - vẫn cho phép HR chỉnh tay khi cần
- Vòng 3:
  - không auto chốt theo một user cố định
  - HR chọn tay 1 user thuộc group BOD
- Vòng 4:
  - không auto chốt theo một user cố định
  - HR chọn tay 1 user thuộc group ABU

##### 5. Chốt phạm vi được quyền chỉnh tay

- Chốt giai đoạn đầu:
  - chỉ HR thao tác trên applicant được quyền chỉnh các field người phỏng vấn chính
- Phạm vi ưu tiên:
  - `hr_recruitment.group_hr_recruitment_user`
  - nếu cần giữ đồng nhất với flow hiện tại, có thể mở thêm cho `hr_recruitment.group_hr_recruitment_manager`
- Không mở quyền chỉnh các field này trực tiếp cho BOD hoặc ABU ở đợt đầu.
- BOD và ABU ở giai đoạn đầu chủ yếu:
  - nhận activity
  - vào tạo lịch / đánh giá theo vai trò của mình
  - không tự quyết định thay đổi người phỏng vấn chính của vòng

##### 6. Ghi nhận thêm về quyền dữ liệu hiện tại

- Group `group_bod_recruitment` và `group_abu_recruitment` hiện đang `imply` từ `hr.group_hr_manager`.
- `ir.model.access.csv` hiện đã có quyền CRUD khá rộng cho `base.group_user` trên `hr.applicant.evaluation`.
- Điều này cho thấy:
  - dữ liệu nền hiện chưa khóa chặt theo vai trò BOD/ABU
  - nhưng ở bước triển khai đầu tiên vẫn nên chốt UI chỉnh tay người phỏng vấn chính ở phía HR để tránh mở luồng chỉnh sửa quá rộng

##### 7. Kết luận thực thi cho các bước sau

- Bước 2 sẽ thêm 4 field `Many2one(res.users)` trên applicant để lưu người phỏng vấn chính từng vòng.
- Bước 4 sẽ đưa các field này lên form applicant cho HR chỉnh tay.
- Bước 5 và Bước 6 sẽ dùng các field này làm nguồn quyết định pass/fail và mở vòng tiếp theo.
- Bước 8 sẽ dùng:
  - user cụ thể từ field applicant để xác định người quyết định kết quả
  - group BOD/ABU để gửi activity cho toàn bộ người liên quan

### Bước 2. Bổ sung field nghiệp vụ trên model đánh giá hoặc applicant

- Thêm field phục vụ xác định người phỏng vấn chính.
- Tùy thiết kế cuối cùng, có thể thêm:
  - `is_primary_interviewer` trên `hr.applicant.evaluation`
  - và/hoặc field `Many2one(res.users)` để lưu user chính theo từng vòng trên applicant
- Đảm bảo các field mới đủ rõ để dùng cho cả UI lẫn logic pass/fail.

### Bước 3. Thêm ràng buộc dữ liệu

- Bổ sung Python constraint để đảm bảo mỗi vòng chỉ có tối đa 1 bản đánh giá chính.
- Nếu cần, thêm validate để ngăn trạng thái dữ liệu mâu thuẫn.

### Bước 4. Cập nhật giao diện đánh giá

- Hiển thị người phỏng vấn chính trên form/list đánh giá.
- Nếu cho phép chỉnh tay, thêm field tương ứng vào UI.
- Bổ sung cảnh báo “chưa có kết luận từ người phỏng vấn chính” nếu cần.

### Bước 5. Đổi logic xác định kết quả vòng

- Sửa `_update_interview_round_outcome()`.
- Bỏ logic cộng điểm của nhiều người để quyết định pass/fail.
- Chuyển sang rule:
  - `pass` của người chính => qua vòng
  - `fail` của người chính => fail vòng
  - `consider` hoặc chưa có đánh giá chính => chưa kết luận

### Bước 6. Đổi logic compute trên applicant

- Sửa `_compute_eval_round_metrics()`.
- Tách rõ:
  - field nào dùng cho nghiệp vụ qua vòng
  - field nào chỉ để tham khảo/báo cáo
- Đảm bảo `eval_round_X_toggle` chỉ bật khi người chính kết luận `pass`.

### Bước 7. Cập nhật flow mở vòng tiếp theo

- Giữ nguyên khung `_ensure_previous_round_completed()` và các button hiện có.
- Chỉ cập nhật điều kiện để flow qua vòng dựa trên kết quả của người phỏng vấn chính.
- Kiểm tra lại toàn bộ các nút gửi lịch vòng 2, 3, 4.

### Bước 8. Bổ sung activity cho CEO, BOD, ABU

- Tách helper gửi activity để tái sử dụng.
- Giữ logic CEO hiện tại làm pattern.
- Mở rộng cho:
  - group BOD ở vòng 3
  - group ABU ở vòng 4
- Đảm bảo gửi cho toàn bộ user trong group và có chống duplicate.

### Bước 9. Rà quyền và button cho BOD/ABU

- Kiểm tra lại `approval_groups.xml`.
- Kiểm tra lại `ir.model.access.csv`.
- Nếu BOD/ABU cần thao tác trực tiếp trên applicant hoặc lịch, bổ sung đúng quyền tối thiểu.
- Nếu cần, đổi `groups` hiển thị button trên view applicant.

### Bước 10. Xử lý dữ liệu cũ theo hướng an toàn

- Không migrate cứng toàn bộ ở bước đầu.
- Đảm bảo dữ liệu cũ không làm vỡ flow mới.
- Nếu cần, tạo báo cáo hoặc bộ lọc để HR rà các applicant cũ chưa có người phỏng vấn chính.

### Bước 11. Kiểm thử nghiệp vụ end-to-end

- Test trường hợp mỗi vòng chỉ có 1 người đánh giá.
- Test trường hợp 1 vòng có nhiều người đánh giá nhưng chỉ 1 người là chính.
- Test các nhánh:
  - `pass`
  - `fail`
  - `consider`
  - chưa có đánh giá chính
- Test việc tạo activity cho CEO, BOD, ABU.
- Test quyền hiển thị và thao tác của HR, BOD, ABU.

### Bước 12. Hoàn thiện tài liệu và note sau triển khai

- Cập nhật lại plan hoặc note nếu có thay đổi so với giả định ban đầu.
- Ghi lại các quyết định cuối cùng về:
  - cách chọn người phỏng vấn chính
  - cách xử lý `consider`
  - cách xử lý dữ liệu cũ
