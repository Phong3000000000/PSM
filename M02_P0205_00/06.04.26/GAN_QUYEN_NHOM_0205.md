# Gán quyền nhóm cho module 0205

Tài liệu này ghi lại quyết định gán quyền cho module `M02_P0205_00` sau khi chuẩn hóa theo backbone group của module `M02_P0200_00`.

## 1. Mục tiêu

- Khôi phục quyền truy cập cho các menu của `0205` như:
  - `Yêu Cầu Tuyển Dụng`
  - `Kế hoạch tuyển dụng`
  - `Kế hoạch con`
- Bỏ phụ thuộc ACL trực tiếp vào:
  - `base.group_user`
  - `hr_recruitment.group_hr_recruitment_manager`
- Chuyển quyền truy cập model về nhóm chuẩn của `0200`
- Tạm thời giữ lại các group đặc thù của flow `0205` như `CEO`, `BOD`, `ABU`

## 2. Các file security cần nạp trong manifest

Trong `__manifest__.py`, cần bật lại các file sau:

- `security/hr_validator_group.xml`
- `security/approval_groups.xml`
- `security/recruitment_security.xml`
- `security/ir.model.access.csv`

## 3. Nguyên tắc gán quyền

### 3.1. Nhóm chuẩn dùng cho ACL

Các quyền truy cập model của `0205` sẽ ưu tiên dùng nhóm chuẩn của `0200`:

- `M02_P0200_00.GDH_RST_HR_RECRUITMENT_S`
- `M02_P0200_00.GDH_RST_HR_RECRUITMENT_M`

Trong đó:

- nhóm `S` dùng cho quyền nghiệp vụ tuyển dụng ở mức nhân viên
- nhóm `M` dùng cho quyền nghiệp vụ tuyển dụng ở mức quản lý

### 3.2. Nhóm đặc thù tạm thời chưa đổi

Các group đặc thù của flow `0205` hiện chưa chuyển sang `0200` vì chưa có group chuẩn tương đương:

- `group_gdh_rst_office_recruitment_mgr_ceo`
- `group_gdh_rst_office_recruitment_mgr_bod`
- `group_gdh_rst_office_recruitment_mgr_abu`

Các group này vẫn được giữ để phục vụ:

- gửi activity đúng người
- điều khiển nút theo vai trò trong view
- xác định interviewer hoặc approver theo flow riêng

## 4. Mapping ACL đã thống nhất

### 4.1. Nhóm nhân viên tuyển dụng

Gán cho `M02_P0200_00.GDH_RST_HR_RECRUITMENT_S`:

- `x_psm_recruitment_request`
- `x_psm_recruitment_plan`
- `x_psm_recruitment_plan_line`
- `x_psm_applicant_evaluation`
- `x_psm_applicant_evaluation_line`
- `x_psm_recruitment_batch`
- `x_psm_recruitment_request_line`
- `x_psm_recruitment_request_approver`
- `survey.survey` với quyền đọc

Quyền dự kiến:

- `read = 1`
- `write = 1`
- `create = 1`
- `unlink = 0`

Riêng `survey.survey`:

- `read = 1`
- `write = 0`
- `create = 0`
- `unlink = 0`

### 4.2. Nhóm quản lý tuyển dụng

Gán cho `M02_P0200_00.GDH_RST_HR_RECRUITMENT_M`:

- `x_psm_recruitment_request`
- `x_psm_recruitment_plan`
- `x_psm_recruitment_plan_line`
- `x_psm_applicant_evaluation`
- `x_psm_applicant_evaluation_line`
- `x_psm_recruitment_batch`
- `x_psm_recruitment_request_line`
- `x_psm_recruitment_request_approver`
- `survey.survey` với quyền đọc

Quyền dự kiến:

- `read = 1`
- `write = 1`
- `create = 1`
- `unlink = 1`

Riêng `survey.survey`:

- `read = 1`
- `write = 0`
- `create = 0`
- `unlink = 0`

## 5. Nội dung ACL đề xuất

File `security/ir.model.access.csv` được đề xuất theo cấu trúc sau:

