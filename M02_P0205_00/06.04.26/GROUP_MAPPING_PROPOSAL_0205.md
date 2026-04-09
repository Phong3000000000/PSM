# Đề xuất mapping group cho module 0205

## 1. Mục tiêu tài liệu

Tài liệu này dùng để đối chiếu giữa:
- group hiện tại đang có trong module `M02_P0205_00`
- group chuẩn theo file ghi chú quyền
- đề xuất nên giữ, bỏ, đổi tên, hay map sang group chuẩn nào

Nguồn tham chiếu chính:
- [GHI_CHU_GROUP_QUYEN.md](/d:/odoo-19.0+e.20250918/addons/M02_P0205_00/06.04.26/GHI_CHU_GROUP_QUYEN.md)
- [GROUP_PERMISSION_MAP_0205.md](/d:/odoo-19.0+e.20250918/addons/M02_P0205_00/06.04.26/GROUP_PERMISSION_MAP_0205.md)

## 2. Group hiện tại của 0205

Các group custom hiện đang được định nghĩa trong module:

| Group hiện tại | Tên hiển thị | Vai trò hiện tại trong 0205 | File định nghĩa |
| --- | --- | --- | --- |
| `M02_P0205_00.group_hr_validator` | HR Validator | Nhóm HR nhận activity validate / duyệt trong flow request | [security/hr_validator_group.xml](/d:/odoo-19.0+e.20250918/addons/M02_P0205_00/security/hr_validator_group.xml) |
| `M02_P0205_00.group_ceo_recruitment` | CEO Recruitment Approver | Nhóm CEO duyệt tuyển dụng | [security/approval_groups.xml](/d:/odoo-19.0+e.20250918/addons/M02_P0205_00/security/approval_groups.xml) |
| `M02_P0205_00.group_bod_recruitment` | BOD Recruitment Viewer | Nhóm BOD tham gia vòng phỏng vấn / evaluation | [security/approval_groups.xml](/d:/odoo-19.0+e.20250918/addons/M02_P0205_00/security/approval_groups.xml) |
| `M02_P0205_00.group_abu_recruitment` | ABU Recruitment Control | Nhóm ABU tham gia vòng phỏng vấn / evaluation | [security/approval_groups.xml](/d:/odoo-19.0+e.20250918/addons/M02_P0205_00/security/approval_groups.xml) |

Ghi chú:
- cả 4 group trên hiện đều đang imply `hr.group_hr_manager`

## 3. Nên map sang group chuẩn nào

Dựa trên [GHI_CHU_GROUP_QUYEN.md](/d:/odoo-19.0+e.20250918/addons/M02_P0205_00/06.04.26/GHI_CHU_GROUP_QUYEN.md), các group chuẩn liên quan gần nhất là:

- `GDH_RST_ALL_BASE_S`
- `GDH_RST_HR_HEAD_M`
- `GDH_RST_HR_RECRUITMENT_S`
- `GDH_RST_HR_RECRUITMENT_M`

Đề xuất mapping:

| Group hiện tại của 0205 | Group chuẩn đề xuất | Lý do |
| --- | --- | --- |
| `M02_P0205_00.group_hr_validator` | `GDH_RST_HR_RECRUITMENT_M` hoặc `GDH_RST_HR_HEAD_M` | Đây là vai trò duyệt/xác nhận nghiệp vụ tuyển dụng phía HR, gần với quản lý tuyển dụng hoặc trưởng phòng HR hơn là một group riêng |
| `M02_P0205_00.group_ceo_recruitment` | Chưa có group chuẩn tương ứng trong danh sách hiện tại | File chuẩn hiện chưa thấy mã quyền riêng cho CEO duyệt tuyển dụng |
| `M02_P0205_00.group_bod_recruitment` | Chưa có group chuẩn tương ứng trong danh sách hiện tại | File chuẩn hiện chưa thấy mã quyền riêng cho BOD tham gia tuyển dụng |
| `M02_P0205_00.group_abu_recruitment` | Chưa có group chuẩn tương ứng trong danh sách hiện tại | File chuẩn hiện chưa thấy mã quyền riêng cho ABU tham gia tuyển dụng |

Nhận xét:
- `group_hr_validator` là group dễ map nhất sang bộ chuẩn hiện có
- 3 group còn lại chưa có đối tượng chuẩn tương ứng trong danh sách hiện tại, nên chưa thể “map thẳng” mà không cần quyết định nghiệp vụ bổ sung

