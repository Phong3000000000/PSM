# 🛡️ Code Review Report — `M02_P0213_00`
**Module**: Quy trình Nghỉ việc (Offboarding / Resignation)  
**Process Code**: M02_P0213_00  
**Reviewed by**: MASTER_REVIEWER (GDH Standards Odoo 19 EE)  
**Date**: 2026-04-07

---

## 1. KẾT LUẬN TỔNG QUAN

## 🟢 PASS (After Refactor) — 5/6 Defects Fixed

| Severity | Count | Status |
|----------|-------|--------|
| 🔴 CRITICAL | 2 | ✅ FIXED |
| 🟡 WARNING | 3 of 4 | ✅ FIXED (1 deferred P2) |
| 🟢 GOOD | 8 | Confirmed |

---

## 2. CODE INVENTORY MATRIX

| Asset | Inherit | New | Files |
|-------|---------|-----|-------|
| Models | 3 (`approval.request`, `approval.category`, `mail.activity`, `survey.user_input`) | 0 | 3 |
| Fields | 0 | 17 (all `x_psm_0213_*`) | — |
| Views | 2 (xpath inherit) | 1 (portal template) | 2 |
| Controllers | 0 | 1 (`PortalResignation`) | 1 |
| Cron | 0 | 1 | 1 |
| Data | 0 | 9 (survey, emails, plan) | 9 |
| Security | ACL + 1 Record Rule | ✅ | 2 |

---

## 3. VI PHẠM ODOO STANDARD & GDH PRINCIPLE

### 🔴 CRITICAL-01: Raw SQL dùng trong compute field — Vi phạm NL-24 (ORM Strict)

