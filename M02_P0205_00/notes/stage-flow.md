# Trình tự Stage trong module `M02_P0205_00`

## Tổng quan

Module `0205` không chỉ có một luồng đi cố định từ `New` đến `Hired`, mà còn có các nhánh rẽ tùy theo kết quả khảo sát, phỏng vấn và offer.

Chuỗi stage chính của quy trình tuyển dụng khối văn phòng:

`New` -> `Screening` -> `Interview 1` -> `Interview 2` -> `Interview 3` -> `Interview 4` -> `Offer` -> `Hired`

Nhánh loại:

`Reject`

## Danh sách stage

### 1. `New`

- File định nghĩa: `addons/M02_P0205_00/data/office_stages.xml`
- External id: `stage_office_new`
- Vai trò:
  - Là điểm khởi đầu cho hồ sơ mới tạo hoặc mới tiếp nhận.
  - Được map về `round 1` trong `addons/M02_P0205_00/models/interview_round.py`.

### 2. `Screening`

- External id: `stage_office_screening`
- Vai trò:
  - Dùng sau khi ứng viên đạt bài khảo sát pre-interview.
  - Là bước để sàng lọc hồ sơ và chuẩn bị cho phỏng vấn vòng 1.
- Logic liên quan:
  - `addons/M02_P0205_00/models/survey_ext.py` sẽ chuyển hồ sơ sang stage này nếu kết quả khảo sát đạt.

### 3. `Interview 1`

- External id: `stage_office_interview_1`
- Vai trò:
  - Là vòng phỏng vấn 1, thường gắn với `Manager`.
- Logic liên quan:
  - Nút `Mời PV L1` trong `addons/M02_P0205_00/views/hr_applicant_views.xml`
  - Hàm `action_invite_interview_l1()` trong `addons/M02_P0205_00/models/hr_applicant.py`

### 4. `Interview 2`

- External id: `stage_office_interview_2`
- Vai trò:
  - Là vòng phỏng vấn 2, thường gắn với `CEO`.
- Logic liên quan:
  - Nút `Mời PV L2`
  - Hàm `action_invite_interview_l2()`

### 5. `Interview 3`

- External id: `stage_office_interview_3`
- Vai trò:
  - Là vòng phỏng vấn 3, thường gắn với `BOD`.
- Logic liên quan:
  - Nút `Mời PV L3`
  - Hàm `action_invite_interview_l3()`

### 6. `Interview 4`

- External id: `stage_office_interview_4`
- Vai trò:
  - Là vòng phỏng vấn 4, thường gắn với `ABU`.
- Logic liên quan:
  - Nút `Mời PV L4`
  - Hàm `action_invite_interview_l4()`
  - Nút `Sẵn sàng Offer` sẽ chuyển hồ sơ sang stage `Offer`.

### 7. `Offer`

- External id: `stage_office_proposal`
- Vai trò:
  - Là giai đoạn đề xuất offer cho ứng viên.
- Hành động hiện có:
  - `Gửi Offer` gọi `action_send_offer()`
  - `Xác nhận đã Ký` gọi `action_confirm_signed()`
- Lưu ý:
  - `action_confirm_signed()` sẽ chuyển hồ sơ sang `Hired`.

### 8. `Hired`

- External id: `stage_office_hired`
- Vai trò:
  - Là giai đoạn đã tuyển xong.
  - Có `hired_stage = True` và `fold = True`.
- Logic liên quan:
  - Trong `write()` của `addons/M02_P0205_00/models/hr_applicant.py`, nếu stage mới có `hired_stage = True` thì hệ thống sẽ post thông báo onboarding.

### 9. `Reject`

- External id: `stage_office_reject`
- Vai trò:
  - Là nhánh loại hồ sơ khi ứng viên không đạt.
  - Có `fold = True`.
- Logic liên quan:
  - Khảo sát fail hoặc kết luận phỏng vấn không đạt có thể đẩy hồ sơ sang stage này trong `addons/M02_P0205_00/models/survey_ext.py` và `addons/M02_P0205_00/models/hr_applicant.py`.

## Luồng đi chính

### Nhánh đạt

1. `New`
2. `Screening`
3. `Interview 1`
4. `Interview 2`
5. `Interview 3`
6. `Interview 4`
7. `Offer`
8. `Hired`

### Nhánh loại

1. Bắt đầu từ `New` hoặc `Screening`
2. Khảo sát fail, phỏng vấn fail hoặc kết luận không đạt
3. Chuyển sang `Reject`

## File liên quan

- `addons/M02_P0205_00/data/office_stages.xml`
- `addons/M02_P0205_00/models/hr_applicant.py`
- `addons/M02_P0205_00/models/interview_round.py`
- `addons/M02_P0205_00/models/survey_ext.py`
- `addons/M02_P0205_00/views/hr_applicant_views.xml`
