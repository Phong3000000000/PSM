# Các vướng mắc cần làm rõ trước khi triển khai plan đánh giá phỏng vấn

## Mục đích

File này dùng để liệt kê các điểm chưa rõ hoặc chưa chốt đủ thông tin trong plan `interview-evaluation-plan.md`, nhằm tránh triển khai sai nghiệp vụ hoặc phải sửa đi sửa lại sau khi code.

## 1. Cách xác định người phỏng vấn chính trong dữ liệu thực tế

Plan đã chốt theo nghiệp vụ:

- Vòng 1: Trưởng phòng ban
- Vòng 2: CEO
- Vòng 3: BOD
- Vòng 4: ABU

Nhưng hiện vẫn còn các câu hỏi kỹ thuật sau:

- Trưởng phòng ban sẽ được xác định từ `department.manager_id`, từ `job.department_id`, hay từ `recruitment.request.line.department_id`?
- CEO đang lấy từ field nào trong dữ liệu hiện tại? Có đang dùng `company_id.ceo_id` ổn định cho mọi công ty hay không?
- BOD và ABU sẽ được xác định theo:
  - user cụ thể
  - employee cụ thể
  - hay theo group quyền?
- Nếu trong group BOD hoặc ABU có nhiều user, ai là người được xem là người phỏng vấn chính thực sự?

## 2. Người phỏng vấn chính được xác định tự động hay chọn tay

Hiện có hai hướng triển khai khả thi:

1. Hệ thống tự động xác định người phỏng vấn chính theo role/group
2. Người dùng tự tick `is_primary_interviewer` trên bản đánh giá

Điểm chưa chốt:

- Có cho phép người dùng chỉnh tay người phỏng vấn chính không?
- Nếu hệ thống tự gán mà người dùng muốn đổi lại thì có được phép không?
- Nếu có nhiều bản đánh giá nhưng chưa có bản nào là chính, hệ thống sẽ:
  - giữ trạng thái chưa kết luận
  - hay tự động chọn một bản?

## 3. Trường hợp người phỏng vấn chính chưa tạo đánh giá

Đây là điểm rất quan trọng để tránh pass/fail sai:

- Nếu đã có đánh giá từ người phụ nhưng chưa có đánh giá của người chính thì hệ thống có được kết luận vòng hay không?
- Có cần chặn việc qua vòng tiếp theo cho đến khi người chính đánh giá xong không?
- Có cần hiển thị cảnh báo trên applicant rằng “chưa có kết luận từ người phỏng vấn chính” không?

## 4. Trường hợp `consider` sẽ xử lý thế nào

Hiện field `recommendation` vẫn đang có 3 giá trị:

- `pass`
- `fail`
- `consider`

Nhưng yêu cầu mới mới chỉ chốt:

- `Đạt` thì pass ngay
- `Không đạt` thì fail ngay

Điểm chưa rõ:

- Nếu người phỏng vấn chính chọn `consider` thì hệ thống sẽ xử lý thế nào?
- `consider` có còn được dùng nữa không?
- Nếu vẫn dùng, nó có nghĩa là:
  - chưa kết luận
  - chờ HR quyết định
  - hay cần thêm một bước phê duyệt?

## 5. Có cần giữ logic điểm số hay không

Hiện tại hệ thống có các field:

- `eval_round_X_score`
- `eval_round_X_pass`
- `eval_round_X_toggle`

Điểm chưa rõ:

- `eval_round_X_score` còn cần giữ để tham khảo hay bỏ hẳn ý nghĩa nghiệp vụ?
- Nếu vẫn giữ score, score chỉ để hiển thị hay còn ảnh hưởng tới báo cáo?
- Có màn hình hoặc báo cáo nào đang dùng score để quyết định nghiệp vụ mà chưa được rà hết không?

## 6. Thời điểm tạo activity cho CEO, BOD, ABU

Plan đã nêu cần bổ sung activity cho BOD và ABU, nhưng vẫn còn điểm phải chốt:

- Activity được tạo ngay khi vòng trước được kết luận `pass`, hay chỉ tạo khi applicant thật sự bước sang stage tiếp theo?
- Với CEO, BOD, ABU thì activity dùng chung một cơ chế hay mỗi nhóm một flow riêng?
- Nếu ứng viên bị chỉnh sửa lại kết quả vòng trước thì activity đã tạo cho vòng sau sẽ xử lý thế nào?

