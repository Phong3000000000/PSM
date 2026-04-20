# Hướng dẫn Sử Dụng Job Templates System

## Tổng quan

Hệ thống đã được thay đổi để sử dụng **hr.job templates** thay vì tạo mới mỗi khi portal user yêu cầu tuyển dụng.

## Thay đổi chính

### 1. Portal Recruitment - Mặc định chọn "Khối Cửa Hàng"

**File:** `views/portal_recruitment_templates.xml`

- Form tạo vị trí tuyển dụng mặc định chọn "Khối Cửa Hàng" (đã được check)
- Ẩn hoàn toàn tùy chọn "Khối Văn Phòng"

### 2. Tạo Job Templates cho từng Department × Position

**File mới:** `wizards/create_job_templates_wizard.py`

Tạo wizard để tạo hr.job templates cho tất cả combinations:
- **Store × Management**: Quản Lý Cửa Hàng, Quản Lý Khu Vực
- **Store × Staff**: Nhân Viên Phục Vụ, Nhân Viên Bếp, Nhân Viên Thu Ngân
- **Office × Management**: Quản Lý Cửa Hàng, Quản Lý Khu Vực
- **Office × Staff**: Nhân Viên Phục Vụ, Nhân Viên Bếp, Nhân Viên Thu Ngân

Mỗi template có:
- `no_of_recruitment = 0` (không tuyển)
- `user_id = False` (không gán user_id)
- `department_id` (phòng ban tương ứng)

**Cách sử dụng:**
1. Vào menu: Recruitment > Tạo Job Templates
2. Chọn Loại Tuyển Dụng và Cấp Bậc
3. Click "Tạo Templates" hoặc "Tạo Tất Cả Templates"

### 3. Portal Controller - Tìm và Cập nhật Template

**File:** `controllers/portal_recruitment.py`

**Logic mới:**
- Khi portal user tạo yêu cầu tuyển dụng:
  1. Tìm hr.job template đã tồn tại dựa trên:
     - `name` (tên vị trí)
     - `department_id` (phòng ban)
     - `recruitment_type` (khối tuyển dụng)
     - `position_level` (cấp bậc)
  
  2. Nếu tìm thấy template:
     - Cập nhật `no_of_recruitment` từ 0 → số lượng cần tuyển
     - Không tạo job.approval.request mới
  
  3. Nếu KHÔNG tìm thấy template:
     - Tạo hr.job mới (fallback)
     - Gán `no_of_recruitment` = số lượng cần tuyển
     - Gán `user_id = False`

**Hiển thị danh sách:**
- Portal hiển thị hr.job thay vì job.approval.request
- Lọc theo department của user
- Hiển thị trạng thái dựa trên `no_of_recruitment`:
  - `= 0`: "Không Tuyển" (badge xám)
  - `> 0`: "Đang Tuyển" (badge xanh)

### 4. HR Job Model - Hiển thị Tên Department

**File:** `models/hr_job.py`

Thêm computed field `display_name_with_dept`:
- Hiển thị: "Vị trí (Tên Phòng Ban)"
- Ví dụ: "Nhân Viên Phục Vụ (Cửa Hàng Hà Nội)"

## Workflow Mới

### Trước (Cũ):
```
Portal User → Tạo job.approval.request → Chờ Duyệt → Tạo hr.job mới → Ứng viên nộp đơn
```

### Sau (Mới):
```
1. Admin chạy Wizard "Tạo Job Templates" 
   → Tạo hr.job templates cho tất cả departments × positions

2. Portal User chọn vị trí từ template
   → Tìm hr.job template đã có
   → Cập nhật no_of_recruitment từ 0 → số lượng cần tuyển

3. Ứng viên nộp đơn cho hr.job đó
```

## Lợi ích

1. **Không tạo trùng lặp:** Mỗi department chỉ có 1 template cho mỗi position
2. **Quản lý dễ dàng:** Admin có thể xem tất cả templates và chỉnh sửa
3. **Phản hồi nhanh:** Portal user chỉ cần cập nhật số lượng cần tuyển
4. **Hiển thị rõ ràng:** Trạng thái dựa trên số lượng cần tuyển

## Cài đặt Module

### Tự động tạo Job Templates (Khuyên nghị)

Sau khi **upgrade module M02_P0204**, hệ thống sẽ **TỰ ĐỘNG** tạo hr.job templates cho:
- Tất cả departments hiện có trong hệ thống
- Tất cả combinations: Store × Management, Store × Staff, Office × Management, Office × Staff
- Mỗi template có `no_of_recruitment = 0` (không tuyển)

**Lưu ý:** Không cần chạy Wizard thủ công! Templates sẽ được tạo tự động khi upgrade module.

### Tạo thủ công (Nếu cần)

Nếu bạn muốn tạo lại templates hoặc thêm templates mới:

1. Vào menu: Recruitment > Tạo Job Templates
2. Chọn Loại Tuyển Dụng và Cấp Bậc
3. Click "Tạo Templates" hoặc "Tạo Tất Cả Templates"

### Sử dụng Portal

Sau khi templates đã được tạo:

1. **Portal users** có thể tạo yêu cầu tuyển dụng:
   - Vào Portal > Vị trí tuyển dụng
   - Chọn vị trí từ danh sách (đã lọc theo department)
   - Nhập số lượng cần tuyển
   - Click "Tạo vị trí"

2. **HR** có thể xem và quản lý job positions:
   - Vào: Recruitment > Khối Cửa Hàng / Khối Văn Phòng
   - Xem danh sách hr.job với trạng thái tuyển dụng

## Lưu ý quan trọng

- **Không sử dụng job.approval.request nữa:** Portal tạo trực tiếp vào hr.job
- **user_id luôn = False:** Để hiển thị tên department thay vì user
- **no_of_recruitment = 0 có nghĩa là không tuyển:** Badge hiển thị "Không Tuyển"
- **no_of_recruitment > 0 có nghĩa là đang tuyển:** Badge hiển thị "Đang Tuyển"

## File đã thay đổi

1. `views/portal_recruitment_templates.xml` - Form portal
2. `controllers/portal_recruitment.py` - Logic portal
3. `models/hr_job.py` - Thêm computed field
4. `wizards/create_job_templates_wizard.py` - Wizard tạo templates (MỚI)
5. `wizards/__init__.py` - Import wizard (MỚI)
6. `views/create_job_templates_wizard_views.xml` - View wizard (MỚI)
7. `__manifest__.py` - Thêm file wizard views (MỚI)
