# SC_0405 Purchase Extend - Receiving Barcode

## Mô Tả
Module này gộp chức năng của 2 module cũ:
- `purchase_barcode_scanner`: Quét mã phiếu nhận hàng (WH/IN/00001) để mở Stock Picking
- `stock_picking_product_filter`: Quét mã sản phẩm trong Stock Picking để lọc operations

## Tính Năng

### 1. Quét Mã Phiếu Nhận Hàng
- Từ màn hình Purchase Order list, có button "Scan Receipt"
- Quét/nhập mã barcode của phiếu nhận (ví dụ: WH/IN/00001)
- Tự động mở form Stock Picking tương ứng

### 2. Quét Mã Sản Phẩm Để Lọc
- Trong form Stock Picking, có button "Scan Product"
- Quét/nhập barcode sản phẩm
- Tự động lọc và chỉ hiển thị dòng sản phẩm đã quét
- Button "Show All" để hiện lại tất cả sản phẩm

## Cài Đặt

1. Copy module vào thư mục addons của Odoo
2. Update Apps List trong Odoo
3. Tìm và Install module "SC_0405 Purchase Extend - Receiving Barcode"

## Gỡ Bỏ Module Cũ

Sau khi cài đặt module này, bạn CÓ THỂ gỡ 2 module cũ:
1. `purchase_barcode_scanner`
2. `stock_picking_product_filter`

**Lưu ý:** Module này thay thế hoàn toàn 2 module trên. Không có breaking changes về dữ liệu vì không có model riêng, chỉ extend `stock.picking`.

## Dependencies
- `purchase`: Module Purchase cơ bản của Odoo
- `stock`: Module Inventory/Stock cơ bản của Odoo
- `barcodes`: Module Barcode scanner của Odoo

## Cấu Trúc Module

```
SC_0405_purchase_extend/
├── __init__.py
├── __manifest__.py
├── models/
│   ├── __init__.py
│   └── stock_picking.py          # Gộp từ cả 2 module cũ
├── views/
│   └── receiving_views.xml       # Gộp từ cả 2 module cũ
└── static/
    └── src/
        ├── js/
        │   └── receiving_barcode.js    # Gộp từ cả 2 module cũ
        ├── xml/
        │   └── receiving_barcode.xml   # Template cho button
        └── scss/
            └── receiving_barcode.scss  # Styling cho button
```

## Hướng Dẫn Sử Dụng

### Test 1: Quét Mã Phiếu Nhận Hàng
1. Mở Odoo → Purchase → Orders
2. Tạo Purchase Order mới, Confirm → sẽ có Stock Picking (WH/IN/xxxxx)
3. Quay lại Purchase Order list view
4. Click "Scan Receipt" hoặc dùng súng quét
5. Nhập mã WH/IN/xxxxx
6. → Mở form Stock Picking tương ứng

### Test 2: Quét Mã Sản Phẩm
1. Mở Stock Picking (từ Test 1)
2. Tab Operations có nhiều dòng sản phẩm
3. Click "Scan Product"
4. Nhập/quét barcode của 1 sản phẩm
5. → Chỉ hiển thị dòng sản phẩm đó
6. Click "Show All" → Hiện lại tất cả

## License
LGPL-3

## Tác Giả
Merged from original modules: purchase_barcode_scanner + stock_picking_product_filter
