# Đề xuất chốt các điểm còn mở trước khi code

## Mục đích

File này tổng hợp các đề xuất thực thi cho những điểm còn phải chốt trong plan đánh giá phỏng vấn của module `M02_P0205`.

## 1. Cách xác định người phỏng vấn chính cho BOD và ABU

### Đề xuất

- Xác định theo `user` cụ thể, không chỉ theo `group`.
- `group_bod_recruitment` và `group_abu_recruitment` chỉ nên dùng để:
  - cấp quyền
  - gửi activity
  - gom danh sách người liên quan
- Người phỏng vấn chính nên là một user được chọn rõ ràng trên từng applicant hoặc từng event phỏng vấn.

### Lý do

- Nếu chỉ xác định theo group thì khi group có nhiều user sẽ không thể biết ai là người có kết luận cuối cùng.
- Việc pass/fail theo kết luận của “người chính” cần một bản ghi rõ ràng, truy vết được.

### Khuyến nghị triển khai

- Thêm field kiểu `Many2one(res.users)` để lưu:
  - `primary_interviewer_round_3_id`
  - `primary_interviewer_round_4_id`
- Khi tạo lịch hoặc khi bắt đầu vòng, HR chọn 1 người chính trong group tương ứng.
- Activity vẫn gửi cho toàn bộ group, nhưng chỉ user được chọn là người quyết định kết luận cuối cùng.

## 2. Có cho phép chọn tay người phỏng vấn chính hay không

### Đề xuất

- Cho phép hệ thống tự gợi ý hoặc tự gán mặc định.
- Nhưng vẫn cho phép người dùng chỉnh tay `is_primary_interviewer` hoặc user phỏng vấn chính.

### Lý do

- Dữ liệu thực tế thường có ngoại lệ.
- Nếu cứng hoàn toàn bằng auto-assign thì dễ sai khi người phụ trách thật thay đổi theo từng đợt tuyển dụng.

### Khuyến nghị triển khai

- Vòng 1: auto gợi ý theo Trưởng phòng ban.
- Vòng 2: auto gợi ý theo CEO.
- Vòng 3 và 4: auto gợi ý rỗng hoặc gợi ý user đầu tiên trong group, nhưng HR phải xác nhận lại.
- Chỉ cho HR Manager hoặc group phù hợp được quyền chỉnh tay.

## 3. Nếu chưa có đánh giá của người chính thì xử lý thế nào

### Đề xuất

- Giữ trạng thái chưa kết luận.
- Không pass/fail tự động.
- Không mở vòng tiếp theo.

### Lý do

- Đây là phương án an toàn nhất, tránh qua vòng sai khi mới có đánh giá phụ.
- Phù hợp với yêu cầu “kết luận của người phỏng vấn chính quyết định kết quả cuối cùng”.

### Khuyến nghị triển khai

- Nếu chưa có đánh giá từ người chính:
  - `eval_round_X_pass` để rỗng hoặc giữ `fail` giả lập là không phù hợp
  - `eval_round_X_toggle = False`
  - hiển thị cảnh báo trên applicant: “Chưa có kết luận từ người phỏng vấn chính”

## 4. `consider` sẽ xử lý thế nào

### Đề xuất

- Giữ `consider`, nhưng đổi nghĩa thành “chưa kết luận / cần xem xét thêm”.
- `consider` không được xem là pass.
- `consider` cũng không tự động reject.

### Lý do

- Xóa `consider` sẽ làm mất một trạng thái trung gian hữu ích về mặt nghiệp vụ.
- Nhưng để `consider = 0` như hiện tại sẽ khiến vòng có thể bị hiểu nhầm là đạt nếu tổng hợp nhiều người.

### Khuyến nghị triển khai

- Với người phỏng vấn chính:
  - `pass` => qua vòng
  - `fail` => fail vòng
  - `consider` => giữ nguyên, chưa kết luận
- Không dùng `consider` trong bất kỳ phép cộng điểm quyết định nghiệp vụ nào nữa.

