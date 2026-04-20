# Hướng dẫn kế thừa và sử dụng Yêu Cầu Tuyển Dụng của module 0205

Tài liệu này dành cho dev cần đọc, kế thừa, mở rộng hoặc tích hợp với chức năng `Yêu Cầu Tuyển Dụng` trong module `M02_P0205`.

## 1. Phạm vi chức năng

Chức năng `Yêu Cầu Tuyển Dụng` của `0205` đang dùng model chính:

- `x_psm_recruitment_request`
- `x_psm_recruitment_request_line`
- `x_psm_recruitment_request_approver`

Trong đó:

- `x_psm_recruitment_request` là bản ghi nghiệp vụ chính
- `x_psm_recruitment_request_line` là danh sách vị trí tuyển dụng
- `x_psm_recruitment_request_approver` là model phụ cũ của flow duyệt

## 2. Luồng hiện tại

### 2.1. Luồng nghiệp vụ chính

Record `x_psm_recruitment_request` vẫn là record gốc để:

- lưu thông tin yêu cầu tuyển dụng
- lưu phòng ban, vị trí, số lượng, lý do
- liên kết đợt tuyển dụng hoặc kế hoạch tuyển dụng
- publish job sau khi được duyệt

### 2.2. Luồng duyệt

Phần duyệt hiện đang chạy theo mô hình hybrid:

- `approval.request` xử lý việc duyệt
- `x_psm_recruitment_request` xử lý nghiệp vụ tuyển dụng

Nghĩa là:

- khi bấm `Gửi duyệt`, hệ thống tạo một `approval.request`
- approver được sinh động từ group
- khi `approval.request` thay đổi trạng thái, `x_psm_recruitment_request` sẽ đồng bộ lại `state`
- khi duyệt hoàn tất, request tuyển dụng chạy logic chuyển trạng thái và publish job

## 3. Những model và field quan trọng

## 3.1. Trên model `x_psm_recruitment_request`

Các field quan trọng:

- `name`
- `request_type`
- `job_id`
- `department_id`
- `quantity`
- `reason`
- `line_ids`
- `batch_id`
- `recruitment_plan_id`
- `state`
- `x_psm_approval_request_id`
- `x_psm_approval_status`

Ý nghĩa:

- `x_psm_approval_request_id`: link sang `approval.request`
- `x_psm_approval_status`: trạng thái approval hiện tại

## 3.2. Trên model gốc `approval.request`

Module `0205` đang kế thừa `approval.request` và thêm các field:

- `x_psm_0205_recruitment_request_id`
- `x_psm_0205_request_code`
- `x_psm_0205_request_owner_id`
- `x_psm_0205_department_id`
- `x_psm_0205_request_type`
- `x_psm_0205_reason`
- `x_psm_0205_request_line_ids`
- `x_psm_0205_total_quantity`
- `x_psm_0205_request_line_count`

Mục đích:

- hiển thị summary trực tiếp trên approval form
- mở sâu sang record gốc khi người duyệt cần xem chi tiết

## 4. File code chính cần biết

### 4.1. Model tuyển dụng

File:

- `addons/M02_P0205/models/recruitment_request.py`

Phần này chứa:

- model nghiệp vụ chính
- logic submit approval
- logic đồng bộ trạng thái theo approval
- logic publish job sau khi duyệt xong

### 4.2. Model mở rộng approval

File:

- `addons/M02_P0205/models/recruitment_approval.py`

Phần này chứa:

- field liên kết từ `approval.request` sang request tuyển dụng
- summary field để render trên approval form
- action mở record gốc

### 4.3. View tuyển dụng

File:

- `addons/M02_P0205/views/recruitment_request_views.xml`

Phần này chứa:

- form view của `x_psm_recruitment_request`
- nút `Gửi duyệt`
- nút mở approval

### 4.4. View approval

File:

- `addons/M02_P0205/views/approval_request_views.xml`

Phần này chứa:

- summary của yêu cầu tuyển dụng trên form approval
- tab chi tiết line tuyển dụng
- nút `Mở yêu cầu gốc`

### 4.5. Dữ liệu category approval

File:

- `addons/M02_P0205/data/approval_category_data.xml`

Category đang dùng:

- `approval_category_recruitment_request`

## 5. Group và approver đang dùng

### 5.1. HR approver

Bước HR duyệt hiện lấy trực tiếp từ:

- `M02_P0200.GDH_RST_HR_RECRUITMENT_M`

Không còn dùng:

- `M02_P0205.group_gdh_rst_office_recruitment_mgr`

cho bước approval chính.

