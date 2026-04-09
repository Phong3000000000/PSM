# Ghi Chú Group Quyền

Tài liệu này dùng để ghi chú và tra cứu nhanh các group quyền phục vụ triển khai về sau.

## 1. Quy ước cấu trúc mã quyền

Mã quyền đang theo cấu trúc chung:

`COMPANY_DIVISION_DEPARTMENT_JOBPOSITION_LEVEL`

Ví dụ:

- `GDH_RST_HR_RECRUITMENT_S`
- `GDH_OPS_STORE_RGM_M`

Ý nghĩa các thành phần:

- `GDH`: Company
- `RST` hoặc `OPS`: Division
- `HR`, `SYSTEM`, `STORE`, `ALL`, `OPS`: Department
- `RECRUITMENT`, `HEAD`, `ADMIN`, `RGM`...: Job position
- `S`, `M`: Level

Gợi ý hiểu level:

- `S`: Staff
- `M`: Manager

## 2. Danh sách group quyền

| STT | Code | Mô tả |
|---|---|---|
| 1 | `GDH_RST_SYSTEM_ST_M` | Quản lý hệ thống |
| 2 | `GDH_RST_ALL_BASE_S` | Người dùng hệ thống |
| 3 | `GDH_RST_HR_HEAD_M` | Trưởng phòng nhân sự |
| 4 | `GDH_RST_HR_RECRUITMENT_S` | Nhân viên tuyển dụng |
| 5 | `GDH_RST_HR_RECRUITMENT_M` | Quản lý tuyển dụng |
| 6 | `GDH_RST_HR_CNB_S` | Nhân viên tính lương |
| 7 | `GDH_RST_HR_CNB_M` | Quản lý tính lương |
| 8 | `GDH_RST_HR_ADMIN_M` | Quản lý admin |
| 9 | `GDH_RST_HR_ADMIN_S` | Nhân viên admin |
| 10 | `GDH_RST_HR_HRBP_M` | Quản lý BP |
| 11 | `GDH_RST_HR_HRBP_S` | Nhân viên BP |
| 12 | `GDH_OPS_STORE_RGM_M` | Cửa hàng trưởng |
| 13 | `GDH_OPS_STORE_PM_M` | People manager |
| 14 | `GDH_OPS_STORE_ST_M` | System manager |
| 15 | `GDH_OPS_STORE_SM_M` | Shift manager |
| 16 | `GDH_OPS_STORE_CREW_S` | Crew |
| 17 | `GDH_OPS_STORE_TRAINER_S` | Crew trainer |
| 18 | `GDH_OPS_STORE_GEL_M` | GEL |
| 19 | `GDH_RST_OPS_OC_S` | Operation consultant |

## 3. Phân nhóm theo khối

### 3.1. Khối RST

#### System

- `GDH_RST_SYSTEM_ST_M`: Quản lý hệ thống
- `GDH_RST_ALL_BASE_S`: Người dùng hệ thống

#### HR

- `GDH_RST_HR_HEAD_M`: Trưởng phòng nhân sự
- `GDH_RST_HR_RECRUITMENT_S`: Nhân viên tuyển dụng
- `GDH_RST_HR_RECRUITMENT_M`: Quản lý tuyển dụng
- `GDH_RST_HR_CNB_S`: Nhân viên tính lương
- `GDH_RST_HR_CNB_M`: Quản lý tính lương
- `GDH_RST_HR_ADMIN_M`: Quản lý admin
- `GDH_RST_HR_ADMIN_S`: Nhân viên admin
- `GDH_RST_HR_HRBP_M`: Quản lý BP
- `GDH_RST_HR_HRBP_S`: Nhân viên BP

#### OPS thuộc RST

- `GDH_RST_OPS_OC_S`: Operation consultant

### 3.2. Khối OPS

#### Store

- `GDH_OPS_STORE_RGM_M`: Cửa hàng trưởng
- `GDH_OPS_STORE_PM_M`: People manager
- `GDH_OPS_STORE_ST_M`: System manager
- `GDH_OPS_STORE_SM_M`: Shift manager
- `GDH_OPS_STORE_CREW_S`: Crew
- `GDH_OPS_STORE_TRAINER_S`: Crew trainer
- `GDH_OPS_STORE_GEL_M`: GEL

## 4. Ghi chú sử dụng về sau

- Đây là danh sách group quyền chuẩn hóa để tham chiếu khi thiết kế phân quyền.
- Khi tạo group mới, nên bám theo cùng cấu trúc mã để dễ quản lý và tra cứu.
- Cần thống nhất rõ:
  - group nào là quyền nghiệp vụ
  - group nào là quyền quản lý
  - group nào là quyền dùng chung toàn hệ thống
- Nên tránh tạo group trùng ý nghĩa nhưng khác tên.
- Nếu một module chỉ cần quyền tối thiểu, nên map vào group sẵn có trước khi nghĩ đến việc tạo group mới.

## 5. Đề xuất áp dụng cho tài liệu và code

- Trong tài liệu: luôn ghi cả `Code` và `Mô tả`.
- Trong XML security: nên giữ tên `id` gần với mã quyền thực tế để dễ đối chiếu.
- Trong phần phân quyền nghiệp vụ: nên mô tả rõ ai được xem, ai được tạo, ai được duyệt, ai được quản lý.
