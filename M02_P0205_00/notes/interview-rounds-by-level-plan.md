# Plan tùy chỉnh số lượng vòng phỏng vấn theo `level_id` của module `M02_P0200_00`

## Mục tiêu

Điều chỉnh flow phỏng vấn của module `M02_P0205_00` để số lượng vòng phỏng vấn không còn cố định cho mọi vị trí, mà được quyết định theo `level_id` của `hr.job` đang có trong module `M02_P0200_00`.

Mục tiêu nghiệp vụ:

- Job level thấp hơn có thể đi ít vòng hơn
- Job level cao hơn có thể đi nhiều vòng hơn
- Flow tuyển dụng của `0205` vẫn giữ được ổn định
- Tận dụng cấu hình level hiện đã có trên UI của `0200`

## Hiện trạng mới trong `0200`

Sau khi rà lại module `M02_P0200_00` bản mới:

### 1. Level đã là model riêng

File:

- `addons/M02_P0200_00/models/hr_job_level.py`

Model:

- `hr.job.level`

Các field hiện có:

- `name`
- `code`
- `sequence`
- `active`

Kết luận:

- level không còn là selection hard-code nữa
- level đã trở thành master data riêng, có thể mở rộng linh hoạt

### 2. `hr.job` dùng `level_id`

File:

- `addons/M02_P0200_00/models/hr_job_ext.py`

Field:

- `level_id = fields.Many2one('hr.job.level', string='Level')`

Kết luận:

- `0205` về sau phải dùng `job.level_id`
- không còn dùng `job.level`

### 3. `hr.job.position.default` cũng dùng `level_id`

File:

- `addons/M02_P0200_00/models/hr_job_position_default.py`

Field:

- `level_id = fields.Many2one('hr.job.level', string='Level')`

Ý nghĩa:

- level có thể được gắn ngay từ master data vị trí mặc định

### 4. Có UI cấu hình level

File:

- `addons/M02_P0200_00/views/hr_job_level_views.xml`

Hiện đã có:

- tree view
- form view
- action
- menu `Job Levels`

Ngoài ra level còn xuất hiện trên UI tại:

- `addons/M02_P0200_00/views/hr_job_views.xml`
  - gắn `level_id` trực tiếp trên form/tree của `hr.job`
- `addons/M02_P0200_00/views/hr_job_position_default_views.xml`
  - gắn `level_id` trên default positions
  - có group by theo `level_id`

Kết luận:

- business đã có nơi cấu hình level trên UI
- không cần tạo thêm cấu hình level mới trong `0205`

### 5. Dữ liệu level seed sẵn

File:

- `addons/M02_P0200_00/data/hr_job_level_data.xml`

Các level hiện có gồm:

- `employee`
- `assistant`
- `coordinator`
- `specialist`
- `consultant`
- `manager`
- `head_of_department`

Kết luận:

- không còn chỉ có 2 level như assumption cũ
- mapping số vòng phỏng vấn cần hỗ trợ nhiều level hơn

## Hiện trạng trong `0205`

Module `M02_P0205_00` hiện vẫn đang xây theo khung 4 vòng cứng:

- `Interview 1`
- `Interview 2`
- `Interview 3`
- `Interview 4`

Các chỗ hard-code chính:

- `addons/M02_P0205_00/models/interview_round.py`
  - `INTERVIEW_ROUND_SELECTION`
  - `INTERVIEW_STAGE_XML_TO_ROUND`
- `addons/M02_P0205_00/models/hr_applicant.py`
  - `interview_date_1..4`
  - `eval_l1_id..4`
  - `primary_interviewer_l1_user_id..4`
  - metrics và toggle vòng 1..4
  - action invite và action evaluation riêng cho từng vòng
  - logic notify vòng sau đang gắn cứng:
    - vòng 1 -> CEO
    - vòng 2 -> BOD
    - vòng 3 -> ABU
    - vòng 4 -> Offer