## 4. Group nào nên giữ

### 4.1 Nên giữ theo nghĩa nghiệp vụ

- `group_ceo_recruitment`
- `group_bod_recruitment`
- `group_abu_recruitment`

Lý do:
- đây là 3 vai trò nghiệp vụ có thật trong flow `0205`
- hiện đang được dùng trong:
  - view
  - logic gửi activity
  - logic chọn interviewer / evaluation
- nếu bỏ ngay sẽ ảnh hưởng trực tiếp đến flow đang chạy

### 4.2 Nên giữ tạm thời theo nghĩa kỹ thuật

- `group_hr_validator`

Lý do:
- hiện vẫn đang được code dùng để tìm người nhận activity HR validate
- tuy nhiên đây là group có khả năng cao sẽ được thay bằng group chuẩn sau khi thống nhất mapping

## 5. Group nào nên bỏ hoặc đổi tên

### 5.1 Group nên xem xét bỏ sau khi map sang group chuẩn

- `M02_P0205_00.group_hr_validator`

Hướng xử lý đề xuất:
- nếu xác nhận vai trò này thực chất là “quản lý tuyển dụng” thì map sang `GDH_RST_HR_RECRUITMENT_M`
- nếu xác nhận vai trò này là “trưởng phòng HR” thì map sang `GDH_RST_HR_HEAD_M`
- sau khi code đã dùng group chuẩn ổn định, có thể bỏ group custom này

### 5.2 Group nên đổi tên hoặc chuẩn hóa mã

- `M02_P0205_00.group_ceo_recruitment`
- `M02_P0205_00.group_bod_recruitment`
- `M02_P0205_00.group_abu_recruitment`

Lý do:
- hiện tên đang theo kiểu cục bộ của module
- chưa bám cấu trúc mã quyền chuẩn dạng:
  - `COMPANY_DIVISION_DEPARTMENT_JOBPOSITION_LEVEL`

Hướng xử lý đề xuất:
- nếu business xác nhận đây là các vai trò chuẩn dùng lâu dài, nên bổ sung mã chuẩn tương ứng vào danh mục quyền chuẩn
- sau đó đổi `id`/cách đặt tên group để bám cùng convention

Ví dụ hướng chuẩn hóa về sau:
- nhóm CEO tuyển dụng: cần một mã chuẩn riêng nếu CEO thực sự là một vai trò phân quyền chính thức
- nhóm BOD tuyển dụng: cần một mã chuẩn riêng nếu BOD là nhóm tham gia phỏng vấn chính thức
- nhóm ABU tuyển dụng: cần một mã chuẩn riêng nếu ABU là nhóm tham gia phỏng vấn chính thức

## 6. Đề xuất quyết định thực tế

### Phương án thực tế nhất ở thời điểm hiện tại

- Giữ lại `group_ceo_recruitment`, `group_bod_recruitment`, `group_abu_recruitment`
- Không để 3 group này imply `hr.group_hr_manager` nữa
- Xem `group_hr_validator` là group chuyển tiếp, chuẩn bị map sang group chuẩn HR

### Phương án mục tiêu sau khi chuẩn hóa toàn hệ thống

- bỏ `group_hr_validator`
- thay bằng group chuẩn HR tương ứng
- chuẩn hóa tên/mã của `group_ceo_recruitment`, `group_bod_recruitment`, `group_abu_recruitment`
- hoặc bổ sung các mã group chuẩn mới vào danh mục chuẩn nếu business xác nhận dùng lâu dài

## 7. Kết luận ngắn

| Group hiện tại | Đề xuất |
| --- | --- |
| `group_hr_validator` | Không nên giữ lâu dài, nên map sang group chuẩn HR rồi bỏ dần |
| `group_ceo_recruitment` | Nên giữ về mặt nghiệp vụ, nhưng nên chuẩn hóa tên/mã |
| `group_bod_recruitment` | Nên giữ về mặt nghiệp vụ, nhưng nên chuẩn hóa tên/mã |
| `group_abu_recruitment` | Nên giữ về mặt nghiệp vụ, nhưng nên chuẩn hóa tên/mã |

Tóm lại:
- group HR validator là ứng viên rõ nhất để bỏ sau khi map
- 3 group CEO/BOD/ABU chưa nên bỏ, nhưng nên đưa vào lộ trình chuẩn hóa
- không nên tiếp tục để các group flow này mang kèm quyền `hr.group_hr_manager`