## 5. `eval_round_X_score` còn vai trò gì

### Đề xuất

- Giữ lại `eval_round_X_score`, nhưng chỉ để tham khảo hoặc phục vụ báo cáo.
- Không dùng score để quyết định pass/fail nghiệp vụ.

### Lý do

- Score vẫn hữu ích để xem xu hướng đánh giá tổng thể.
- Nhưng nếu tiếp tục để score quyết định pass/fail thì sẽ mâu thuẫn với rule mới theo người phỏng vấn chính.

### Khuyến nghị triển khai

- `eval_round_X_score` tiếp tục compute từ toàn bộ đánh giá trong vòng.
- `eval_round_X_pass` và `eval_round_X_toggle` chỉ lấy theo người phỏng vấn chính.
- Nếu có báo cáo hiện tại dùng score, vẫn có thể giữ tương thích.

## 6. Cách xử lý dữ liệu cũ

### Đề xuất

- Không migrate tự động toàn bộ dữ liệu cũ ở bước đầu.
- Chấp nhận rằng applicant cũ có thể rơi vào trạng thái “chưa kết luận” nếu chưa xác định được người chính.
- Chỉ migrate khi có quy tắc đủ rõ.

### Lý do

- Dữ liệu cũ thường không đủ thông tin để suy ra chính xác ai là người phỏng vấn chính.
- Migrate đoán sai sẽ nguy hiểm hơn để trạng thái chờ xác nhận.

### Khuyến nghị triển khai

- Với dữ liệu mới: áp dụng đầy đủ rule mới.
- Với dữ liệu cũ:
  - nếu xác định được rõ người chính thì cập nhật
  - nếu không xác định được thì giữ trạng thái cần rà soát
- Có thể bổ sung một bộ lọc hoặc báo cáo để HR xử lý dần các applicant cũ chưa có primary interviewer.

## 7. Quyền của group BOD và ABU

### Đề xuất

- Không chỉnh vội access rộng ngay.
- Trước tiên rà quyền hiện tại của user trong group BOD/ABU trên:
  - applicant
  - evaluation
  - calendar event
- Sau đó chỉ bổ sung đúng quyền còn thiếu để họ làm được tác vụ của mình.

### Lý do

- Group BOD/ABU hiện mới là group nghiệp vụ, chưa chắc đã cần full quyền như HR.
- Nếu mở quyền quá rộng sẽ dễ phát sinh rủi ro thao tác ngoài phạm vi cần thiết.

### Khuyến nghị triển khai

- Kiểm tra:
  - `addons/M02_P0205/security/approval_groups.xml`
  - `addons/M02_P0205/security/ir.model.access.csv`
- Mục tiêu tối thiểu:
  - đọc applicant liên quan
  - tạo/sửa evaluation của vòng mình
  - tạo hoặc cập nhật lịch phỏng vấn nếu flow yêu cầu
- Nếu button vòng 3/4 chuyển cho BOD/ABU thao tác trực tiếp, cần cấp thêm quyền tương ứng trên form applicant và event.

## Khuyến nghị chốt cuối cùng

Nếu cần một bộ quyết định ngắn gọn để triển khai ngay, mình đề xuất chốt như sau:

1. BOD/ABU được quản lý theo group để nhận activity, nhưng người phỏng vấn chính phải là một `user` cụ thể.
2. Cho phép chỉnh tay người phỏng vấn chính, dù hệ thống có thể auto gợi ý ban đầu.
3. Nếu chưa có đánh giá của người chính thì giữ trạng thái chưa kết luận và không mở vòng tiếp theo.
4. Giữ `consider` như trạng thái chờ kết luận, không tham gia pass/fail.
5. Giữ `eval_round_X_score` chỉ để tham khảo và báo cáo.
6. Không migrate cứng dữ liệu cũ ở đợt đầu; xử lý dần theo danh sách cần rà soát.
7. Rà quyền của BOD/ABU theo nguyên tắc cấp đủ dùng, không cấp rộng mặc định.
