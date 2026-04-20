# Quy Ước Đặt Tên Và Rule

Tài liệu này tổng hợp các quy ước cần lưu ý khi phát triển module.

## 1. Quy ước đặt tên

### 1.1. Manifest

- Cấu trúc tên module trong manifest:
  - `M02_P0101_<TÊN_QUY_TRÌNH_VIẾT_HOA>`
- Không cần thể hiện version trong tên module.

### 1.2. model gốc

- model gốc giữ nguyên tên.
- Không đổi tên model gốc.

### 1.3. model mới

- model mới đặt theo quy ước:
  - `x_psm_<tên_model>`

### 1.4. Field mới trong model gốc

- Field mới bổ sung vào model gốc đặt theo quy ước:
  - `x_psm_0101_tenfield`

### 1.5. Field mới trong model mới

- Field mới trong model mới đặt theo quy ước:
  - `x_psm_tenfield`

### 1.6. Action mới

- Action mới đặt theo quy ước:
  - `action_psm_tenaction`

### 1.7. View mới

- View mới đặt theo quy ước:
  - `view_psm_tenview`

### 1.8. Security

#### Văn phòng

- Nhóm 1:
  - `group_gdh_rst_module_stf`
- Nhóm 2:
  - `group_gdh_rst_module_mgr`

#### Nhà hàng

- Nhóm 1:
  - `group_gdh_ops_module_crw`
- Nhóm 2:
  - `group_gdh_ops_module_mgr`

### 1.9. Duyệt

- Sử dụng chung 1 module:
  - `approval`

### 1.10. Chấm điểm, khảo sát, phỏng vấn, câu hỏi

- Sử dụng chung 1 module:
  - `survey`

### 1.11. Ứng viên

- Sử dụng tên thống nhất:
  - `applicant`

### 1.12. Nhân viên

- Sử dụng tên thống nhất:
  - `employee`

## 2. Rule cần tuân thủ

### 2.1. Ưu tiên dùng cái sẵn có

- Cố gắng tận dụng tối đa model, field, action, view, module sẵn có của Odoo hoặc hệ thống hiện tại.
- Hạn chế tối đa việc tạo model mới nếu chưa thật sự cần thiết.

### 2.2. Phân quyền tối thiểu

- Chỉ cấp đúng mức quyền cần thiết để hoàn thành công việc.
- Không phân quyền tràn lan.
- Ưu tiên nguyên tắc minimum permission.

### 2.3. Tách bạch rõ ràng

- Ngăn nào ra ngăn nấy.
- Chức năng nào thuộc module nào thì để đúng module đó.
- Hạn chế viết logic lồng ghép, chồng chéo giữa các module.

## 3. Tóm tắt nhanh

- model gốc: giữ nguyên tên.
- model mới: `x_psm_<tên_model>`.
- Field mới model gốc: `x_psm_0101_tenfield`.
- Field mới model mới: `x_psm_tenfield`.
- Action mới: `action_psm_tenaction`.
- View mới: `view_psm_tenview`.
- Approval dùng chung module `approval`.
- Survey, chấm điểm, phỏng vấn, câu hỏi dùng chung module `survey`.
- Ứng viên dùng tên `applicant`.
- Nhân viên dùng tên `employee`.
- Ưu tiên dùng sẵn có, phân quyền tối thiểu, tách bạch rõ ràng.
