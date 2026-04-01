Bật dev mode, vào apps xóa bộ lọc app đi, tìm dev admin tool, cài module. Khi cài xong module sẽ tự động bypass expiration bằng 3 cách:

1. Sửa luôn hạn của DB tới 2099 (giá trị thật trong database)
2. Fake gia hạn qua session_info, trả về date = 2099 (UI thấy 2099)
3. Patch JS daysLeft = 27375 (75 năm), UI nghĩ còn 75 năm

Nếu bị đăng xuất mà không đăng nhập lại được thì chạy reset_password.sql. Chỉ dùng cho DEV/TEST!