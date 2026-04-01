# Stage Offer trong module `M02_P0205_00`

## File định nghĩa Stage Offer

Stage `Offer` được khai báo trong file `addons/M02_P0205_00/data/office_stages.xml`.

Record tương ứng là:

```xml
<record id="stage_office_proposal" model="hr.recruitment.stage">
```

Thông tin chính của stage này:

- `name`: `Offer`
- `sequence`: `60`
- `recruitment_type`: `office`
- `external id`: `stage_office_proposal`

Nếu cần chỉnh sửa tên stage, thứ tự hiển thị hoặc các thuộc tính liên quan, cần thao tác tại file XML này hoặc tham chiếu đến record có `external id` ở trên.

## File xử lý logic khi chuyển stage

Hành vi kiểu “khi đến một stage thì thực hiện một hành động nào đó” trong module `0205` chủ yếu được xử lý tại file `addons/M02_P0205_00/models/hr_applicant.py`.

Điểm quan trọng:

- File này có override hàm `write` để bắt sự thay đổi của `stage_id`.
- Khi hồ sơ được chuyển sang stage có `hired_stage = True`, hệ thống sẽ tự động `message_post` để thông báo chúc mừng và báo rằng quy trình Onboarding đã bắt đầu.
- Ngoài ra, các method như `action_ready_for_offer`, `action_send_offer`, `action_confirm_signed`... cũng là nơi đổi `stage_id` và kích hoạt thêm các hành động như gửi mail hoặc hiển thị thông báo.

Có thể xem đây là file trung tâm để kiểm tra logic “đến stage nào thì làm gì”.

## Thao tác của người dùng tại stage Offer

Khi ứng viên đang ở stage `Offer` (`stage_office_proposal`), giao diện form trong file `addons/M02_P0205_00/views/hr_applicant_views.xml` hiển thị hai nút chính:

- `Gửi Offer` gọi hàm `action_send_offer`
- `Xác nhận đã Ký` gọi hàm `action_confirm_signed`

### `action_send_offer`

- Kiểm tra xem đã có giá trị `Lương đề nghị` (`salary_proposed`) hay chưa.
- Nếu đã có, hệ thống gửi email Offer Letter cho ứng viên.
- Sau đó cập nhật `offer_status = 'proposed'`.

### `action_confirm_signed`

- Đây là thao tác để chuyển hồ sơ từ stage `Offer` sang thẳng stage `Hired` (`stage_office_hired`).
- Đồng thời hệ thống cập nhật `offer_status = 'accepted'`.
- Sau đó hiển thị thông báo xác nhận ứng viên đã nhận offer.

## Kết luận

Tại stage `Offer`, người dùng có thao tác rõ ràng để đưa hồ sơ sang bước tiếp theo.

Luồng chính là:

1. Bấm `Gửi Offer` để gửi thư mời nhận việc.
2. Khi ứng viên đã ký/đồng ý, bấm `Xác nhận đã Ký` để chuyển thẳng sang stage `Hired`.

Phần logic chi tiết nằm chủ yếu trong file `addons/M02_P0205_00/models/hr_applicant.py`, còn phần hiển thị nút thao tác nằm trong `addons/M02_P0205_00/views/hr_applicant_views.xml`.
