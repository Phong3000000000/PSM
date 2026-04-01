# Kịch bản test end-to-end cho logic đánh giá phỏng vấn

## Mục tiêu

Tài liệu này dùng để kiểm thử thủ công các thay đổi đã triển khai cho flow:

- người phỏng vấn chính theo từng vòng
- pass/fail dựa trên kết luận của người phỏng vấn chính
- `consider` là trạng thái chưa kết luận
- activity cho CEO, BOD, ABU
- quyền hiển thị và thao tác của HR, BOD, ABU
- xử lý dữ liệu cũ theo hướng an toàn

## Chuẩn bị dữ liệu test

### Tài khoản cần có

- 1 tài khoản HR có quyền thao tác applicant office
- 1 tài khoản CEO
- 1 tài khoản BOD thuộc group `M02_P0205_00.group_bod_recruitment`
- 1 tài khoản ABU thuộc group `M02_P0205_00.group_abu_recruitment`
- nếu cần test nhiều người đánh giá trong cùng vòng:
  - thêm 1 user phụ cho vòng 2
  - thêm 1 user phụ cho vòng 3
  - thêm 1 user phụ cho vòng 4

### Dữ liệu master cần kiểm tra trước

- `res.company.ceo_id` đã có employee và employee đó có `user_id`
- Job Position test có `department_id`
- Department test có `manager_id.user_id`
- group BOD có ít nhất 1 user
- group ABU có ít nhất 1 user

### Applicant test đề xuất

- `APP-01`: dùng cho luồng pass toàn bộ
- `APP-02`: dùng cho luồng fail
- `APP-03`: dùng cho luồng consider
- `APP-04`: dùng cho luồng chưa có đánh giá của người chính
- `APP-05`: dùng cho test nhiều người đánh giá trong cùng 1 vòng
- `APP-06`: dùng cho test dữ liệu cũ / thiếu người phỏng vấn chính

## Checklist kiểm thử

### 1. Test dữ liệu nền sau khi mở form applicant

#### Bước thực hiện

1. Mở applicant office mới.
2. Kiểm tra block `Người phỏng vấn chính`.
3. Chọn job/department/company đầy đủ dữ liệu.

#### Kết quả mong đợi

- `Người phỏng vấn chính Vòng 1` được gợi ý theo Trưởng phòng ban.
- `Người phỏng vấn chính Vòng 2` được gợi ý theo CEO.
- `Người phỏng vấn chính Vòng 3` chỉ chọn được user thuộc group BOD.
- `Người phỏng vấn chính Vòng 4` chỉ chọn được user thuộc group ABU.

### 2. Test mỗi vòng chỉ có 1 người đánh giá

#### Bước thực hiện

1. Dùng `APP-01`.
2. Gán đầy đủ người phỏng vấn chính cho 4 vòng.
3. Ở mỗi vòng chỉ tạo 1 evaluation, và `interviewer_id` chính là người phỏng vấn chính của vòng đó.
4. Lần lượt test các nhánh `pass`, `fail`, `consider`.

#### Kết quả mong đợi

- Nếu người chính chọn `pass`:
  - `eval_round_X_pass = pass`
  - `eval_round_X_toggle = True`
- Nếu người chính chọn `fail`:
  - `eval_round_X_pass = fail`
  - `eval_round_X_toggle = False`
  - applicant bị chuyển sang `Reject`
- Nếu người chính chọn `consider`:
  - `eval_round_X_pass` để trống
  - `eval_round_X_toggle = False`
  - applicant không qua vòng tiếp theo

### 3. Test 1 vòng có nhiều người đánh giá nhưng chỉ 1 người là chính

#### Bước thực hiện

1. Dùng `APP-05`.
2. Chọn rõ người phỏng vấn chính cho vòng test.
3. Tạo ít nhất 2 evaluation trong cùng vòng:
  - 1 evaluation của người chính
  - 1 evaluation của người phụ
4. Test các tổ hợp sau:
  - người chính `pass`, người phụ `fail`
  - người chính `fail`, người phụ `pass`
  - người chính `consider`, người phụ `pass`

#### Kết quả mong đợi

- `eval_round_X_score` vẫn thay đổi theo tổng các evaluation.
- `eval_round_X_pass` và `eval_round_X_toggle` chỉ bám theo evaluation của người chính.
- Trường hợp người phụ khác kết luận với người chính:
  - hệ thống vẫn lấy kết luận của người chính làm quyết định cuối cùng.

