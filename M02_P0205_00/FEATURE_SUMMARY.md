## Tóm tắt enhancements cho Recruitment Request

1. **Form header bổ sung Phòng ban:**  
   - Thêm field `department_id` ngay cạnh người yêu cầu (từ model `recruitment.request`).  
   - Field này tự động lấy phòng ban của người yêu cầu khi tạo/đổi `user_id`, đảm bảo thông tin luôn đồng bộ.

2. **Danh sách tuyển dụng (line_ids) tự động kế thừa phòng ban:**  
   - Khi mở `Add a line`, context truyền `default_department_id` lấy từ `department_id` hoặc phòng ban người yêu cầu, nên dòng mới sẽ tự gán phòng ban tương ứng.  
   - Model `recruitment.request.line` ưu tiên giá trị này trong `default_get`.

3. **View điều chỉnh:**  
   - Loại bỏ hai cột ngày bắt đầu/kết thúc trong bảng list (để nhìn rõ các cột chính).  
   - Cập nhật context cho `line_ids` để dòng mới nhận phòng ban.  
   - Menu “Kế hoạch tuyển dụng” và “Kế hoạch con” được thêm vào menu gốc `Recruitment` mặc định (để hiển thị trong app Recruitment gốc), giữ nguyên menu cũ trong “Tuyển dụng VP”.

4. **Các hành động dữ liệu liên quan (đã có sẵn trong model trước đó nhưng có liên quan):**  
- `recruitment.request` liên kết đến `recruitment.plan_id` và có sẵn các logics gửi activity cho HR/CEO, hành động publish job, tăng `no_of_recruitment`... (các phần này không sửa trong request hiện tại nhưng tạo thành bối cảnh của các menu mới).

> *Lưu ý:* Tập trung vào phần “feature”/tính năng đã thực hiện từ đầu cuộc hội thoại (không liệt kê các bản vá bug). Nếu cần mở rộng, có thể chuyển nội dung vào README hoặc tài liệu tổng quan của module.

## Lưu ý khi kế thừa
1. Các tích hợp trên `recruitment.request` giả định `department_id` có thể được ghi lại thông qua view (Field hỗ trợ read/write). Nếu một dev khác override view/model cần đảm bảo không vô hiệu hóa field này hoặc sự kiện `onchange`.
2. `recruitment.request.line.default_get` dùng context `'default_department_id'`; khi kế thừa controller hay logic tạo line cần truyền context tương tự để tránh line mới thiếu phòng ban.
3. Các menu mới trong file `recruitment_plan_views.xml` gắn tới root của `hr_recruitment`. Nếu chỉnh sửa action/menu, giữ id cũ hoặc cập nhật các tham chiếu để không mất đường link từ thanh menu Recruitment.
4. Tài liệu summary nên cập nhật khi thay đổi behavior context hoặc logic tự động gán phòng ban, tránh dev sau phải reverse-engineer.
