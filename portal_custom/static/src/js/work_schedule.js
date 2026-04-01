/** @odoo-module **/

document.addEventListener('DOMContentLoaded', function () {
    var calendarEl = document.getElementById('workScheduleCalendar');
    if (!calendarEl) return;

    // Get CSRF token from Odoo
    function getCsrfToken() {
        var csrfInput = document.querySelector('input[name="csrf_token"]');
        return csrfInput ? csrfInput.value : '';
    }

    // JSON-RPC call helper
    function jsonRpc(url, params) {
        return fetch(url, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                jsonrpc: '2.0',
                method: 'call',
                params: params,
                id: Math.floor(Math.random() * 1000000)
            })
        }).then(function (response) {
            return response.json();
        });
    }

    // Initialize FullCalendar
    var calendar = new FullCalendar.Calendar(calendarEl, {
        initialView: 'dayGridMonth',
        locale: 'vi',
        height: 'auto',
        headerToolbar: {
            left: 'prev,next today',
            center: 'title',
            right: 'dayGridMonth,timeGridWeek,listWeek'
        },
        buttonText: {
            today: 'Hôm nay',
            month: 'Tháng',
            week: 'Tuần',
            list: 'Danh sách'
        },
        firstDay: 1, // Monday
        navLinks: true,
        editable: false,
        selectable: true,
        selectMirror: true,
        dayMaxEvents: 3,

        // Fetch events from server
        events: function (info, successCallback, failureCallback) {
            jsonRpc('/my/work-schedule/events', {
                start: info.startStr,
                end: info.endStr
            }).then(function (data) {
                if (data.result) {
                    successCallback(data.result);
                } else if (data.error) {
                    console.error('Error:', data.error);
                    failureCallback(data.error);
                }
            }).catch(function (error) {
                console.error('Error fetching events:', error);
                failureCallback(error);
            });
        },

        // Click on a date to open create modal
        dateClick: function (info) {
            var startInput = document.querySelector('#createScheduleForm input[name="start"]');
            var endInput = document.querySelector('#createScheduleForm input[name="end"]');

            if (startInput && endInput) {
                // Set default times: 8:00 - 17:00
                var startDate = info.dateStr + 'T08:00';
                var endDate = info.dateStr + 'T17:00';
                startInput.value = startDate;
                endInput.value = endDate;
            }

            var modal = new bootstrap.Modal(document.getElementById('createScheduleModal'));
            modal.show();
        },

        // Click on an event to view details
        eventClick: function (info) {
            alert('Sự kiện: ' + info.event.title + '\nBắt đầu: ' + info.event.start.toLocaleString('vi-VN'));
        },

        // Select a date range
        select: function (info) {
            var startInput = document.querySelector('#createScheduleForm input[name="start"]');
            var endInput = document.querySelector('#createScheduleForm input[name="end"]');

            if (startInput && endInput) {
                startInput.value = info.startStr.substring(0, 16);
                endInput.value = info.endStr.substring(0, 16);
            }

            var modal = new bootstrap.Modal(document.getElementById('createScheduleModal'));
            modal.show();
            calendar.unselect();
        }
    });

    calendar.render();

    // Handle form submission
    var submitBtn = document.getElementById('submitScheduleBtn');
    if (submitBtn) {
        submitBtn.addEventListener('click', function () {
            var form = document.getElementById('createScheduleForm');
            var title = form.querySelector('input[name="title"]').value;
            var start = form.querySelector('input[name="start"]').value;
            var end = form.querySelector('input[name="end"]').value;

            if (!start || !end) {
                alert('Vui lòng nhập đầy đủ thời gian bắt đầu và kết thúc!');
                return;
            }

            // Disable button during submission
            submitBtn.disabled = true;
            submitBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span> Đang xử lý...';

            jsonRpc('/my/work-schedule/create', {
                title: title,
                start: start,
                end: end
            }).then(function (data) {
                if (data.result && data.result.success) {
                    // Close modal
                    var modal = bootstrap.Modal.getInstance(document.getElementById('createScheduleModal'));
                    modal.hide();

                    // Show success message
                    showToast('success', data.result.message);

                    // Refresh calendar
                    calendar.refetchEvents();

                    // Reload page to update history
                    setTimeout(function () {
                        location.reload();
                    }, 1000);
                } else if (data.result && data.result.error) {
                    showToast('error', 'Lỗi: ' + data.result.error);
                } else if (data.error) {
                    showToast('error', 'Lỗi: ' + data.error.message);
                }
            }).catch(function (error) {
                console.error('Error:', error);
                showToast('error', 'Có lỗi xảy ra khi đăng ký!');
            }).finally(function () {
                submitBtn.disabled = false;
                submitBtn.innerHTML = 'Đăng ký';
            });
        });
    }

    // Toast notification helper
    function showToast(type, message) {
        // Create toast container if not exists
        var toastContainer = document.getElementById('toastContainer');
        if (!toastContainer) {
            toastContainer = document.createElement('div');
            toastContainer.id = 'toastContainer';
            toastContainer.className = 'toast-container position-fixed top-0 end-0 p-3';
            toastContainer.style.zIndex = '9999';
            document.body.appendChild(toastContainer);
        }

        var bgClass = type === 'success' ? 'bg-success' : 'bg-danger';
        var toastHtml = '<div class="toast align-items-center text-white ' + bgClass + ' border-0" role="alert">' +
            '<div class="d-flex">' +
            '<div class="toast-body">' + message + '</div>' +
            '<button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>' +
            '</div></div>';

        toastContainer.insertAdjacentHTML('beforeend', toastHtml);
        var toastEl = toastContainer.lastElementChild;
        var toast = new bootstrap.Toast(toastEl, { delay: 3000 });
        toast.show();

        // Remove toast after hidden
        toastEl.addEventListener('hidden.bs.toast', function () {
            toastEl.remove();
        });
    }
});