[resignation_request.py:383-391](file:///c:/Users/DELL/OneDrive/Desktop/AI/GOOD%20DAY/05.%20Development%20&%20Code/Sample/M02_P0213_00/models/resignation_request.py#L383-L391)

```python
# ❌ HIỆN TẠI — Raw SQL trong compute field
self.env.cr.execute("""
    SELECT id FROM mail_activity
    WHERE (res_model = 'approval.request' AND res_id = %s)
       OR (res_model = 'hr.employee' AND res_id = %s)
""", (request.id, request.x_psm_0213_employee_id.id))
activity_ids = [r[0] for r in self.env.cr.fetchall()]
```

**Vi phạm**: NL-24 cấm tuyệt đối Raw SQL khi ORM có thể làm được. Lý do DEV bypass ORM có thể do `active_test=False` context không hoạt động — nhưng cách đúng là:

```python
# ✅ ĐỀ XUẤT — ORM với with_context
ActivitySudo = self.env["mail.activity"].sudo().with_context(active_test=False)
activities = ActivitySudo.search([
    '|',
    '&', ('res_model', '=', 'approval.request'), ('res_id', '=', request.id),
    '&', ('res_model', '=', 'hr.employee'), ('res_id', '=', request.x_psm_0213_employee_id.id),
])
request.x_psm_0213_employee_activity_ids = activities
```

> [!WARNING]
> raw SQL bypass hoàn toàn Record Rules, trả về IDs mà user hiện tại có thể không có quyền truy cập. Đây là lỗ hổng bảo mật tiềm ẩn.

---

### 🔴 CRITICAL-02: Hardcode category name string matching — Dễ vỡ

[resignation_request.py:128,144](file:///c:/Users/DELL/OneDrive/Desktop/AI/GOOD%20DAY/05.%20Development%20&%20Code/Sample/M02_P0213_00/models/resignation_request.py#L128)

```python
# ❌ HIỆN TẠI — So sánh tên cứng (chú ý có dấu cách thừa cuối!)
if request.category_id.name == "Yêu cầu nghỉ việc ":  # ← trailing space!
```

Category name có thể bị user đổi bất cứ lúc nào. Và trailing space `" "` là bug ẩn — nếu ai đó trim tên category, logic sẽ vỡ.

```python
# ✅ ĐỀ XUẤT — So sánh bằng XML ID (không bao giờ thay đổi)
resign_cat = self.env.ref(
    "M02_P0213_00.psm_0213_approval_category_resignation",
    raise_if_not_found=False,
)
if resign_cat and request.category_id == resign_cat:
```

> [!CAUTION]
> Đặc biệt nguy hiểm vì `action_withdraw()` và `action_cancel()` dùng logic này — nếu tên bị đổi, user có thể rút/hủy đơn đã duyệt.

---

## 4. WARNINGS

### 🟡 WARNING-01: Duplicate `ensure_one()` — Code smell

[resignation_request.py:512-513](file:///c:/Users/DELL/OneDrive/Desktop/AI/GOOD%20DAY/05.%20Development%20&%20Code/Sample/M02_P0213_00/models/resignation_request.py#L512-L513)

```python
# ❌ Gọi ensure_one() 2 lần liên tiếp
self.ensure_one()
self.ensure_one()  # redundant
```

---

### 🟡 WARNING-02: Excessive `hasattr()` checks on standard Odoo fields

[resignation_request.py:196-206](file:///c:/Users/DELL/OneDrive/Desktop/AI/GOOD%20DAY/05.%20Development%20&%20Code/Sample/M02_P0213_00/models/resignation_request.py#L196-L206)

```python
# ❌ contract_id và contract_type_id là standard fields — không cần hasattr
if hasattr(employee, "contract_id") and employee.contract_id:
    if hasattr(employee.contract_id.sudo(), "contract_type_id"):
        contract_type = employee.contract_id.sudo().contract_type_id
```

Module đã `depends: ['hr']` nên `contract_id` chắc chắn tồn tại. Simplified:

```python
# ✅ Truy cập trực tiếp
contract = employee.sudo().contract_id
if contract and contract.contract_type_id:
    contract_name = contract.contract_type_id.name
```

---

### 🟡 WARNING-03: N+1 Pattern tiềm ẩn trong Cron

[resignation_request.py:719-760](file:///c:/Users/DELL/OneDrive/Desktop/AI/GOOD%20DAY/05.%20Development%20&%20Code/Sample/M02_P0213_00/models/resignation_request.py#L719-L760)

```python
for req in requests:  # N requests
    pending_activities = self.env["mail.activity"].sudo().search([...])  # N queries
    for user in users_to_remind:  # M users  
        user_acts = pending_activities.filtered(...)  # Lặp filter
        template.send_mail(...)  # N*M emails
```

Khi có 50 đơn approved × 3 users mỗi đơn = 150 email calls + 50 separate search queries. Nên batch:

```python
# ✅ Batch search tất cả overdue activities 1 lần
all_overdue = self.env["mail.activity"].sudo().search([
    ('active', '=', True),
    ('date_deadline', '<', today),
    ('res_model', 'in', ['approval.request', 'hr.employee']),
])
# Rồi group by res_id
```

---

### 🟡 WARNING-04: Debug `_logger.info()` còn sót trong production code

[resignation_request.py:367-369](file:///c:/Users/DELL/OneDrive/Desktop/AI/GOOD%20DAY/05.%20Development%20&%20Code/Sample/M02_P0213_00/models/resignation_request.py#L367-L369)

```python
# ❌ Logging level quá cao cho production
_logger.info(
    f"OWNER ACTIVITIES: Employee ID={request.x_psm_0213_employee_id.id}, Found {len(activity_ids)} activity IDs: {activity_ids}"
)
```

Nên đổi thành `_logger.debug()` hoặc xóa. `info` level sẽ flood log file trên production.

---

## 5. SECURITY & PERFORMANCE AUDIT

### 🔒 SEC-01: Portal Controller — IDOR partially mitigated ✅

[controllers/main.py:130-134](file:///c:/Users/DELL/OneDrive/Desktop/AI/GOOD%20DAY/05.%20Development%20&%20Code/Sample/M02_P0213_00/controllers/main.py#L130-L134)

```python
# ✅ Đúng chuẩn: Chỉ cho phép owner mark activity done
owned_request = self._get_owned_resignation_request_by_id(activity.res_id)
if owned_request and activity.user_id == request.env.user:
    activity.sudo().action_feedback(...)
```

Đã filter đúng: (1) đơn thuộc user hiện tại, (2) activity assigned cho user hiện tại.

### 🔒 SEC-02: Record Rule cho Survey — ✅ Đúng chuẩn

```xml
<!-- Portal user chỉ xem survey.user_input của chính mình -->
<field name="domain_force">['|', ('partner_id', '=', user.partner_id.id), ('email', '=', user.email)]</field>
```

### 🔒 SEC-03: Deactivate user — ✅ Safe guard cho Admin

```python
# Không vô hiệu hóa system admin
if not user_to_deactivate.has_group('base.group_system'):
    user_to_deactivate.write({'active': False})
```

### ⚡ PERF-01: `_compute_exit_survey_completed` — trong loop nhưng search nằm ngoài ✅ (đúng pattern)

### ⚡ PERF-02: Cron activity search — Warning (xem WARNING-03)

---

## 6. ĐIỂM TỐT (BEST PRACTICES ĐÃ TUÂN THỦ) ✅

| # | Best Practice | Áp dụng tại |
|---|--------------|-------------|
| 1 | **Inherit-First** — Mở rộng `approval.request` thay vì tạo model mới | Toàn module |
| 2 | **`x_psm_0213_` prefix** — Naming convention nhất quán cho tất cả 17 fields | Toàn module |
| 3 | **`super()` chain** — Mọi override đều gọi super() đúng chuẩn | `action_approve`, `action_withdraw`, `action_cancel`, `write`, `unlink`, `_action_done` |
| 4 | **Portal CSRF** — Tất cả POST routes có `csrf=True` | `controllers/main.py` |
| 5 | **IDOR Protection** — Portal activities kiểm tra ownership trước khi mark done | `portal_activity_done()` |
| 6 | **`list` mode** — Dùng `<list>` thay vì deprecated `<tree>` | `resignation_request_views.xml:89` |
| 7 | **Activity Plan Architecture** — Dùng `mail.activity.plan` chuẩn Odoo thay vì custom cron | `offboarding_activity_plan_data.xml` |
| 8 | **`raise_if_not_found=False`** — An toàn khi ref XML ID | Mọi `self.env.ref()` |

---

## 7. TỔNG KẾT HÀNH ĐỘNG

| Priority | Action | Effort | Status |
|----------|--------|--------|--------|
| 🔴 P0 | Thay Raw SQL bằng ORM `with_context(active_test=False)` | ~10 phút | ✅ DONE |
| 🔴 P0 | Thay string match `"Yêu cầu nghỉ việc "` bằng `_get_resignation_category()` helper | ~10 phút | ✅ DONE |
| 🟡 P1 | Xóa duplicate `ensure_one()` | ~1 phút | ✅ DONE |
| 🟡 P1 | Bỏ `hasattr()` thừa, truy cập trực tiếp standard fields | ~5 phút | ✅ DONE |
| 🟡 P2 | Batch cron activity search để tránh N+1 | ~20 phút | ⏳ Deferred |
| 🟡 P2 | Đổi `_logger.info` → `_logger.debug` | ~1 phút | ✅ DONE |