## 7. Cách gửi activity cho group BOD và ABU

Hiện định hướng là gửi cho toàn bộ user trong group:

- `M02_P0205_00.group_bod_recruitment`
- `M02_P0205_00.group_abu_recruitment`

Nhưng còn các điểm chưa rõ:

- Có gửi cho tất cả user trong group thật không, hay chỉ user đang active?
- Có cần bỏ qua user không có quyền thao tác lịch phỏng vấn không?
- Nếu group có nhiều người, có chấp nhận việc tất cả cùng nhận activity giống nhau không?
- Có cần cơ chế chống duplicate activity theo `applicant + round + user` không?

## 8. Hành động mong muốn của BOD và ABU sau khi nhận activity

Yêu cầu hiện nói rằng BOD và ABU cần được nhắc:

- vào tạo lịch
- và gửi lịch cho vòng của mình

Điểm chưa rõ:

- Sau khi nhận activity, BOD/ABU sẽ thao tác trực tiếp trên applicant hay trên calendar event?
- Có cần thêm nút riêng cho BOD/ABU hay dùng lại flow hiện tại?
- Có cần giới hạn quyền để chỉ BOD/ABU được gửi lịch vòng 3/4 không?

## 9. Ảnh hưởng tới các button hiện tại trên form applicant

Hiện form applicant đang có các button như:

- `Gui lich PV L2`
- `Gui lich PV L3`
- `Gui lich PV L4`
- `Mời PV L1` ... `Mời PV L4`

Điểm chưa rõ:

- Sau khi đổi rule theo người phỏng vấn chính, các button hiện tại có còn đúng vai trò không?
- Button gửi lịch vòng 3 và vòng 4 hiện đang do HR thao tác hay sẽ chuyển trách nhiệm cho BOD/ABU?
- Nếu BOD/ABU là người chịu trách nhiệm chính, có cần đổi group quyền hiển thị button không?

## 10. Ảnh hưởng tới dữ liệu cũ

Nếu đã có applicant cũ với nhiều đánh giá ở mỗi vòng, cần chốt:

- Sau khi deploy logic mới, hệ thống sẽ xác định lại kết quả cũ như thế nào?
- Các bản đánh giá cũ có cần migrate để đánh dấu `is_primary_interviewer` không?
- Nếu không migrate, applicant cũ có thể rơi vào trạng thái “chưa kết luận” hay không?

## 11. Cần rà thêm quyền và group

Plan đã nhắc tới group của BOD và ABU, nhưng vẫn cần xác nhận:

- External id group có đúng là:
  - `M02_P0205_00.group_bod_recruitment`
  - `M02_P0205_00.group_abu_recruitment`
- User trong các group này đã có đủ quyền đọc/ghi applicant, evaluation, calendar event chưa?
- Nếu chưa đủ, cần bổ sung access rule hay record rule nào?

## 12. Thông báo và giao diện cần hiển thị tới mức nào

Các điểm chưa rõ về UX:

- Có cần hiển thị rõ ai là người phỏng vấn chính trên tab đánh giá không?
- Có cần hiển thị badge/cảnh báo khi vòng chưa có kết luận của người chính không?
- Có cần hiển thị danh sách activity đã gửi cho BOD/ABU ngay trên form applicant không?

## Đề xuất cách chốt trước khi code

Nên chốt lần lượt các điểm sau:

1. Cơ chế xác định người phỏng vấn chính cho từng vòng.
2. Cách xử lý giá trị `consider`.
3. Quy tắc tạo activity cho CEO, BOD, ABU.
4. Phạm vi user trong group sẽ nhận activity.
5. Cách xử lý dữ liệu cũ sau khi đổi rule.

## Kết luận

Plan triển khai đã khá rõ về hướng tổng thể, nhưng để code an toàn và không phát sinh sửa vòng lặp, cần chốt thêm các vướng mắc ở trên, đặc biệt là:

- ai thực sự là người phỏng vấn chính trong dữ liệu hệ thống
- `consider` sẽ sống hay bỏ
- activity cho BOD/ABU sẽ được tạo ở thời điểm nào và gửi cho ai
- dữ liệu cũ sẽ được chuyển tiếp ra sao
