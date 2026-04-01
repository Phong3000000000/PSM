/** @odoo-module **/

import publicWidget from "@web/legacy/js/public/public_widget";

// Hàm gọi API thủ công (Bất tử trên mọi phiên bản Odoo 17, 18, 19)
async function callOdooRpc(route, params) {
    const response = await fetch(route, {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
        body: JSON.stringify({
            jsonrpc: "2.0",
            method: "call",
            params: params,
            id: Date.now(),
        }),
    });
    const result = await response.json();

    if (result.error) {
        throw result.error;
    }
    return result.result;
}

// 1. Widget ĐĂNG KÝ (slot có sẵn)
publicWidget.registry.ShiftRegister = publicWidget.Widget.extend({
    selector: '.js_register_shift',
    events: {
        'click': '_onRegisterClick',
    },

    start: function () {
        console.log("🚀 Odoo 19: Shift Register Widget Loaded!");
        return this._super.apply(this, arguments);
    },

    async _onRegisterClick(ev) {
        ev.preventDefault();
        const $btn = $(ev.currentTarget);
        const slotId = $btn.data('slot-id');

        if (!confirm("Bạn có chắc chắn muốn đăng ký ca này?")) return;

        // Khóa nút
        $btn.prop('disabled', true);
        const originalHtml = $btn.html();
        $btn.html('<i class="fa fa-spinner fa-spin"></i> Đang xử lý...');

        try {
            // Gọi API bằng hàm thủ công ở trên
            const result = await callOdooRpc("/my/shifts/register", {
                slot_id: parseInt(slotId),
            });

            if (result.success) {
                $btn.removeClass('btn-outline-primary').addClass('btn-success');
                $btn.html('<i class="fa fa-check"></i> Thành công!');
                window.location.reload();
            } else {
                alert("⚠️ Lỗi: " + (result.error || "Không xác định"));
                $btn.prop('disabled', false).html(originalHtml);
            }
        } catch (error) {
            console.error("RPC Error:", error);
            // Lấy message lỗi chi tiết từ Odoo nếu có
            const msg = error.data ? error.data.message : "Lỗi kết nối Server!";
            alert("❌ " + msg);
            $btn.prop('disabled', false).html(originalHtml);
        }
    }
});

// 2. Widget ĐĂNG KÝ MỚI (tạo slot mới khi chưa có)
publicWidget.registry.ShiftRegisterNew = publicWidget.Widget.extend({
    selector: '.js_register_new_shift',
    events: {
        'click': '_onRegisterNewClick',
    },

    start: function () {
        console.log("🚀 Odoo 19: Shift Register New Widget Loaded!");
        return this._super.apply(this, arguments);
    },

    async _onRegisterNewClick(ev) {
        ev.preventDefault();
        const $btn = $(ev.currentTarget);
        const roleId = $btn.data('role-id');
        const dateStr = $btn.data('date');
        const templateId = $btn.data('template-id');
        const storeId = $btn.data('store-id');
        const slotId = $btn.data('slot-id');

        if (!roleId || !dateStr || !templateId) {
            alert("❌ Thiếu thông tin đăng ký!");
            return;
        }

        if (!confirm("Bạn có chắc chắn muốn đăng ký ca này?")) return;

        // Khóa nút
        $btn.prop('disabled', true);
        const originalHtml = $btn.html();
        $btn.html('<i class="fa fa-spinner fa-spin"></i> Đang xử lý...');

        try {
            // Nếu có slot_id thì đăng ký vào slot có sẵn, không thì tạo mới
            let result;
            if (slotId && slotId > 0) {
                result = await callOdooRpc("/my/shifts/register", {
                    slot_id: parseInt(slotId),
                });
            } else {
                result = await callOdooRpc("/my/shifts/register-new", {
                    role_id: parseInt(roleId),
                    date_str: dateStr,
                    template_id: parseInt(templateId),
                    store_id: storeId ? parseInt(storeId) : false,
                });
            }

            if (result.success) {
                $btn.removeClass('btn-register').addClass('btn-success');
                $btn.html('<i class="fa fa-check"></i> Thành công!');
                setTimeout(function () {
                    window.location.reload();
                }, 500);
            } else {
                alert("⚠️ Lỗi: " + (result.error || "Không xác định"));
                $btn.prop('disabled', false).html(originalHtml);
            }
        } catch (error) {
            console.error("RPC Error:", error);
            const msg = error.data ? error.data.message : "Lỗi kết nối Server!";
            alert("❌ " + msg);
            $btn.prop('disabled', false).html(originalHtml);
        }
    }
});