- `addons/M02_P0205_00/views/hr_applicant_views.xml`
  - tab riêng cho từng vòng
  - button riêng cho từng vòng

Kết luận:

- `0205` hiện không phải dạng “n vòng động hoàn toàn”
- số vòng đang được encode sâu ở model, view, stage, activity và mail

## Nhận định kiến trúc phù hợp

Với trạng thái hiện tại của hai module, hướng phù hợp nhất là:

- **không refactor toàn bộ sang mô hình số vòng động hoàn toàn**
- **giữ nguyên khung 4 vòng đang có**
- **thêm lớp điều khiển số vòng hiệu lực theo `job.level_id`**

Đây là hướng an toàn hơn vì:

- ít đụng đến cấu trúc dữ liệu cũ
- ít phải thay đổi hàng loạt ở view/mail/activity
- tận dụng được UI level đã có sẵn trong `0200`
- vẫn đạt mục tiêu nghiệp vụ “level khác nhau thì số vòng khác nhau”

## Đề xuất thiết kế

### 1. Tạo mapping `level_id -> max_interview_round`

Tại `0205` nên có helper để xác định:

- applicant này tối đa cần đi đến vòng mấy

Nguồn tính:

- `applicant.job_id.level_id`

### 2. Không hard-code theo `name`

Vì `hr.job.level` là master data cấu hình được trên UI, không nên phụ thuộc trực tiếp vào label hiển thị.

Khuyến nghị đã chốt:

- map theo `level_id.code`
- không sửa `0200` ở giai đoạn hiện tại

Mapping level -> số vòng đã được business chốt:

- `employee` -> `2`
- `assistant` -> `2`
- `coordinator` -> `2`
- `specialist` -> `3`
- `consultant` -> `3`
- `manager` -> `4`
- `head_of_department` -> `4`

Lưu ý:

- giai đoạn đầu không cần fallback theo `name`
- dữ liệu cần đảm bảo `level_id.code` được nhập đúng trong `0200`

### 3. Không đổi cấu trúc 4 vòng hiện có

Tạm thời vẫn giữ:

- `interview_date_1..4`
- `eval_l1_id..4`
- `primary_interviewer_l1_user_id..4`
- các field metrics 1..4

Nhưng:

- chỉ dùng các vòng đến `max_interview_round`
- các vòng lớn hơn sẽ bị ẩn và không được kích hoạt flow

## Đề xuất cấu trúc triển khai

### Phase 1. Đồng bộ dependency và helper level

File liên quan:

- `addons/M02_P0205_00/__manifest__.py`
- `addons/M02_P0205_00/models/hr_applicant.py`

Việc cần làm:

- thêm dependency `M02_P0200_00` vào `0205`
- thêm helper hoặc field compute:
  - `max_interview_round`
  - hoặc helper `_get_max_interview_round_from_job_level()`

Khuyến nghị:

- chỉ cần `max_interview_round` là đủ
- các flag `is_round_X_enabled` có thể derive từ field này

### Phase 2. Chặn flow model theo `max_interview_round`

File chính:

- `addons/M02_P0205_00/models/hr_applicant.py`

Việc cần làm:

- sửa `_compute_next_interview_round()`
  - không mở vòng vượt quá `max_interview_round`
- sửa `_ensure_previous_round_completed()`
  - chỉ kiểm tra các vòng còn hiệu lực
- sửa `_update_interview_round_outcome()`
  - nếu applicant pass ở vòng cuối theo level thì handoff sang `Offer`
  - không notify vòng kế nếu level không cần vòng đó
- sửa `action_ready_for_offer()`
  - không hard-code chỉ đi sau vòng 4
  - thay bằng “đã pass vòng cuối theo level”

Đây là trọng tâm chính của toàn bộ thay đổi.

### Phase 3. Điều chỉnh UI theo `max_interview_round`

File chính:

- `addons/M02_P0205_00/views/hr_applicant_views.xml`

Việc cần làm:

