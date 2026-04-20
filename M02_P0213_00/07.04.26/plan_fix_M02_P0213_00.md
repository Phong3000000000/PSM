# Kế hoạch thực hiện fix review `M02_P0213_00`

**Nguồn tham chiếu**: `code_review_M02_P0213_00.md`  
**Phạm vi**: Dựa trên phần 3 `Vi phạm Odoo Standard & GDH Principle` và phần 4 `Warnings`  
**Mục tiêu**: Chuẩn bị checklist triển khai fix các điểm reviewer đã nêu, ưu tiên xử lý an toàn, đúng chuẩn Odoo và hạn chế phát sinh regression.

---

## 1. Mục tiêu thực hiện

- Loại bỏ các điểm vi phạm chuẩn Odoo/GDH trong logic hiện tại.
- Chuẩn hóa cách truy cập dữ liệu theo ORM thay cho raw SQL.
- Giảm rủi ro logic dễ vỡ do hardcode tên hiển thị.
- Dọn các code smell và warning còn lại để code dễ bảo trì hơn.
- Chuẩn bị sẵn tiêu chí kiểm tra sau khi fix.

---

## 2. Danh sách hạng mục cần fix

| Mức độ | Mã lỗi | Nội dung | Ưu tiên |
|---|---|---|---|
| Critical | CRITICAL-01 | Raw SQL trong compute field | P0 |
| Critical | CRITICAL-02 | Hardcode category name để so sánh logic | P0 |
| Warning | WARNING-01 | Duplicate `ensure_one()` | P1 |
| Warning | WARNING-02 | Dùng `hasattr()` dư thừa với field chuẩn Odoo | P1 |
| Warning | WARNING-03 | N+1 pattern tiềm ẩn trong cron | P2 |
| Warning | WARNING-04 | `_logger.info()` mang tính debug trong production | P2 |

---

## 3. Kế hoạch fix chi tiết

### 3.1. CRITICAL-01 - Thay raw SQL bằng ORM

**Hiện trạng**
- Có đoạn dùng `self.env.cr.execute(...)` để lấy `mail.activity`.
- Cách làm này bypass ORM, có thể bỏ qua record rules và không đúng chuẩn NL-24.

**Mục tiêu fix**
- Chuyển toàn bộ logic truy vấn hoạt động liên quan sang ORM Odoo.
- Giữ nguyên kết quả nghiệp vụ hiện tại, bao gồm trường hợp cần đọc bản ghi inactive.

**Hướng thực hiện**
- Xác định compute field hoặc method đang dùng raw SQL.
- Thay bằng:
  - `self.env["mail.activity"].sudo().with_context(active_test=False).search(...)`
- Dùng domain với toán tử `|` và `&` để thay thế điều kiện SQL hiện tại.
- Gán trực tiếp recordset vào field đích thay vì lấy danh sách ID từ cursor.

**Điểm cần kiểm tra sau fix**
- Danh sách activity trả về vẫn đúng cho:
  - `approval.request`
  - `hr.employee`
- Trường hợp activity inactive vẫn đọc được nếu nghiệp vụ yêu cầu.
- Không phát sinh lỗi quyền truy cập khi user thường mở màn hình liên quan.
- Không còn `self.env.cr.execute` trong đoạn logic này.

**Kết quả mong đợi**
- Đúng chuẩn ORM.
- Giảm rủi ro bảo mật và dễ maintain hơn.

---

### 3.2. CRITICAL-02 - Bỏ so sánh bằng tên category hardcode

**Hiện trạng**
- Logic đang dùng kiểu:
  - `request.category_id.name == "Yêu cầu nghỉ việc "`
- Có phụ thuộc vào tên hiển thị và còn có nguy cơ sai do khoảng trắng cuối chuỗi.

**Mục tiêu fix**
- Chuyển sang nhận diện category bằng XML ID cố định.
- Tránh tình trạng đổi tên category làm vỡ luồng nghiệp vụ.

**Hướng thực hiện**
- Tạo helper dùng chung, ví dụ `_get_resignation_category()` hoặc tương đương.
- Trong helper:
  - dùng `self.env.ref("M02_P0213_00.psm_0213_approval_category_resignation", raise_if_not_found=False)`
- Các chỗ đang so sánh bằng `category_id.name` sẽ đổi sang:
  - so sánh record `request.category_id == resign_cat`
- Rà soát đặc biệt các luồng:
  - `action_withdraw()`
  - `action_cancel()`
  - các method khác nếu có dùng lại cùng logic

**Điểm cần kiểm tra sau fix**
- User vẫn rút đơn/hủy đơn đúng theo rule nghiệp vụ.
- Nếu admin đổi tên category hiển thị, logic vẫn chạy đúng.
- Nếu XML ID không tồn tại, code không crash ngoài ý muốn.

**Kết quả mong đợi**
- Logic ổn định hơn.
- Không phụ thuộc vào tên hiển thị do người dùng chỉnh sửa.

---

### 3.3. WARNING-01 - Xóa duplicate `ensure_one()`

**Hiện trạng**
- Có method gọi `self.ensure_one()` hai lần liên tiếp.

**Mục tiêu fix**
- Giữ lại một lần gọi duy nhất ở đúng vị trí cần thiết.

