# Phase triển khai code cho plan `interview rounds by level`

## Mục tiêu

Tài liệu này tách plan `interview rounds by level` thành các phase triển khai code cụ thể trong `M02_P0205_00`, để có thể thực hiện lần lượt và kiểm soát rủi ro tốt hơn.

Plan gốc tham chiếu:

- `addons/M02_P0205_00/notes/interview-rounds-by-level-plan.md`

Chốt nghiệp vụ hiện tại:

- dùng `job.level_id.code` để map số vòng trong `0205`
- không sửa `0200`
- mapping số vòng như sau:
  - `employee` -> `2`
  - `assistant` -> `2`
  - `coordinator` -> `2`
  - `specialist` -> `3`
  - `consultant` -> `3`
  - `manager` -> `4`
  - `head_of_department` -> `4`

## Nguyên tắc triển khai

- không refactor `0205` thành mô hình “n vòng động hoàn toàn”
- giữ nguyên khung 4 vòng hiện có
- thêm lớp điều khiển `max_interview_round`
- triển khai từ model trước, rồi mới đến UI, activity, mail và test

## Phase 1. Thêm dependency và helper đọc level

### Mục tiêu

Chuẩn bị nền tảng để `0205` có thể đọc `job.level_id` một cách chính thức và ổn định.

### File chính

- `addons/M02_P0205_00/__manifest__.py`
- `addons/M02_P0205_00/models/hr_applicant.py`

### Việc cần làm

- thêm dependency `M02_P0200_00` vào `0205`
- thêm helper lấy `level_id.code` từ `applicant.job_id`
- thêm helper map `level_id.code -> max_interview_round`

### Kết quả mong muốn

- mỗi applicant có thể xác định được số vòng tối đa cần đi
- nếu không có `job_id` hoặc `level_id`, phải có fallback an toàn

### Gợi ý kỹ thuật

- tạo helper:
  - `_get_job_level_code()`
  - `_get_max_interview_round()`
- fallback đề xuất:
  - nếu không có level -> trả `4`

## Phase 2. Điều chỉnh flow model theo `max_interview_round`

### Mục tiêu

Làm cho core flow nghiệp vụ của applicant dừng đúng ở vòng cuối theo level, thay vì luôn đi theo 4 vòng cố định.

### File chính

- `addons/M02_P0205_00/models/hr_applicant.py`
- `addons/M02_P0205_00/models/interview_round.py`

### Việc cần làm

#### 1. Sửa xác định vòng tiếp theo

- cập nhật `_compute_next_interview_round()`
- không cho mở vòng vượt quá `max_interview_round`

#### 2. Sửa điều kiện qua vòng

- cập nhật `_ensure_previous_round_completed()`
- cập nhật `_ensure_round_passed()`
- chỉ kiểm tra các vòng còn hiệu lực

#### 3. Sửa logic pass/fail theo vòng cuối động

- cập nhật `_update_interview_round_outcome()`
- nếu pass ở vòng cuối theo level:
  - không notify vòng tiếp theo
  - chuyển sang handoff `Offer`

#### 4. Sửa logic sang Offer

- cập nhật `action_ready_for_offer()`
- thay vì hard-code phải pass vòng 4, đổi thành:
  - pass vòng cuối theo level là được

### Kết quả mong muốn

- applicant `employee/assistant/coordinator` dừng ở vòng 2
- applicant `specialist/consultant` dừng ở vòng 3
- applicant `manager/head_of_department` đi đủ 4 vòng

## Phase 3. Điều chỉnh UI theo số vòng hiệu lực

### Mục tiêu

Ẩn các vòng không dùng để người dùng không thao tác nhầm.

### File chính

- `addons/M02_P0205_00/views/hr_applicant_views.xml`

### Việc cần làm

#### 1. Ẩn tab vòng dư

- tab `PV Vòng 3` và `PV Vòng 4` phải ẩn với level chỉ cần 2 vòng
- tab `PV Vòng 4` phải ẩn với level chỉ cần 3 vòng

#### 2. Ẩn button vòng dư

- `Mời PV L3`
- `Mời PV L4`
- `Thêm đánh giá Vòng 3`
- `Thêm đánh giá Vòng 4`