```csv
id,name,model_id:id,group_id:id,perm_read,perm_write,perm_create,perm_unlink
access_recruitment_request_staff,x_psm_recruitment_request.staff,model_x_psm_recruitment_request,M02_P0200_00.GDH_RST_HR_RECRUITMENT_S,1,1,1,0
access_recruitment_request_manager,x_psm_recruitment_request.manager,model_x_psm_recruitment_request,M02_P0200_00.GDH_RST_HR_RECRUITMENT_M,1,1,1,1
access_recruitment_plan_staff,x_psm_recruitment_plan.staff,model_x_psm_recruitment_plan,M02_P0200_00.GDH_RST_HR_RECRUITMENT_S,1,1,1,0
access_recruitment_plan_manager,x_psm_recruitment_plan.manager,model_x_psm_recruitment_plan,M02_P0200_00.GDH_RST_HR_RECRUITMENT_M,1,1,1,1
access_recruitment_plan_line_staff,x_psm_recruitment_plan_line.staff,model_x_psm_recruitment_plan_line,M02_P0200_00.GDH_RST_HR_RECRUITMENT_S,1,1,1,0
access_recruitment_plan_line_manager,x_psm_recruitment_plan_line.manager,model_x_psm_recruitment_plan_line,M02_P0200_00.GDH_RST_HR_RECRUITMENT_M,1,1,1,1
access_hr_applicant_evaluation_staff,x_psm_applicant_evaluation.staff,model_x_psm_applicant_evaluation,M02_P0200_00.GDH_RST_HR_RECRUITMENT_S,1,1,1,0
access_hr_applicant_evaluation_manager,x_psm_applicant_evaluation.manager,model_x_psm_applicant_evaluation,M02_P0200_00.GDH_RST_HR_RECRUITMENT_M,1,1,1,1
access_hr_applicant_evaluation_line_staff,x_psm_applicant_evaluation_line.staff,model_x_psm_applicant_evaluation_line,M02_P0200_00.GDH_RST_HR_RECRUITMENT_S,1,1,1,0
access_hr_applicant_evaluation_line_manager,x_psm_applicant_evaluation_line.manager,model_x_psm_applicant_evaluation_line,M02_P0200_00.GDH_RST_HR_RECRUITMENT_M,1,1,1,1
access_recruitment_batch_staff,x_psm_recruitment_batch.staff,model_x_psm_recruitment_batch,M02_P0200_00.GDH_RST_HR_RECRUITMENT_S,1,1,1,0
access_recruitment_batch_manager,x_psm_recruitment_batch.manager,model_x_psm_recruitment_batch,M02_P0200_00.GDH_RST_HR_RECRUITMENT_M,1,1,1,1
access_recruitment_request_line_staff,x_psm_recruitment_request_line.staff,model_x_psm_recruitment_request_line,M02_P0200_00.GDH_RST_HR_RECRUITMENT_S,1,1,1,0
access_recruitment_request_line_manager,x_psm_recruitment_request_line.manager,model_x_psm_recruitment_request_line,M02_P0200_00.GDH_RST_HR_RECRUITMENT_M,1,1,1,1
access_recruitment_request_approver_staff,x_psm_recruitment_request_approver.staff,model_x_psm_recruitment_request_approver,M02_P0200_00.GDH_RST_HR_RECRUITMENT_S,1,1,1,0
access_recruitment_request_approver_manager,x_psm_recruitment_request_approver.manager,model_x_psm_recruitment_request_approver,M02_P0200_00.GDH_RST_HR_RECRUITMENT_M,1,1,1,1
access_survey_staff,survey.survey,survey.model_survey_survey,M02_P0200_00.GDH_RST_HR_RECRUITMENT_S,1,0,0,0
access_survey_manager,survey.survey,survey.model_survey_survey,M02_P0200_00.GDH_RST_HR_RECRUITMENT_M,1,0,0,0
```

## 6. Lý do chưa dùng `GDH_RST_ALL_BASE_S`

Hiện tại chưa mở quyền các model của `0205` cho `M02_P0200_00.GDH_RST_ALL_BASE_S` vì:

- cần an toàn hơn trong giai đoạn khôi phục menu và quyền
- chưa chốt nghiệp vụ rằng mọi user nội bộ đều được tạo yêu cầu tuyển dụng
- nếu mở quá rộng sớm có thể làm sai phạm vi nghiệp vụ

Nếu business xác nhận mọi user nội bộ đều được lập `Yêu Cầu Tuyển Dụng`, có thể xem xét tách riêng các model sau sang `GDH_RST_ALL_BASE_S`:

- `x_psm_recruitment_request`
- `x_psm_recruitment_request_line`
- `x_psm_recruitment_request_approver`

## 7. Việc cần làm sau khi chỉnh file quyền

Sau khi cập nhật manifest và ACL:

1. Upgrade lại module `M02_P0205_00`
2. Kiểm tra lại menu:
   - `Yêu Cầu Tuyển Dụng`
   - `Kế hoạch tuyển dụng`
   - `Kế hoạch con`
3. Mở thử từng menu để xác nhận không còn lỗi `Access Error`
4. Kiểm tra user test đã được gán đúng group của `0200`

## 8. Ghi chú thêm

- Việc chuẩn hóa ACL sang `0200` không đồng nghĩa xóa ngay các group flow đặc thù của `0205`
- Các group `CEO`, `BOD`, `ABU` hiện vẫn cần được giữ để không làm hỏng flow nghiệp vụ
- Ở bước sau có thể tiếp tục chuẩn hóa code backend từ group cũ sang group chuẩn nếu backbone bổ sung đủ group đích