### 4. Test nhánh `pass`

#### Vòng 1 -> Vòng 2

1. Dùng `APP-01`.
2. Tạo evaluation vòng 1 bởi người chính với `recommendation = pass`.

#### Kết quả mong đợi

- `eval_round_1_toggle = True`
- hiện được các nút liên quan vòng 2
- tạo activity cho CEO với nội dung lên lịch vòng 2

#### Vòng 2 -> Vòng 3

1. Tạo evaluation vòng 2 bởi người chính với `recommendation = pass`.

#### Kết quả mong đợi

- `eval_round_2_toggle = True`
- hiện được các nút liên quan vòng 3
- toàn bộ user trong group BOD nhận activity lên lịch vòng 3

#### Vòng 3 -> Vòng 4

1. Tạo evaluation vòng 3 bởi người chính với `recommendation = pass`.

#### Kết quả mong đợi

- `eval_round_3_toggle = True`
- hiện được các nút liên quan vòng 4
- toàn bộ user trong group ABU nhận activity lên lịch vòng 4

#### Vòng 4 -> Offer

1. Tạo evaluation vòng 4 bởi người chính với `recommendation = pass`.

#### Kết quả mong đợi

- `eval_round_4_toggle = True`
- hiện nút `Sẵn sàng Offer`
- bấm `Sẵn sàng Offer` thì applicant chuyển sang stage `Offer`

### 5. Test nhánh `fail`

#### Bước thực hiện

1. Dùng `APP-02`.
2. Ở một vòng bất kỳ, tạo evaluation của người chính với `recommendation = fail`.

#### Kết quả mong đợi

- applicant bị chuyển sang stage `Reject`
- có message ghi rõ bị loại theo kết luận của người phỏng vấn chính
- không hiện nút của vòng tiếp theo
- không tạo activity mở vòng tiếp theo

### 6. Test nhánh `consider`

#### Bước thực hiện

1. Dùng `APP-03`.
2. Tạo evaluation của người chính với `recommendation = consider`.

#### Kết quả mong đợi

- `eval_round_X_pass` để trống
- `eval_round_X_toggle = False`
- xuất hiện cảnh báo trên tab vòng đó rằng người chính đang ở trạng thái cần xem xét thêm
- không tạo activity mở vòng tiếp theo
- không hiện nút qua vòng tiếp theo

### 7. Test nhánh chưa có đánh giá của người chính

#### Bước thực hiện

1. Dùng `APP-04`.
2. Gán người phỏng vấn chính cho vòng test.
3. Chỉ tạo evaluation của người phụ, không tạo evaluation của người chính.

#### Kết quả mong đợi

- `eval_round_X_pass` để trống
- `eval_round_X_toggle = False`
- có cảnh báo “đang chờ đánh giá từ người phỏng vấn chính”
- không tạo activity mở vòng tiếp theo
- không hiện nút qua vòng tiếp theo

### 8. Test constraint dữ liệu

#### Test 1: người chính vòng 3 không thuộc group BOD

1. Trên applicant, thử gán `Người phỏng vấn chính Vòng 3` bằng user không thuộc group BOD.

#### Kết quả mong đợi

- hệ thống chặn lưu và báo lỗi validation.

#### Test 2: người chính vòng 4 không thuộc group ABU

1. Trên applicant, thử gán `Người phỏng vấn chính Vòng 4` bằng user không thuộc group ABU.

#### Kết quả mong đợi

- hệ thống chặn lưu và báo lỗi validation.

#### Test 3: 1 vòng có 2 evaluation cùng là người chính

1. Chọn người chính cho một vòng.
2. Tạo 2 evaluation cùng `interviewer_id` là người chính, cùng `interview_round`.

#### Kết quả mong đợi

- hệ thống chặn bản ghi thứ 2 và báo lỗi mỗi vòng chỉ có tối đa 1 bản đánh giá của người phỏng vấn chính.

### 9. Test activity cho CEO, BOD, ABU

#### Bước thực hiện

1. Dùng `APP-01`.
2. Cho pass lần lượt vòng 1, 2, 3.
3. Sau mỗi lần pass, kiểm tra menu Activities của user tương ứng.
4. Lưu ý test cả thao tác sửa evaluation nhiều lần để xem có duplicate hay không.

