# 📘 Module: Quy Trình Tuyển Dụng Khối Cửa Hàng

## 🎯 Mục Đích
Module quản lý lịch phỏng vấn cho các cửa hàng, tự động hóa việc gửi email mời phỏng vấn kèm khảo sát cho ứng viên.

## ✨ Tính Năng

### 1. Quản Lý Lịch Phỏng Vấn
- **Store Manager** đặt 3 ngày trong tuần có thể phỏng vấn
- Hiển thị dạng Kanban cards (mỗi cửa hàng 1 card)
- Validation: 3 ngày phải nằm trong tuần được chọn

### 2. Gửi Thư Mời Phỏng Vấn
- **HR** chọn ứng viên → Chọn cửa hàng → Auto-load schedule
- Click button "Gửi Thư Mời Phỏng Vấn"
- Email professional với:
  - 3 ngày phỏng vấn (format đẹp)
  - Link khảo sát
  - Thông tin cửa hàng

### 3. Khảo Sát Trước Phỏng Vấn
- Survey mẫu với 6 câu hỏi:
  1. Kinh nghiệm F&B
  2. Ca làm việc ưa thích
  3. Ngày PV ưu tiên (trong 3 ngày)
  4. Mức lương mong muốn
  5. Ngày bắt đầu làm việc
  6. Ghi chú thêm

## 📂 Cấu Trúc Module

```
store_recruitment_process/
├── __manifest__.py
├── __init__.py
├── models/
│   ├── __init__.py
│   ├── interview_schedule.py      # Lịch PV (3 dates/week)
│   ├── hr_applicant.py            # Extend ứng viên
│   ├── hr_department.py           # Thêm is_store flag
│   └── survey_survey.py           # Thêm is_pre_interview flag
├── views/
│   ├── interview_schedule_views.xml  # Kanban, Form, List
│   ├── hr_applicant_views.xml        # Extend form
│   └── menus.xml                     # Menu mới
├── data/
│   ├── email_template.xml         # Email mời PV
│   └── survey_template.xml        # Survey mẫu
├── security/
│   └── ir.model.access.csv
└── README.md
```

## 🚀 Cài Đặt

### Bước 1: Activate Module
1. Vào **Apps** > **Update App List**
2. Search: `store` hoặc `Quy Trình Tuyển Dụng`
3. Click **Activate**

### Bước 2: Cấu Hình Departments
1. Vào **Employees > Configuration > Departments**
2. Tìm departments là cửa hàng
3. Tick checkbox **"Là Cửa Hàng"**

### Bước 3: Tạo Lịch Phỏng Vấn (Store Manager)
1. Vào **Recruitment > Lịch phỏng vấn dự kiến**
2. Click **Create**
3. Chọn:
   - Cửa hàng
   - Tuần (Thứ Hai)
   - 3 ngày PV
4. Click **Xác Nhận**

### Bước 4: Gửi Thư Mời (HR)
1. Vào **Recruitment > Applications**
2. Mở ứng viên
3. Chọn:
   - Cửa Hàng (auto-load schedule if available)
   - Lịch PV (nếu chưa auto-load)
   - Khảo Sát (chọn "Khảo Sát Trước Phỏng Vấn")
4. Click **"Gửi Thư Mời Phỏng Vấn"**

## 📧 Email Template

Email được gửi sẽ có:
- **Header** đẹp với logo/tên công ty
- **3 slots phỏng vấn** hiển thị rõ ràng
- **CTA button** lớn để điền khảo sát
- **Thông tin cửa hàng** (địa chỉ, SĐT)
- **Footer** professional

## 📊 Survey Workflow

```
Ứng viên nhận email
    ↓
Click "ĐIỀN KHẢO SÁT NGAY"
    ↓
Trả lời 6 câu hỏi
    ↓
Submit
    ↓
HR xem kết quả trong Survey module
```

## 🔐 Phân Quyền

| Nhóm | Quyền |
|------|-------|
| Base User | Xem lịch PV |
| HR Officer | Xem, Sửa, Tạo lịch |
| HR Manager | Full quyền |

## 🐛 Troubleshooting

### Lỗi: "Cửa hàng chưa có lịch PV tuần này"
**Giải pháp:** Store Manager cần tạo lịch cho tuần hiện tại và click "Xác Nhận"

### Lỗi: Email không gửi
**Kiểm tra:**
1. SMTP đã cấu hình? (Settings > Technical > Outgoing Mail Servers)
2. Ứng viên có email chưa?
3. Email template tồn tại chưa?

### Không thấy menu "Lịch phỏng vấn dự kiến"
**Giải pháp:** 
- Update module: Apps > search module > Upgrade
- Clear cache browser

## 🔄 Workflow Tổng Quát

```
┌─────────────────────────────────────────────┐
│ Store Manager: Tạo lịch PV (3 ngày/tuần)   │
└─────────────────┬───────────────────────────┘
                  │
                  ↓
┌─────────────────────────────────────────────┐
│ HR: Chọn ứng viên + Store + Survey          │
└─────────────────┬───────────────────────────┘
                  │
                  ↓
┌─────────────────────────────────────────────┐
│ System: Gửi email (3 ngày + survey link)    │
└─────────────────┬───────────────────────────┘
                  │
                  ↓
┌─────────────────────────────────────────────┐
│ Ứng viên: Nhận email → Điền survey          │
└─────────────────┬───────────────────────────┘
                  │
                  ↓
┌─────────────────────────────────────────────┐
│ HR: Xem kết quả survey → Schedule PV        │
└─────────────────────────────────────────────┘
```

## 🎨 Screenshots (Conceptual)

### Kanban View - Lịch Các Cửa Hàng
```
┌──────────────────┐  ┌──────────────────┐
│ 🏪 Store Vincom  │  │ 🏪 Store Aeon    │
│ Tuần: 13-19/01   │  │ Tuần: 13-19/01   │
│                  │  │                  │
│ 📅 14/01 9:00 AM │  │ 📅 14/01 2:00 PM │
│ 📅 16/01 2:00 PM │  │ 📅 15/01 10:00AM │
│ 📅 18/01 10:00AM │  │ 📅 17/01 3:00 PM │
│                  │  │                  │
│ 👥 5 ứng viên    │  │ 👥 3 ứng viên    │
└──────────────────┘  └──────────────────┘
```

## 📝 Notes

- Module này là **Phase 1** của quy trình tuyển dụng lớn hơn
- Các phases tiếp theo sẽ được thêm vào sau
- Liên hệ Dev team để customize thêm

## 📞 Liên Hệ

**Technical Support:** IT Team  
**Process Questions:** HR Manager  
**Module Version:** 1.0