### 5.2. CEO approver

Bước CEO duyệt hiện vẫn dùng group riêng của `0205`:

- `M02_P0205.group_gdh_rst_office_recruitment_mgr_ceo`

### 5.3. Group đặc thù khác

Các group sau vẫn đang dùng cho flow riêng, chưa bỏ:

- `M02_P0205.group_gdh_rst_office_recruitment_mgr_bod`
- `M02_P0205.group_gdh_rst_office_recruitment_mgr_abu`

Lưu ý:

- không tự ý gộp `CEO/BOD/ABU` vào recruiter nếu chưa chốt nghiệp vụ

## 6. Những thứ dev khác cần đặc biệt lưu ý

### 6.1. Đừng hiểu nhầm approval là record chính

`approval.request` chỉ là record duyệt.

Record nghiệp vụ chính vẫn là:

- `x_psm_recruitment_request`

Nếu cần đọc hoặc mở rộng logic nghiệp vụ tuyển dụng, hãy sửa ở model này trước.

### 6.2. Không bỏ link 2 chiều giữa approval và recruitment request

Nếu xóa hoặc đổi sai các field:

- `x_psm_approval_request_id`
- `x_psm_0205_recruitment_request_id`

thì:

- approval sẽ không mở được record gốc
- request sẽ không đồng bộ đúng trạng thái

### 6.3. Khi sửa logic duyệt, kiểm tra cả 2 chiều

Mỗi thay đổi liên quan approval cần test:

- từ `x_psm_recruitment_request` tạo approval
- từ `approval.request` approve/refuse
- trạng thái quay lại request tuyển dụng

### 6.4. Khi thêm field mới, phải theo đúng quy ước đặt tên

Theo tài liệu quy ước:

- field mới trên model gốc: `x_psm_0205_<ten_field>`
- field mới trên model mới: `x_psm_<ten_field>`

Không nên thêm field mới kiểu tên chung chung vì sẽ khó bảo trì sau này.

### 6.5. Khi thêm view/action mới, phải giữ đúng convention

- action mới: `action_psm_<ten_action>`
- view mới: `view_psm_<ten_view>`

## 7. Những tình huống dễ lỗi

### 7.1. Không tìm thấy người duyệt

Nếu bấm `Gửi duyệt` báo:

- `Không tìm thấy người duyệt cho Yêu Cầu Tuyển Dụng`

thì thường do:

- group `GDH_RST_HR_RECRUITMENT_M` chưa có user
- group CEO chưa có user
- user tạo request bị loại khỏi danh sách approver vì không được tự duyệt request của chính mình

### 7.2. Approval mở được nhưng thiếu chi tiết

Nếu approval không hiện đúng summary hoặc tab line:

- kiểm tra module `M02_P0205` đã upgrade chưa
- kiểm tra field mới trên `approval.request` đã được nạp chưa

### 7.3. Approval bị lỗi từ module khác

`approval.request` là model gốc dùng chung.

Nếu mở approval bị lỗi traceback ở module khác như:

- offboarding
- resignation
- survey

thì cần hiểu:

- đó có thể không phải lỗi của tuyển dụng
- phải xem module nào đang `_inherit = "approval.request"` và compute field đang nổ

## 8. Cách mở rộng an toàn

Nếu dev khác cần mở rộng tiếp, nên làm theo thứ tự:

1. Giữ `x_psm_recruitment_request` là record nghiệp vụ gốc
2. Chỉ thêm field summary lên `approval.request` nếu thực sự cần cho người duyệt
3. Không nhét logic nghiệp vụ tuyển dụng sâu vào module `approvals`
4. Approval lo phần duyệt
5. Recruitment request lo phần nghiệp vụ sau duyệt

## 9. Checklist sau khi sửa

Sau mỗi thay đổi liên quan `Yêu Cầu Tuyển Dụng`, nên test:

1. Tạo request mới
2. Bấm `Gửi duyệt`
3. Approval request được tạo thành công
4. Approval hiện đúng summary
5. Nút `Mở yêu cầu gốc` hoạt động
6. Approve từ approval form
7. State của `x_psm_recruitment_request` đồng bộ đúng
8. Job được publish đúng sau khi duyệt xong

## 10. Kết luận ngắn

Muốn hiểu `Yêu Cầu Tuyển Dụng` của `0205`, hãy nhớ 3 ý:

- `x_psm_recruitment_request` là record nghiệp vụ chính
- `approval.request` là engine duyệt
- hai record này đang được nối bằng cơ chế hybrid, không nên tách rời khi kế thừa
