# PSM Database Sync Module cho Odoo 17

Module đồng bộ dữ liệu từ các cơ sở dữ liệu ngoài (MySQL, PostgreSQL, MS SQL Server, Oracle, MariaDB) vào Odoo 17.

## 🚀 Tính năng chính

### 1. **Kết nối đa nền tảng**
- ✅ MySQL/MariaDB
- ✅ PostgreSQL  
- ✅ MS SQL Server
- ✅ Oracle
- ✅ MariaDB
- 🔐 Hỗ trợ SSL và các tùy chọn bảo mật

### 2. **Ánh xạ thông minh**
- 🤖 **AI-powered field mapping**: Tự động đề xuất ánh xạ trường dựa trên tên và kiểu dữ liệu
- 🔗 **Tự động phát hiện quan hệ**: Phát hiện khóa ngoại và đề xuất quan hệ
- 🎯 **Ánh xạ linh hoạt**: Hỗ trợ bảng hoặc truy vấn SQL tùy chỉnh

### 3. **Chuyển đổi dữ liệu mạnh mẽ**
- 📅 Chuyển đổi định dạng ngày/giờ
- 🔢 Xử lý định dạng số và tiền tệ
- 🗂️ Ánh xạ giá trị tùy chỉnh
- 🐍 Hàm Python tùy chỉnh cho chuyển đổi phức tạp
- 🔗 Xử lý quan hệ giữa các bảng

### 4. **Đồng bộ linh hoạt**
- 🔄 **Đồng bộ đầy đủ**: Đồng bộ toàn bộ dữ liệu
- ⏰ **Đồng bộ tăng dần**: Chỉ đồng bộ dữ liệu mới/thay đổi
- 🕐 **Lập lịch tự động**: Đồng bộ theo lịch trình
- 👤 **Đồng bộ thủ công**: Kiểm soát hoàn toàn quá trình

### 5. **Hiệu suất cao**
- 🚀 **Xử lý theo lô**: Tối ưu hiệu suất với batch processing
- 📊 **Checksum**: Phát hiện thay đổi nhanh chóng
- ⚡ **Queue Jobs**: Xử lý background với queue_job
- 🔧 **Tối ưu truy vấn**: Tự động tối ưu SQL queries

### 6. **Giám sát và báo cáo**
- 📈 **Dashboard tổng quan**: Theo dõi trạng thái real-time
- 📝 **Nhật ký chi tiết**: Ghi lại mọi hoạt động đồng bộ
- 📊 **Thống kê hiệu suất**: Theo dõi tỷ lệ thành công, thời gian xử lý
- 🔍 **Truy vết lỗi**: Chi tiết lỗi và cách khắc phục

## 📋 Yêu cầu hệ thống

### Odoo
- Odoo 17.0+
- Python 3.8+

### Python Dependencies
```bash
pip install sqlalchemy pymysql pyodbc cx_Oracle psycopg2-binary
```

### Odoo Modules
- `base`
- `mail` 
- `web`
- `queue_job` (khuyến nghị)

## 🛠️ Cài đặt

### 1. Tải module
```bash
cd /path/to/odoo/addons
git clone <repository_url> psm_db_sync
```

### 2. Cài đặt dependencies
```bash
pip install -r psm_db_sync/requirements.txt
```

### 3. Cập nhật Odoo
- Restart Odoo server
- Vào Apps → Update Apps List
- Tìm "PSM Database Sync" và Install

### 4. Cấu hình permissions
Gán quyền phù hợp cho users:
- **DB Sync: User** - Xem và sử dụng chức năng cơ bản
- **DB Sync: Manager** - Tạo và chỉnh sửa cấu hình
- **DB Sync: Administrator** - Toàn