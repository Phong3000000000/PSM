/** @odoo-module **/

import publicWidget from "@web/legacy/js/public/public_widget";

/**
 * Helper function to make JSON RPC calls to Odoo
 */
function callOdooRpc(url, params) {
    return fetch(url, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            jsonrpc: '2.0',
            method: 'call',
            params: params,
            id: Math.floor(Math.random() * 1000000),
        }),
    }).then(function (response) {
        return response.json();
    }).then(function (data) {
        if (data.error) {
            throw new Error(data.error.data?.message || data.error.message || 'Unknown error');
        }
        return data.result;
    });
}

/**
 * Widget: Approve Shift
 */
publicWidget.registry.PortalApproveShift = publicWidget.Widget.extend({
    selector: '.js_approve_shift',
    events: {
        'click': '_onClick',
    },

    _onClick: function (ev) {
        ev.preventDefault();
        var self = this;
        var $btn = $(ev.currentTarget);
        var slotId = $btn.data('slot-id');

        if (!slotId) {
            alert('Lỗi: Không tìm thấy ID ca làm việc.');
            return;
        }

        if (!confirm('Bạn có chắc muốn duyệt ca làm việc này?')) {
            return;
        }

        // Disable button and show loading
        $btn.prop('disabled', true);
        $btn.html('<i class="fa fa-spinner fa-spin"></i>');

        callOdooRpc('/my/approvals/approve-shift', { slot_id: slotId })
            .then(function (result) {
                if (result.success) {
                    // Remove the row with animation
                    var $row = $btn.closest('tr, .shift-row');
                    $row.fadeOut(300, function () {
                        $(this).remove();
                        // Show success message
                        self._showAlert('success', result.message || 'Đã duyệt thành công!');
                    });
                } else {
                    alert(result.error || 'Có lỗi xảy ra.');
                    $btn.prop('disabled', false);
                    $btn.html('<i class="fa fa-check"></i> Duyệt');
                }
            })
            .catch(function (err) {
                alert('Lỗi: ' + err.message);
                $btn.prop('disabled', false);
                $btn.html('<i class="fa fa-check"></i> Duyệt');
            });
    },

    _showAlert: function (type, message) {
        var alertHtml = '<div class="alert alert-' + type + ' alert-dismissible fade show" role="alert">' +
            message +
            '<button type="button" class="btn-close" data-bs-dismiss="alert"></button>' +
            '</div>';
        $('.container').first().prepend(alertHtml);
        setTimeout(function () {
            $('.alert').fadeOut();
        }, 3000);
    }
});

/**
 * Widget: Reject Shift
 */
publicWidget.registry.PortalRejectShift = publicWidget.Widget.extend({
    selector: '.js_reject_shift',
    events: {
        'click': '_onClick',
    },

    _onClick: function (ev) {
        ev.preventDefault();
        var self = this;
        var $btn = $(ev.currentTarget);
        var slotId = $btn.data('slot-id');

        if (!slotId) {
            alert('Lỗi: Không tìm thấy ID ca làm việc.');
            return;
        }

        var reason = prompt('Nhập lý do từ chối (tùy chọn):');
        if (reason === null) {
            // User cancelled
            return;
        }

        // Disable button and show loading
        $btn.prop('disabled', true);
        $btn.html('<i class="fa fa-spinner fa-spin"></i>');

        callOdooRpc('/my/approvals/reject-shift', { slot_id: slotId, reason: reason })
            .then(function (result) {
                if (result.success) {
                    var $row = $btn.closest('tr, .shift-row');
                    $row.fadeOut(300, function () {
                        $(this).remove();
                        self._showAlert('warning', result.message || 'Đã từ chối ca.');
                    });
                } else {
                    alert(result.error || 'Có lỗi xảy ra.');
                    $btn.prop('disabled', false);
                    $btn.html('<i class="fa fa-times"></i> Từ chối');
                }
            })
            .catch(function (err) {
                alert('Lỗi: ' + err.message);
                $btn.prop('disabled', false);
                $btn.html('<i class="fa fa-times"></i> Từ chối');
            });
    },

    _showAlert: function (type, message) {
        var alertHtml = '<div class="alert alert-' + type + ' alert-dismissible fade show" role="alert">' +
            message +
            '<button type="button" class="btn-close" data-bs-dismiss="alert"></button>' +
            '</div>';
        $('.container').first().prepend(alertHtml);
        setTimeout(function () {
            $('.alert').fadeOut();
        }, 3000);
    }
});

