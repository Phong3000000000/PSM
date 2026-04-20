# Kết quả fix theo review `M02_P0213_00`

**Ngày cập nhật**: 2026-04-07
**Phạm vi**: Đối chiếu và fix theo:
- `code_review_M02_P0213_00.md`
- `plan_fix_M02_P0213_00.md`

## Các mục đã xử lý trong code

### 1. CRITICAL-01 - Bỏ raw SQL trong compute field
- Đã bỏ `self.env.cr.execute(...)` trong logic tính `x_psm_0213_employee_activity_ids`.
- Đã chuyển sang ORM `search(...)` với `with_context(active_test=False)`.
- File áp dụng: `models/resignation_request.py`

### 2. CRITICAL-02 - Bỏ so sánh category bằng tên hiển thị
- Đã thêm helper `_get_resignation_category()`.
- `action_withdraw()` và `action_cancel()` đã dùng so sánh record theo XML ID thay cho `category_id.name`.
- File áp dụng: `models/resignation_request.py`

### 3. WARNING-01 - Xóa duplicate `ensure_one()`
- Đã bỏ lời gọi `ensure_one()` dư trong `action_launch_plan()`.
- File áp dụng: `models/resignation_request.py`

### 4. WARNING-02 - Bỏ `hasattr()` thừa
- Đã bỏ `hasattr()` trên các field chuẩn liên quan đến hợp đồng trong `_compute_type_contract()`.
- File áp dụng: `models/resignation_request.py`

### 5. WARNING-03 - Giảm N+1 ở cron reminder
- Đã thêm helper `_get_overdue_activities_by_request()` để gom activity overdue một lần cho toàn bộ request.
- Đã thêm helper `_group_activities_by_user()` để gom activity theo user, tránh `filtered()` lặp trong vòng lặp nhắc việc.
- Đã áp dụng cho:
  - `_cron_send_offboarding_reminders()`
  - `action_manual_reminder_extension()`
- File áp dụng: `models/resignation_request.py`

### 6. WARNING-04 - Hạ log debug
- Đã đổi `_logger.info(...)` sang `_logger.debug(...)` ở phần owner-related activities.
- File áp dụng: `models/resignation_request.py`

## Kết quả kiểm tra nhanh

- Không còn `env.cr.execute` trong `models/resignation_request.py`.
- Không còn `category_id.name == "Yêu cầu nghỉ việc "` trong `models/resignation_request.py`.
- Không còn `hasattr(...)` trong `models/resignation_request.py`.
- `py_compile` pass cho `models/resignation_request.py`.

## Lưu ý còn lại

- Một số chuỗi tiếng Việt trong file Python vẫn đang bị lỗi mã hóa hiển thị, nhưng không ảnh hưởng đến logic fix của đợt này.
- Cron đã giảm N+1 đáng kể; nếu cần tối ưu sâu hơn nữa, có thể tiếp tục gom email hoặc write deadline theo batch lớn hơn.