#### Kết quả mong đợi

- pass vòng 1:
  - CEO có đúng 1 activity `Lên lịch PV vòng 2`
- pass vòng 2:
  - mỗi user trong group BOD có đúng 1 activity `Lên lịch PV vòng 3`
- pass vòng 3:
  - mỗi user trong group ABU có đúng 1 activity `Lên lịch PV vòng 4`
- sửa lại evaluation cùng một kết luận không tạo activity trùng

### 10. Test quyền hiển thị và thao tác của HR, BOD, ABU

#### HR

##### Bước thực hiện

1. Đăng nhập bằng user HR.
2. Mở applicant office.

##### Kết quả mong đợi

- thấy block `Người phỏng vấn chính`
- chỉnh được người phỏng vấn chính
- thấy các nút HR:
  - `Gui lich PV L2`
  - `Gui lich PV L3`
  - `Gui lich PV L4`
  - `Mời PV L1`
  - `Mời PV L2`
  - `Mời PV L3`
  - `Mời PV L4`
  - `Sẵn sàng Offer`
  - `Gửi Offer`
  - `Xác nhận đã Ký`

#### BOD

##### Bước thực hiện

1. Đăng nhập bằng user BOD.
2. Mở applicant đã đủ điều kiện vào vòng 3.

##### Kết quả mong đợi

- thấy được các nút:
  - `Gui lich PV L3`
  - `Mời PV L3`
  - `Bắt đầu đánh giá Vòng 3`
- không thấy block chỉnh `Người phỏng vấn chính`
- không thấy các nút `Offer`

#### ABU

##### Bước thực hiện

1. Đăng nhập bằng user ABU.
2. Mở applicant đã đủ điều kiện vào vòng 4.

##### Kết quả mong đợi

- thấy được các nút:
  - `Gui lich PV L4`
  - `Mời PV L4`
  - `Bắt đầu đánh giá Vòng 4`
- không thấy block chỉnh `Người phỏng vấn chính`
- không thấy các nút `Offer`

### 11. Test xử lý dữ liệu cũ

#### Bước thực hiện

1. Dùng `APP-06`.
2. Tạo applicant theo kiểu dữ liệu cũ:
  - đã có interview date hoặc evaluation
  - nhưng chưa có người phỏng vấn chính ở 1 hoặc nhiều vòng
3. Mở form applicant.
4. Vào search view và dùng filter `Cần rà người PV chính`.

#### Kết quả mong đợi

- form applicant hiển thị cảnh báo cần rà người phỏng vấn chính
- filter `Cần rà người PV chính` tìm ra đúng applicant đó
- sau khi HR điền đủ người phỏng vấn chính, applicant biến mất khỏi filter

## Mẫu ghi nhận kết quả test

| Mã test | Nội dung | Kết quả mong đợi | Kết quả thực tế | Pass/Fail | Ghi chú |
|---|---|---|---|---|---|
| T01 | Mỗi vòng 1 người đánh giá | Toggle theo người chính |  |  |  |
| T02 | Nhiều người đánh giá, 1 người chính | Kết quả theo người chính |  |  |  |
| T03 | Nhánh pass | Qua vòng + tạo activity |  |  |  |
| T04 | Nhánh fail | Reject |  |  |  |
| T05 | Nhánh consider | Chưa kết luận |  |  |  |
| T06 | Chưa có đánh giá chính | Không qua vòng |  |  |  |
| T07 | Constraint dữ liệu | Chặn dữ liệu mâu thuẫn |  |  |  |
| T08 | Activity CEO/BOD/ABU | Không duplicate |  |  |  |
| T09 | Quyền HR/BOD/ABU | Hiển thị đúng button |  |  |  |
| T10 | Dữ liệu cũ | Có filter rà soát |  |  |  |

## Ghi chú khi test

- Sau mỗi nhánh `pass/fail/consider`, nên refresh form applicant để kiểm tra:
  - stage hiện tại
  - toggle
  - warning
  - activity
- Nếu test activity, nên kiểm tra cả:
  - chatter của applicant
  - menu Activities
  - số lượng activity trùng theo từng user
- Nếu phát sinh lỗi, nên chụp lại:
  - user đang đăng nhập
  - applicant đang test
  - vòng đang test
  - thao tác vừa bấm
  - traceback hoặc popup lỗi