#### 3. Điều chỉnh tab tổng hợp evaluation

- chỉ nên hiển thị các group vòng đang còn hiệu lực

### Kết quả mong muốn

- UI applicant nhìn đúng số vòng thực sự cần dùng
- user không thấy vòng thừa

### Gợi ý kỹ thuật

- thêm các field boolean compute để dùng cho `invisible`, ví dụ:
  - `show_interview_round_3`
  - `show_interview_round_4`
- hoặc derive trực tiếp từ `max_interview_round`

## Phase 4. Điều chỉnh activity và notification theo vòng cuối động

### Mục tiêu

Đảm bảo activity và handoff bám đúng vòng cuối theo level.

### File chính

- `addons/M02_P0205_00/models/hr_applicant.py`

### Việc cần làm

#### 1. Activity mở vòng sau

- chỉ tạo activity mở vòng sau nếu vòng sau còn hiệu lực

Ví dụ:

- `employee`
  - pass vòng 2 -> không tạo activity cho BOD
- `specialist`
  - pass vòng 3 -> không tạo activity cho ABU

#### 2. Activity handoff sang Offer

- `Chuẩn bị Offer` phải kích hoạt ở vòng cuối theo level
- không phụ thuộc cứng vào vòng 4

#### 3. Offer follow-up

- giữ logic offer follow-up hiện có
- kiểm tra nó vẫn chạy đúng với applicant kết thúc sớm ở vòng 2 hoặc 3

### Kết quả mong muốn

- không còn activity sai vòng
- handoff sang Offer đúng thời điểm

## Phase 5. Điều chỉnh mail notification theo vòng hiệu lực

### Mục tiêu

Không gửi mail cho những vòng applicant không cần đi.

### File chính

- `addons/M02_P0205_00/models/hr_applicant.py`
- `addons/M02_P0205_00/data/mail_template_data.xml`

### Việc cần làm

- rà `action_send_interview_round2_notification()`
- rà `action_send_interview_round3_notification()`
- rà `action_send_interview_round4_notification()`
- chặn gửi mail nếu vòng đó vượt quá `max_interview_round`

### Kết quả mong muốn

- employee không có mail vòng 3, 4
- specialist/consultant không có mail vòng 4

## Phase 6. Test scenario end-to-end

### Mục tiêu

Xác nhận flow chạy trọn vẹn cho từng nhóm level.

### Nhóm test bắt buộc

- `employee`
- `assistant`
- `coordinator`
- `specialist`
- `consultant`
- `manager`
- `head_of_department`

### Case cần test

#### Nhóm 2 vòng

- pass vòng 1 -> mở vòng 2
- pass vòng 2 -> sang Offer
- không hiện / không đi vào vòng 3, 4

#### Nhóm 3 vòng

- pass vòng 1 -> mở vòng 2
- pass vòng 2 -> mở vòng 3
- pass vòng 3 -> sang Offer
- không hiện / không đi vào vòng 4

#### Nhóm 4 vòng

- giữ nguyên full flow hiện có

### Case biên

- job không có `level_id`
- `level_id.code` rỗng
- level không nằm trong bảng mapping

### Kỳ vọng fallback

- fallback về `4` vòng để không làm vỡ flow hiện tại

## Thứ tự triển khai khuyến nghị

Để an toàn và dễ rollback, nên làm theo 3 đợt:

### Đợt 1

- Phase 1
- Phase 2

Đây là đợt quan trọng nhất vì chạm vào core logic.

### Đợt 2

- Phase 3
- Phase 4

Đây là đợt đồng bộ UI và activity với flow mới.

### Đợt 3

- Phase 5
- Phase 6

Đây là đợt hoàn thiện notification và kiểm thử tổng thể.

## Kết luận

Tài liệu này dùng để biến plan tổng quan thành lộ trình code có thể thực hiện ngay.

Hướng triển khai thực tế nên là:

- thêm helper `max_interview_round`
- sửa core flow trước
- sau đó mới đồng bộ UI, activity, mail
- cuối cùng test lại end-to-end theo từng nhóm `level_id.code`