- ẩn tab các vòng vượt quá `max_interview_round`
- ẩn button invite/evaluation của các vòng dư
- ở tab tổng hợp evaluation chỉ hiển thị các vòng còn hiệu lực

Khuyến nghị:

- giữ nguyên layout hiện có
- chỉ thêm điều kiện `invisible`

### Phase 4. Điều chỉnh activity / notification / mail

File liên quan:

- `addons/M02_P0205_00/models/hr_applicant.py`
- `addons/M02_P0205_00/data/mail_template_data.xml`

Việc cần làm:

- activity mở vòng sau chỉ tạo khi vòng sau còn hiệu lực
- notification email vòng 3/4 không được gửi cho applicant level không cần các vòng đó
- activity handoff sang Offer phải chạy ở vòng cuối theo level, không phụ thuộc cứng vào vòng 4

Ví dụ:

- level `employee`
  - pass vòng 2 -> tạo activity `Chuẩn bị Offer`
  - không tạo activity cho BOD/ABU
- level `specialist`
  - pass vòng 3 -> sang `Offer`
- level `manager`
  - vẫn full 4 vòng

### Phase 5. Stage / round mapping

File liên quan:

- `addons/M02_P0205_00/models/interview_round.py`
- `addons/M02_P0205_00/models/hr_applicant.py`

Hướng xử lý:

- không xóa stage cũ
- vẫn giữ `Interview 1 -> Interview 4`
- applicant nào có `max_interview_round < 4` thì không đi vào stage dư

Ví dụ:

- level `assistant`
  - pass vòng 2 -> đi thẳng sang Offer
- level `consultant`
  - pass vòng 3 -> đi thẳng sang Offer

### Phase 6. Test scenario

Nên test theo ít nhất 4 nhóm level:

- `employee`
- `specialist`
- `manager`
- `head_of_department`

Case tối thiểu:

- `employee`
  - chỉ đi 2 vòng
- `specialist`
  - đi 3 vòng
- `manager`
  - đi đủ 4 vòng
- `head_of_department`
  - đi đủ 4 vòng

Ngoài ra cần test:

- job không có `level_id`
- `level_id` bị inactive
- `level_id.code` rỗng nhưng `name` có dữ liệu

## Các điểm cần chốt với business trước khi code

### 1. Mapping level -> số vòng

Đã chốt như sau:

- `employee` -> `2`
- `assistant` -> `2`
- `coordinator` -> `2`
- `specialist` -> `3`
- `consultant` -> `3`
- `manager` -> `4`
- `head_of_department` -> `4`

### 2. Có cần cấu hình mềm số vòng ngay trên UI không

Đã chốt:

- chưa cần cấu hình mềm trên UI
- dùng `level_id.code` để map số vòng ngay trong `0205`
- không sửa `0200`
- ưu tiên hoàn tất flow end-to-end trước

## Khuyến nghị triển khai thực tế

### Giai đoạn 1

- dùng `level_id.code` để map số vòng trong `0205`
- không sửa `0200`
- hoàn tất flow end-to-end trước

### Giai đoạn 2

- chỉ xem xét sau nếu business đổi yêu cầu
- khi đó mới cân nhắc thêm field cấu hình số vòng ở `0200`

## Kết luận

Với cấu trúc mới của `0200` và chốt hiện tại từ business, hướng triển khai là:

- `0205` đọc `job.level_id`
- map `level_id.code` ra `max_interview_round` theo bảng đã chốt
- giữ nguyên khung 4 vòng hiện có của `0205`
- chỉ giới hạn số vòng hiệu lực theo level
- không sửa `0200` trong giai đoạn hiện tại

Điểm quan trọng nhất của bản cập nhật note này là:

- không còn assumption cũ `job.level = manager/employee`
- thay bằng mô hình đúng với code mới:
  - `job.level_id -> hr.job.level`
  - level được cấu hình trên UI của `0200`
  - số vòng được map cứng trong `0205` theo `level_id.code`
