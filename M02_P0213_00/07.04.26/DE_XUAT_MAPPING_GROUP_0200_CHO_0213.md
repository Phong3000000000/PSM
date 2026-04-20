# Đề xuất mapping group `0200` cho module `0213`

**Ngày cập nhật**: 2026-04-07  
**Mục tiêu**: Đề xuất cách dùng lại các group đã có của `M02_P0200_00` để phân quyền cho `M02_P0213_00`, thay vì tạo group mới riêng cho `0213`.

---

## 1. Kết luận nhanh

- Có thể dùng lại group của `0200` cho `0213`
- Đây là hướng **hợp lý hơn tạo group mới** nếu mục tiêu là đồng bộ phân quyền theo cơ cấu tổ chức chung
- Tuy nhiên, cần:
  - map đúng vai trò nghiệp vụ
  - giới hạn quyền bằng ACL + record rule + visibility
  - giữ riêng `base.group_portal` cho người dùng portal

---

## 2. Nhóm group hiện có trong `0200`

Dựa trên [security.xml](/d:/odoo-19.0+e.20250918/addons/M02_P0200_00/security/security.xml), các group đáng chú ý gồm:

### Nhóm nền tảng hệ thống
- `GDH_RST_ALL_BASE_S`
- `GDH_RST_SYSTEM_ST_M`

### Nhóm HR
- `GDH_RST_HR_RECRUITMENT_S`
- `GDH_RST_HR_RECRUITMENT_M`
- `GDH_RST_HR_CNB_S`
- `GDH_RST_HR_CNB_M`
- `GDH_RST_HR_HRBP_S`
- `GDH_RST_HR_HRBP_M`
- `GDH_RST_HR_ADMIN_S`
- `GDH_RST_HR_ADMIN_M`
- `GDH_RST_HR_HEAD_M`

### Nhóm OPS / Cửa hàng
- `GDH_OPS_STORE_CREW_S`
- `GDH_OPS_STORE_TRAINER_S`
- `GDH_OPS_STORE_GEL_M`
- `GDH_OPS_STORE_SM_M`
- `GDH_OPS_STORE_ST_M`
- `GDH_OPS_STORE_PM_M`
- `GDH_OPS_STORE_RGM_M`

### Nhóm OPS cấp vùng / điều hành
- `GDH_RST_OPS_OC_S`
- `GDH_RST_OPS_OM_M`

---

## 3. Đề xuất nguyên tắc áp dụng cho `0213`

### Nên dùng lại group `0200` cho user nội bộ

Lý do:
- Đồng bộ role toàn hệ thống
- Tránh tạo thêm group trùng nghĩa
- Dễ quản trị user và audit quyền

### Không dùng group `0200` để thay portal

Portal trong `0213` vẫn nên dùng:
- `base.group_portal`

Lý do:
- Portal là kiểu truy cập riêng
- Không nên gộp user portal vào các group tổ chức nội bộ

### Phân quyền nên theo 3 lớp

1. ACL  
- Quy định quyền đọc/ghi/tạo/xóa ở mức model

2. Record Rule  
- Giới hạn user chỉ thấy đúng hồ sơ thuộc phạm vi của mình

3. View/Button Visibility  
- Ẩn/hiện nút thao tác theo group nghiệp vụ

---

## 4. Mapping đề xuất cho `0213`

| Vai trò trong `0213` | Group đề xuất từ `0200` | Phạm vi quyền đề xuất |
|---|---|---|
| Người dùng portal gửi đơn nghỉ việc | `base.group_portal` | Chỉ tạo/xem hồ sơ của chính mình qua portal |
| HR vận hành hồ sơ nghỉ việc | `GDH_RST_HR_ADMIN_S`, `GDH_RST_HR_HRBP_S` | Xem và xử lý hồ sơ nghỉ việc |
| HR quản lý / kiểm soát | `GDH_RST_HR_ADMIN_M`, `GDH_RST_HR_HRBP_M`, `GDH_RST_HR_HEAD_M` | Duyệt, hoàn tất, theo dõi toàn bộ hồ sơ |
| OPS quản lý cửa hàng liên quan nghỉ việc | `GDH_OPS_STORE_PM_M`, `GDH_OPS_STORE_RGM_M` | Xem/duyệt hoặc phối hợp xử lý theo phạm vi cửa hàng |
| OPS điều hành vùng | `GDH_RST_OPS_OC_S`, `GDH_RST_OPS_OM_M` | Xem báo cáo hoặc theo dõi hồ sơ theo phạm vi nghiệp vụ |
| Quản trị hệ thống | `GDH_RST_SYSTEM_ST_M` | Full quyền kỹ thuật |

