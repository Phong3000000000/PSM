/** @odoo-module **/

function extractSlotIndexFromText(text) {
    if (!text) {
        return null;
    }
    var match = text.match(/Ngay\s*PV\s*(\d)|Ngày\s*PV\s*(\d)/i);
    if (!match) {
        return null;
    }
    var index = parseInt(match[1] || match[2], 10);
    return [1, 2, 3].includes(index) ? String(index) : null;
}

function getChoiceRowsForQ14(formEl) {
    var rows = [];
    formEl.querySelectorAll('.o_survey_form_choice .o_survey_choice_btn').forEach(function (row) {
        var text = row.innerText || '';
        var slotIndex = extractSlotIndexFromText(text);
        if (slotIndex) {
            rows.push({
                row: row,
                slotIndex: slotIndex,
            });
        }
    });
    return rows;
}

function applySlotAvailability(formEl, availability) {
    var rows = getChoiceRowsForQ14(formEl);
    if (!rows.length) {
        return;
    }

    rows.forEach(function (item) {
        var remaining = (availability.remaining || {})[item.slotIndex] || 0;
        var input = item.row.querySelector('input[type="radio"], input[type="checkbox"]');
        var isFull = remaining <= 0;

        if (input) {
            input.disabled = isFull;
            if (isFull) {
                input.checked = false;
            }
        }

        item.row.classList.toggle('opacity-50', isFull);
        item.row.classList.toggle('pe-none', isFull);

        var badge = item.row.querySelector('.o_slot_remaining_badge');
        if (!badge) {
            badge = document.createElement('span');
            badge.className = 'o_slot_remaining_badge badge ms-2';
            item.row.appendChild(badge);
        }

        badge.classList.remove('text-bg-success', 'text-bg-danger');
        badge.classList.add(isFull ? 'text-bg-danger' : 'text-bg-success');
        badge.textContent = isFull ? 'Hết chổ' : ('Còn ' + remaining);
    });
}

async function fetchAvailability(formEl) {
    var surveyToken = formEl.dataset.surveyToken;
    var answerToken = formEl.dataset.answerToken;
    if (!surveyToken || !answerToken) {
        return null;
    }

    var response = await fetch('/recruitment/interview/slot_status/' + surveyToken + '/' + answerToken, {
        method: 'GET',
        credentials: 'same-origin',
        headers: {
            'Accept': 'application/json',
        },
    });
    if (!response.ok) {
        return null;
    }
    return await response.json();
}

async function refreshSlotStatus(formEl) {
    try {
        var data = await fetchAvailability(formEl);
        if (data && data.ok) {
            applySlotAvailability(formEl, data);
        }
    } catch (_err) {
        // Do not block survey flow if polling fails.
    }
}

function bootRealtimeSlotAvailability() {
    var formEl = document.querySelector('form.o_survey-fill-form');
    if (!formEl) {
        return;
    }

    refreshSlotStatus(formEl);
    setInterval(function () {
        refreshSlotStatus(formEl);
    }, 4000);

    document.addEventListener('click', function () {
        // Survey uses AJAX to replace question content, so refresh after interactions.
        setTimeout(function () {
            refreshSlotStatus(formEl);
        }, 200);
    });
}

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', bootRealtimeSlotAvailability);
} else {
    bootRealtimeSlotAvailability();
}