/**
 * Widget: Approve Request
 */
publicWidget.registry.PortalApproveRequest = publicWidget.Widget.extend({
    selector: '.js_approve_request',
    events: {
        'click': '_onClick',
    },

    _onClick: function (ev) {
        ev.preventDefault();
        var self = this;
        var $btn = $(ev.currentTarget);
        var requestId = $btn.data('request-id');

        if (!requestId) {
            alert('Lỗi: Không tìm thấy ID yêu cầu.');
            return;
        }

        if (!confirm('Bạn có chắc muốn duyệt yêu cầu này?')) {
            return;
        }

        $btn.prop('disabled', true);
        $btn.html('<i class="fa fa-spinner fa-spin"></i>');

        callOdooRpc('/my/approvals/approve-request', { request_id: requestId })
            .then(function (result) {
                if (result.success) {
                    var $row = $btn.closest('.request-row, .list-group-item');
                    $row.fadeOut(300, function () {
                        $(this).remove();
                        self._showAlert('success', result.message || 'Đã duyệt thành công!');
                    });
                } else {
                    alert(result.error || 'Có lỗi xảy ra.');
                    $btn.prop('disabled', false);
                    $btn.html('<i class="fa fa-check"></i> Duyệt');
                }
            })
            .catch(function (err) {
                alert('Lỗi: ' + err.message);
                $btn.prop('disabled', false);
                $btn.html('<i class="fa fa-check"></i> Duyệt');
            });
    },

    _showAlert: function (type, message) {
        var alertHtml = '<div class="alert alert-' + type + ' alert-dismissible fade show" role="alert">' +
            message +
            '<button type="button" class="btn-close" data-bs-dismiss="alert"></button>' +
            '</div>';
        $('.container').first().prepend(alertHtml);
        setTimeout(function () {
            $('.alert').fadeOut();
        }, 3000);
    }
});

/**
 * Widget: Reject Request
 */
publicWidget.registry.PortalRejectRequest = publicWidget.Widget.extend({
    selector: '.js_reject_request',
    events: {
        'click': '_onClick',
    },

    _onClick: function (ev) {
        ev.preventDefault();
        var self = this;
        var $btn = $(ev.currentTarget);
        var requestId = $btn.data('request-id');

        if (!requestId) {
            alert('Lỗi: Không tìm thấy ID yêu cầu.');
            return;
        }

        var reason = prompt('Nhập lý do từ chối:');
        if (reason === null) {
            return;
        }

        $btn.prop('disabled', true);
        $btn.html('<i class="fa fa-spinner fa-spin"></i>');

        callOdooRpc('/my/approvals/reject-request', { request_id: requestId, reason: reason })
            .then(function (result) {
                if (result.success) {
                    var $row = $btn.closest('.request-row, .list-group-item');
                    $row.fadeOut(300, function () {
                        $(this).remove();
                        self._showAlert('warning', result.message || 'Đã từ chối yêu cầu.');
                    });
                } else {
                    alert(result.error || 'Có lỗi xảy ra.');
                    $btn.prop('disabled', false);
                    $btn.html('<i class="fa fa-times"></i> Từ chối');
                }
            })
            .catch(function (err) {
                alert('Lỗi: ' + err.message);
                $btn.prop('disabled', false);
                $btn.html('<i class="fa fa-times"></i> Từ chối');
            });
    },

    _showAlert: function (type, message) {
        var alertHtml = '<div class="alert alert-' + type + ' alert-dismissible fade show" role="alert">' +
            message +
            '<button type="button" class="btn-close" data-bs-dismiss="alert"></button>' +
            '</div>';
        $('.container').first().prepend(alertHtml);
        setTimeout(function () {
            $('.alert').fadeOut();
        }, 3000);
    }
});

/**
 * Widget: Approve Leave (with Replacement select)
 */