---

## 5. Đề xuất chi tiết theo loại quyền

### 5.1. `approval.request`

**Portal**
- Không cấp ACL rộng ở menu backend
- Chỉ đi qua controller/portal và record ownership

**HR nhóm xử lý**
- Nên cho:
  - read
  - write
- Tạo và xóa cần cân nhắc theo nghiệp vụ

**HR manager / HR head**
- Có thể cho full hơn:
  - read
  - write
  - create
  - unlink nếu thực sự cần

**OPS manager**
- Nên giới hạn hơn HR
- Có thể chỉ:
  - read
  - một phần write nếu cần phê duyệt/phối hợp

### 5.2. `mail.activity`

- Không nên mở quá rộng cho tất cả group nội bộ
- Nên ưu tiên:
  - user được giao activity thì xử lý phần của mình
  - HR/manager có quyền đọc rộng hơn

### 5.3. `survey.user_input`

- Portal vẫn giữ rule “chỉ thấy khảo sát của chính mình”
- HR có thể cần quyền đọc kết quả khảo sát
- Không nên cho OPS xem toàn bộ nếu không có nhu cầu nghiệp vụ rõ

### 5.4. `approval.category`

- Chỉ nên để nhóm quản trị hoặc HR manager chỉnh sửa
- Không nên mở cho user nội bộ phổ thông

---

## 6. Mapping tối thiểu nên triển khai trước

Nếu muốn làm gọn, nên ưu tiên áp dụng trước 4 nhóm sau:

| Mục tiêu | Group |
|---|---|
| Portal | `base.group_portal` |
| HR xử lý | `GDH_RST_HR_ADMIN_S`, `GDH_RST_HR_HRBP_S` |
| HR quản lý | `GDH_RST_HR_ADMIN_M`, `GDH_RST_HR_HRBP_M`, `GDH_RST_HR_HEAD_M` |
| System | `GDH_RST_SYSTEM_ST_M` |

Nhóm OPS có thể bổ sung sau nếu BA xác nhận họ thực sự cần tham gia trực tiếp ở backend.

---

## 7. Các điểm cần chốt trước khi code

Trước khi áp vào ACL/rule thật, cần chốt:

1. Ai là người được phép xem toàn bộ đơn nghỉ việc?
- Chỉ HR
- Hay cả OPS manager

2. Ai được phép bấm các action nhạy cảm?
- `action_done`
- `action_send_social_insurance`
- `action_send_adecco_notification`
- `action_blacklist`
- `action_rehire`

3. OPS có cần chỉ xem hồ sơ thuộc cửa hàng/phạm vi mình quản lý không?
- Nếu có, cần thêm record rule theo tổ chức/phòng ban/cửa hàng

4. `approval.category` có cần để HR manager cấu hình không?
- Nếu không, nên khóa về system/admin

---

## 8. Khuyến nghị triển khai

### Giai đoạn 1
- Dùng lại group `0200`
- Chưa tạo group mới của `0213`
- Siết ACL rõ hơn cho:
  - `approval.request`
  - `approval.category`
  - `mail.activity`
  - `survey.user_input`

### Giai đoạn 2
- Gắn `groups` cho button/view trong `resignation_request_views.xml`
- Giữ portal riêng với `base.group_portal`

### Giai đoạn 3
- Nếu BA cần phân quyền tinh hơn theo phạm vi cửa hàng hoặc tuyến quản lý:
  - bổ sung record rule theo tổ chức

---

## 9. Kết luận cuối

`0213` hoàn toàn có thể dùng lại group của `0200` để phân quyền nội bộ, và đây là hướng nên làm trong bối cảnh hiện tại.

Hướng này phù hợp vì:
- không đổi kiến trúc module
- không tạo thêm role trùng nghĩa
- đồng bộ với mô hình tổ chức đã có

Điểm cần giữ riêng:
- `base.group_portal` cho portal

Điểm cần làm cẩn thận:
- ACL
- record rule
- visibility của button/action