**Hướng thực hiện**
- Xóa lệnh `ensure_one()` dư thừa.
- Đọc lại toàn method để chắc chắn không có refactor dở dang.

**Điểm cần kiểm tra sau fix**
- Method vẫn chạy bình thường với 1 record.
- Không ảnh hưởng exception khi truyền nhiều record.

---

### 3.4. WARNING-02 - Bỏ `hasattr()` không cần thiết trên field chuẩn

**Hiện trạng**
- Code kiểm tra `hasattr(employee, "contract_id")` và `hasattr(contract, "contract_type_id")`.
- Với module đã phụ thuộc `hr`, các field chuẩn này được xem là có sẵn.

**Mục tiêu fix**
- Đơn giản hóa code, đọc dễ hơn và đúng với giả định chuẩn của module.

**Hướng thực hiện**
- Truy cập trực tiếp:
  - `contract = employee.sudo().contract_id`
  - sau đó kiểm tra `if contract and contract.contract_type_id`
- Chỉ giữ lại các điều kiện thật sự cần cho null/empty.

**Điểm cần kiểm tra sau fix**
- Không lỗi với nhân viên chưa có hợp đồng.
- Không lỗi với hợp đồng chưa có `contract_type_id`.
- Kết quả hiển thị hoặc mapping dữ liệu không thay đổi ngoài mong đợi.

---

### 3.5. WARNING-03 - Tối ưu cron tránh N+1 query

**Hiện trạng**
- Trong vòng lặp từng request lại search activity riêng.
- Sau đó tiếp tục filter nhiều lần theo user và gửi mail từng lượt.

**Mục tiêu fix**
- Giảm số lượng query và giảm chi phí xử lý khi số lượng request tăng.

**Hướng thực hiện**
- Đọc lại cron hiện tại để xác định:
  - input request
  - domain activity
  - cách gom user nhận nhắc việc
- Chuyển từ pattern:
  - lặp từng request rồi `search(...)`
- Sang pattern:
  - search tất cả overdue activities một lần
  - group theo `res_model`, `res_id` hoặc khóa nghiệp vụ phù hợp
  - map sang từng request trong bộ nhớ
- Xem xét gom email theo user hoặc theo request nếu nghiệp vụ cho phép.

**Điểm cần kiểm tra sau fix**
- Số lượng email gửi ra không bị thiếu hoặc bị lặp.
- Cron vẫn chỉ nhắc các activity overdue đúng điều kiện.
- Thời gian chạy cải thiện khi số lượng request lớn.

**Ghi chú**
- Đây là hạng mục tối ưu hiệu năng, nên cần test kỹ để tránh đổi hành vi nghiệp vụ.

---

### 3.6. WARNING-04 - Hạ mức hoặc xóa log debug-style

**Hiện trạng**
- Có `_logger.info()` dùng để in chi tiết activity IDs trong production code.

**Mục tiêu fix**
- Tránh làm log production bị nhiễu.

**Hướng thực hiện**
- Đổi sang `_logger.debug()` nếu thông tin vẫn hữu ích cho debug.
- Nếu không còn cần thiết, xóa hẳn log.

**Điểm cần kiểm tra sau fix**
- Không mất log nghiệp vụ quan trọng.
- Log file production bớt thông tin kỹ thuật dư thừa.

---

## 4. Thứ tự triển khai đề xuất

1. Fix `CRITICAL-01` vì liên quan chuẩn ORM và rủi ro bảo mật.
2. Fix `CRITICAL-02` vì ảnh hưởng trực tiếp đến logic nghiệp vụ rút/hủy đơn.
3. Fix `WARNING-01` và `WARNING-02` để làm sạch code nhanh, ít rủi ro.
4. Fix `WARNING-04` để dọn log production.
5. Thực hiện `WARNING-03` sau cùng vì là hạng mục tối ưu, cần test kỹ hơn.

---

## 5. Checklist kiểm tra sau khi hoàn tất

- Không còn raw SQL trong phần logic reviewer đã nêu.
- Không còn so sánh category bằng tên hiển thị hardcode.
- Không còn duplicate `ensure_one()`.
- Không còn `hasattr()` thừa với field chuẩn trong đoạn liên quan.
- Log debug-style đã được hạ mức hoặc loại bỏ.
- Cron reminder vẫn gửi đúng đối tượng, đúng điều kiện.
- Kiểm tra regression cho các luồng chính:
  - tạo đơn nghỉ việc
  - duyệt đơn
  - rút đơn
  - hủy đơn
  - offboarding activity
  - portal activity done

---

## 6. Ước lượng sơ bộ

| Hạng mục | Ước lượng |
|---|---|
| CRITICAL-01 | 10-20 phút |
| CRITICAL-02 | 10-20 phút |
| WARNING-01 | 5 phút |
| WARNING-02 | 5-10 phút |
| WARNING-03 | 20-40 phút |
| WARNING-04 | 5 phút |

---

## 7. Kết quả đầu ra mong muốn

- 1 bản code đã fix theo chuẩn reviewer yêu cầu.
- 1 vòng self-test cho các luồng chính.
- 1 bản note ngắn tổng hợp:
  - mục nào đã fix
  - mục nào deferred
  - rủi ro còn lại nếu chưa tối ưu cron
