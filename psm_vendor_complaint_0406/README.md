# SC_0406 Stock Vendor Complaint

## Mô Tả
Module xử lý hàng thiếu, thừa, kém chất lượng phát sinh từ quy trình nhận hàng (SC_0405).

## Thay Đổi So Với `stock_vendor_claim` Cũ

### 1. **Đổi Tên Module**
- Tên cũ: `stock_vendor_claim`
- Tên mới: `SC_0406_stock_vendor_complaint`
- Phù hợp với convention đặt tên: SC_xxxx

### 2. **Di Chuyển QIP Status**
- Field `qip_status` đã được chuyển sang module `SC_0405_purchase_extend`
- Lý do: QIP thuộc Bước 3 của quy trình nhận hàng (SC_0405), không thuộc quy trình complaint
- Module này chỉ đọc `qip_status` để tạo claim, không định nghĩa field

### 3. **Sửa Logic Deadline 48h**
- **Cũ:** Deadline = Thời điểm FSC approve + 48h
- **Mới:** Deadline = Thời điểm tạo claim + 48h (đúng nghiệp vụ)

### 4. **Dependencies**
- Thêm dependency: `SC_0405_purchase_extend`
- Phải install SC_0405 trước SC_0406

---

## Quy Trình Nghiệp Vụ SC_0406

### **4 Trường Hợp Xử Lý:**

#### **TH1: Hàng Thừa** → Auto Accept (B2 + B3)
- Tự động chấp nhận và đóng phiếu
- State: `draft` → `submitted` → `closed`

#### **TH2: Hàng Thiếu** → FSC Review → Giao bù 48h (B7 + B9 + B10)
- Chuyển FSC duyệt
- Nếu approve: Tạo backorder, deadline 48h
- State: `draft` → `submitted` → `fsc_review` → `approved/rejected`

#### **TH3: Hàng Lỗi Tỉnh** → QA Review → FSC Review (B5 + B6 + B7)
- QA xác định mức độ lỗi
- FSC chốt phương án xử lý
- State: `draft` → `submitted` → `qa_review` → `fsc_review` → `approved/rejected`

#### **TH4: Hàng Lỗi HCM/HN** → Auto Reject (B4)
- Tự động từ chối nhận hàng
- State: `draft` → `submitted` → `closed`

---

## Cài Đặt

### **Yêu Cầu:**
- Module `SC_0405_purchase_extend` phải được install trước

### **Các Bước:**

1. **Uninstall module cũ** (nếu có):
   ```
   Apps → Stock Vendor Claim → Uninstall
   ```

2. **Update Apps List:**
   ```
   Apps → Update Apps List
   ```

3. **Install SC_0405** (nếu chưa có):
   ```
   Apps → SC_0405 Purchase Extend → Install
   ```

4. **Install SC_0406:**
   ```
   Apps → SC_0406 Stock Vendor Complaint → Install
   ```

---

## Cấu Trúc Module

```
SC_0406_stock_vendor_complaint/
├── __init__.py
├── __manifest__.py
├── README.md
├── data/
│   └── sequence.xml               # Sequence cho claim reference
├── models/
│   ├── __init__.py
│   ├── stock_picking.py           # Extend picking + override button_validate
│   ├── vendor_claim.py            # Main claim model + workflow
│   └── vendor_claim_line.py       # Claim lines (products)
├── security/
│   └── ir.model.access.csv        # Access rights
├── views/
│   ├── stock_picking_views.xml    # Smart button Claims count
│   └── vendor_claim_views.xml     # Form/tree/search views
└── wizard/
    ├── __init__.py
    ├── vendor_claim_wizard.py     # Wizard khi validate picking
    └── vendor_claim_wizard_views.xml
```

**Note:** `models/stock_move.py` đã bị xóa - `qip_status` giờ được định nghĩa trong `SC_0405_purchase_extend`

---

## Workflow States

```
draft → submitted → qa_review (TH3) → fsc_review (TH2/TH3) → approved/rejected → closed
           ↓                                    ↓
        closed (TH1/TH4)                   closed (auto)
```

---

## Dependencies

- `stock`: Odoo Stock Management
- `purchase`: Odoo Purchase Management  
- `mail`: Mail tracking (chatter, activities)
- `SC_0405_purchase_extend`: **BẮT BUỘC** - Cung cấp field `qip_status`

---

## Migration Notes

### **Từ `stock_vendor_claim` → `SC_0406_stock_vendor_complaint`**

⚠️ **Warning:** Data claims cũ sẽ **MẤT** khi uninstall module cũ

**Nếu cần migrate data:**
1. Export claims hiện có (CSV/Excel)
2. Uninstall `stock_vendor_claim`
3. Install `SC_0406_stock_vendor_complaint`
4. Import lại data (nếu cần)

**Nếu không cần data cũ:**
1. Uninstall `stock_vendor_claim`
2. Install `SC_0406_stock_vendor_complaint`

---

## License
LGPL-3

## Author
Refactored from original `stock_vendor_claim` module
