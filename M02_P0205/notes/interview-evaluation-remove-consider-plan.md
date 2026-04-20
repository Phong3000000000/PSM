# Plan bỏ luồng và nút liên quan đến `consider`

## Mục tiêu

Loại bỏ hoàn toàn nhánh nghiệp vụ `consider` trong phần đánh giá phỏng vấn của module `M02_P0205`.

Kết quả mong muốn sau chỉnh sửa:

- Người dùng chỉ còn 2 lựa chọn kết luận: `pass` hoặc `fail`.
- Không còn trạng thái trung gian `consider` trong form, tree, logic tính toán và flow nghiệp vụ.
- Hệ thống chỉ xử lý 2 nhánh:
  - `pass` => chuyển tiếp sang vòng tiếp theo hoặc bước offer
  - `fail` => loại ứng viên

## Hiện trạng liên quan đến `consider`

Các điểm còn dùng `consider` trong module:

- Field `recommendation` tại `models/hr_applicant.py`
  - hiện đang có 3 giá trị: `pass`, `fail`, `consider`
- Hàm `_recommendation_score()`
  - đang map `consider = 0`
- Hàm `_update_interview_round_outcome()`
  - đang có nhánh `if recommendation == 'consider': return`
- Các compute/tổng hợp vòng phỏng vấn
  - vẫn đang đọc `recommendation` và cho phép `consider` tồn tại như trạng thái chưa kết luận
- View `addons/M02_P0205/views/hr_applicant_views.xml`
  - phần radio `recommendation` ở form đánh giá các vòng
  - phần form `hr.applicant.evaluation`
  - phần tree `hr.applicant.evaluation`

## Phạm vi bỏ `consider`

### 1. Model dữ liệu

Điều chỉnh field `recommendation` chỉ còn:

- `pass`
- `fail`

Tác động:

- Không cho tạo mới evaluation với giá trị `consider`
- Các chỗ đọc dữ liệu phải coi mọi giá trị cũ `consider` là dữ liệu legacy cần xử lý an toàn

### 2. Flow nghiệp vụ

Bỏ hoàn toàn nhánh `consider` trong kết luận vòng phỏng vấn.

Sau khi sửa:

- Nếu người phỏng vấn chính chọn `pass`:
  - vòng hiện tại được xem là đạt
  - hệ thống gửi activity / mở bước tiếp theo như flow hiện tại
- Nếu người phỏng vấn chính chọn `fail`:
  - ứng viên bị chuyển sang `Reject`
- Không còn trạng thái “chưa kết luận vì chọn consider”

### 3. Nút và hiển thị liên quan

Về bản chất hiện tại `consider` không có nút riêng, nhưng nó đang xuất hiện qua các thành phần UI sau và cần được bỏ:

- Radio `recommendation` trên form đánh giá
  - bỏ option `consider`
- Các màn hình đánh giá theo vòng `PV Vòng 1 -> PV Vòng 4`
  - chỉ còn hiển thị `pass/fail`
- Form chi tiết `hr.applicant.evaluation`
  - chỉ còn hiển thị `pass/fail`
- Tree evaluation
  - cột `Status` không còn khả năng xuất hiện `consider`
- Các note/cảnh báo/tổng hợp nếu đang ngầm hỗ trợ trạng thái “pending do consider”
  - cần rà lại để tránh thông điệp sai nghiệp vụ

## Kế hoạch triển khai

### Bước 1. Chỉnh model

File chính:

- `addons/M02_P0205/models/hr_applicant.py`

Việc cần làm:

- Sửa field `recommendation` bỏ lựa chọn `consider`
- Sửa `_recommendation_score()` chỉ còn xử lý `pass/fail`
- Sửa các hàm tổng hợp để không còn nhánh `consider`
- Sửa `_update_interview_round_outcome()`:
  - bỏ đoạn `if recommendation == 'consider': return`
  - bảo đảm chỉ còn 2 nhánh rõ ràng `pass/fail`

### Bước 2. Chỉnh view

File chính:

- `addons/M02_P0205/views/hr_applicant_views.xml`

Việc cần làm:

- Rà toàn bộ các field `recommendation` dùng `widget="radio"`
- Sau khi selection chỉ còn `pass/fail`, xác nhận UI không còn hiện `consider`
- Kiểm tra các tab `PV Vòng 1`, `PV Vòng 2`, `PV Vòng 3`, `PV Vòng 4`
- Kiểm tra form và tree của `hr.applicant.evaluation`

### Bước 3. Xử lý dữ liệu cũ

Vì database có thể đã tồn tại record `recommendation = 'consider'`, cần chốt cách migrate:

Phương án an toàn đề xuất:

- Không giữ `consider` trong code mới
- Tạo script/data migration để chuyển dữ liệu cũ:
  - hoặc map toàn bộ `consider` sang `fail`
  - hoặc map sang `pass`
  - hoặc clear về rỗng và yêu cầu người dùng đánh giá lại

Khuyến nghị:

- Không tự map `consider -> pass`
- Không tự map `consider -> fail`
- Nên đưa về trạng thái cần người dùng rà soát lại, vì `consider` là dữ liệu chưa kết luận

Nếu không làm migration, nguy cơ là:

- selection mới không còn chứa `consider`
- record cũ có thể gây lỗi hiển thị hoặc dữ liệu không nhất quán

### Bước 4. Rà lại logic chuyển bước sau mỗi vòng

Cần test lại các luồng:

- Pass vòng 1 => notify vòng 2
- Pass vòng 2 => notify vòng 3
- Pass vòng 3 => notify vòng 4
- Fail ở bất kỳ vòng nào => chuyển `Reject`
- Sau khi bỏ `consider`, không còn trường hợp hồ sơ đứng giữa flow chỉ vì chọn trạng thái trung gian

## Điểm cần chốt trước khi code

Có 1 quyết định nghiệp vụ quan trọng:

- Dữ liệu cũ đang là `consider` sẽ được xử lý thế nào

Nếu chưa chốt được migration, nên vẫn làm theo thứ tự:

1. Bỏ `consider` ở UI để chặn phát sinh mới
2. Chạy rà dữ liệu cũ
3. Chốt quy tắc migrate
4. Mới khóa hẳn logic ở model nếu cần

## Test scenario tối thiểu

- Tạo mới evaluation vòng bất kỳ, xác nhận chỉ còn `pass/fail`
- Chọn `pass`, xác nhận flow đi tiếp đúng
- Chọn `fail`, xác nhận applicant sang `Reject`
- Mở tree/form evaluation, xác nhận không còn thấy `consider`
- Kiểm tra applicant cũ từng có `consider` để xem có lỗi hiển thị hay không

## Kết luận

Việc bỏ `consider` là thay đổi đúng hướng nếu nghiệp vụ chỉ muốn một kết luận dứt khoát sau mỗi vòng.

Tuy nhiên phần cần cẩn thận nhất không phải UI, mà là:

- logic tổng hợp đang còn vết `consider`
- dữ liệu cũ trong database
- thông điệp/cảnh báo đang dựa trên trạng thái chưa kết luận