publicWidget.registry.PortalApproveLeave = publicWidget.Widget.extend({
    selector: '.js_approve_leave',
    events: {
        'click': '_onClick',
    },

    _onClick: function (ev) {
        ev.preventDefault();
        var $btn = $(ev.currentTarget);
        var leaveId = $btn.data('leave-id');
        var employeeName = $btn.data('employee-name');
        var leaveInfo = $btn.data('leave-info');

        if (!leaveId) {
            alert('Lỗi: Không tìm thấy ID đơn nghỉ.');
            return;
        }

        // Setup modal
        $('#modal_leave_id').val(leaveId);
        $('#modal_employee_name').text(employeeName);
        $('#modal_leave_info').text(leaveInfo);

        // Reset select
        var $select = $('#replacement_employee_id');
        $select.html('<option value="">-- Đang tải danh sách... --</option>');
        $select.prop('disabled', true);

        // Open modal (BS5)
        var modalEl = document.getElementById('leaveApprovalModal');
        if (modalEl) {
            var modal = bootstrap.Modal.getOrCreateInstance(modalEl);
            modal.show();

            // Fetch candidates
            callOdooRpc('/my/approvals/leave-replacement-candidates', { leave_id: leaveId })
                .then(function (result) {
                    var html = '<option value="">-- Không có người thay thế --</option>';
                    if (result.candidates && result.candidates.length > 0) {
                        result.candidates.forEach(function (c) {
                            html += '<option value="' + c.id + '">' + c.name + ' (' + c.dept + ')</option>';
                        });
                    }
                    $select.html(html);
                    $select.prop('disabled', false);
                })
                .catch(function (err) {
                    console.error(err);
                    $select.html('<option value="">-- Lỗi khi tải danh sách --</option>');
                });
        }
    },
});

// Logic for Confirm button in modal (Global handler for BS5 modal in Portal)
$(document).on('click', '#btn_confirm_leave_approval', function () {
    var leaveId = $('#modal_leave_id').val();
    var replacementId = $('#replacement_employee_id').val();
    var $btn = $(this);

    $btn.prop('disabled', true);
    var originalHtml = $btn.html();
    $btn.html('<i class="fa fa-spinner fa-spin me-1"></i>Đang duyệt...');

    callOdooRpc('/my/team/leave/approve', {
        leave_id: leaveId,
        replacement_employee_id: replacementId || null
    }).then(function (result) {
        if (result.success) {
            // Success: Close modal
            var modalEl = document.getElementById('leaveApprovalModal');
            var modal = bootstrap.Modal.getInstance(modalEl);
            if (modal) modal.hide();

            // Remove row from table
            var $row = $('.leave-row[data-leave-id="' + leaveId + '"]');
            $row.fadeOut(300, function () {
                $(this).remove();
            });

            // Re-enable button for next use
            $btn.prop('disabled', false);
            $btn.html(originalHtml);
        } else {
            alert(result.error || 'Có lỗi xảy ra.');
            $btn.prop('disabled', false);
            $btn.html(originalHtml);
        }
    }).catch(function (err) {
        alert('Lỗi: ' + err.message);
        $btn.prop('disabled', false);
        $btn.html(originalHtml);
    });
});

/**
 * Widget: Reject Leave
 */
publicWidget.registry.PortalRejectLeave = publicWidget.Widget.extend({
    selector: '.js_reject_leave',
    events: {
        'click': '_onClick',
    },

    _onClick: function (ev) {
        ev.preventDefault();
        var $btn = $(ev.currentTarget);
        var leaveId = $btn.data('leave-id');

        if (!leaveId) {
            alert('Lỗi: Không tìm thấy ID đơn nghỉ.');
            return;
        }

        var reason = prompt('Nhập lý do từ chối đơn nghỉ phép:');
        if (reason === null) return;

        $btn.prop('disabled', true);
        $btn.html('<i class="fa fa-spinner fa-spin"></i>');

        callOdooRpc('/my/team/leave/reject', { leave_id: leaveId, reason: reason })
            .then(function (result) {
                if (result.success) {
                    var $row = $btn.closest('.leave-row');
                    $row.fadeOut(300, function () {
                        $(this).remove();
                    });
                } else {
                    alert(result.error || 'Có lỗi xảy ra.');
                    $btn.prop('disabled', false);
                    $btn.html('<i class="fa fa-times"></i> Từ chối');
                }
            })
            .catch(function (err) {
                alert('Lỗi: ' + err.message);
                $btn.prop('disabled', false);
                $btn.html('<i class="fa fa-times"></i> Từ chối');
            });
    }
});

export default {
    PortalApproveShift: publicWidget.registry.PortalApproveShift,
    PortalRejectShift: publicWidget.registry.PortalRejectShift,
    PortalApproveRequest: publicWidget.registry.PortalApproveRequest,
    PortalRejectRequest: publicWidget.registry.PortalRejectRequest,
    PortalApproveLeave: publicWidget.registry.PortalApproveLeave,
    PortalRejectLeave: publicWidget.registry.PortalRejectLeave,
};