// 3. Widget HỦY ĐĂNG KÝ
publicWidget.registry.ShiftUnregister = publicWidget.Widget.extend({
    selector: '.js_unregister_shift',
    events: {
        'click': '_onUnregisterClick',
    },

    async _onUnregisterClick(ev) {
        ev.preventDefault();
        const $btn = $(ev.currentTarget);
        const slotId = $btn.data('slot-id');

        if (!slotId || slotId == 0) {
            alert("❌ Không tìm thấy ca làm việc!");
            return;
        }

        if (!confirm("Bạn muốn HỦY đăng ký ca này?")) return;

        $btn.prop('disabled', true);
        const originalHtml = $btn.html();
        $btn.html('<i class="fa fa-spinner fa-spin"></i>');

        try {
            const result = await callOdooRpc("/my/shifts/unregister", {
                slot_id: parseInt(slotId),
            });

            if (result.success) {
                window.location.reload();
            } else {
                alert("⚠️ " + result.error);
                $btn.prop('disabled', false).html(originalHtml);
            }
        } catch (error) {
            console.error(error);
            const msg = error.data ? error.data.message : "Lỗi kết nối!";
            alert("❌ " + msg);
            $btn.prop('disabled', false).html(originalHtml);
        }
    }
});

// 4. Widget DUYỆT CA (cho Line Manager Portal)
publicWidget.registry.ShiftApprove = publicWidget.Widget.extend({
    selector: '.js_portal_approve',
    events: {
        'click': '_onApproveClick',
    },

    start: function () {
        console.log("🚀 Odoo 19: Portal Approve Widget Loaded!");
        return this._super.apply(this, arguments);
    },

    async _onApproveClick(ev) {
        ev.preventDefault();
        const $btn = $(ev.currentTarget);
        const slotId = $btn.data('slot-id');

        if (!slotId) {
            alert("❌ Không tìm thấy ca làm việc!");
            return;
        }

        if (!confirm("Xác nhận DUYỆT ca này?")) return;

        $btn.prop('disabled', true);
        const originalHtml = $btn.html();
        $btn.html('<i class="fa fa-spinner fa-spin"></i> Đang xử lý...');

        try {
            const result = await callOdooRpc("/my/team/approve", {
                slot_id: parseInt(slotId),
            });

            if (result.success) {
                $btn.removeClass('btn-approve').addClass('btn-success');
                $btn.html('<i class="fa fa-check"></i> Đã duyệt');
                // Ẩn nút từ chối
                $btn.siblings('.js_portal_reject').hide();
                setTimeout(function () {
                    window.location.reload();
                }, 800);
            } else {
                alert("⚠️ " + (result.error || "Không xác định"));
                $btn.prop('disabled', false).html(originalHtml);
            }
        } catch (error) {
            console.error("RPC Error:", error);
            const msg = error.data ? error.data.message : "Lỗi kết nối Server!";
            alert("❌ " + msg);
            $btn.prop('disabled', false).html(originalHtml);
        }
    }
});

// 5. Widget TỪ CHỐI CA (cho Line Manager Portal)
publicWidget.registry.ShiftReject = publicWidget.Widget.extend({
    selector: '.js_portal_reject',
    events: {
        'click': '_onRejectClick',
    },

    async _onRejectClick(ev) {
        ev.preventDefault();
        const $btn = $(ev.currentTarget);
        const slotId = $btn.data('slot-id');

        if (!slotId) {
            alert("❌ Không tìm thấy ca làm việc!");
            return;
        }

        const reason = prompt("Nhập lý do từ chối (bỏ trống nếu không có):");
        if (reason === null) return; // User cancelled

        $btn.prop('disabled', true);
        const originalHtml = $btn.html();
        $btn.html('<i class="fa fa-spinner fa-spin"></i>');

        try {
            const result = await callOdooRpc("/my/team/reject", {
                slot_id: parseInt(slotId),
                reason: reason || "Không phù hợp",
            });

            if (result.success) {
                $btn.removeClass('btn-reject').addClass('btn-secondary');
                $btn.html('<i class="fa fa-times"></i> Đã từ chối');
                $btn.siblings('.js_portal_approve').hide();
                setTimeout(function () {
                    window.location.reload();
                }, 800);
            } else {
                alert("⚠️ " + (result.error || "Không xác định"));
                $btn.prop('disabled', false).html(originalHtml);
            }
        } catch (error) {
            console.error("RPC Error:", error);
            const msg = error.data ? error.data.message : "Lỗi kết nối Server!";
            alert("❌ " + msg);
            $btn.prop('disabled', false).html(originalHtml);
        }
    }
});