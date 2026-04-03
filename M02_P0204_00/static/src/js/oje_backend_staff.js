/* eslint-disable no-undef */
(function () {
    function initStaffForm(form) {
        var countNi = document.getElementById("staff_count_ni");
        var countGd = document.getElementById("staff_count_gd");
        var countEx = document.getElementById("staff_count_ex");
        var countOs = document.getElementById("staff_count_os");
        var warning = document.getElementById("staff_ni_warning");
        var rejectDecision = form.querySelector("input[name='staff_decision'][value='reject']");

        if (!countNi || !countGd || !countEx || !countOs) {
            return;
        }

        function recalc() {
            var selected = form.querySelectorAll("input[type='radio'][name$='_rating']:checked");
            var ni = 0;
            var gd = 0;
            var ex = 0;
            var os = 0;

            selected.forEach(function (input) {
                if (input.value === "ni") {
                    ni += 1;
                } else if (input.value === "gd") {
                    gd += 1;
                } else if (input.value === "ex") {
                    ex += 1;
                } else if (input.value === "os") {
                    os += 1;
                }
            });

            countNi.value = ni;
            countGd.value = gd;
            countEx.value = ex;
            countOs.value = os;

            if (warning) {
                if (ni > 0) {
                    warning.classList.remove("d-none");
                } else {
                    warning.classList.add("d-none");
                }
            }

            if (rejectDecision && !rejectDecision.disabled && ni > 0 && !rejectDecision.checked) {
                rejectDecision.checked = true;
            }
        }

        form.addEventListener("change", function (ev) {
            if (ev.target && ev.target.name && ev.target.name.endsWith("_rating")) {
                recalc();
            }
        });

        recalc();
    }

    function initManagementForm(form) {
        var overallInput = document.getElementById("management_overall_rating");
        var resultLabel = document.getElementById("management_result_label");
        var hireRadio = document.getElementById("management_applicant_hire");
        var rejectRadio = document.getElementById("management_applicant_reject");

        if (!overallInput || !resultLabel || !hireRadio || !rejectRadio) {
            return;
        }

        function normalizeOverall() {
            var parsed = Number(overallInput.value || 0);
            if (!Number.isFinite(parsed)) {
                parsed = 0;
            }
            parsed = Math.floor(parsed);

            if (parsed < 1) {
                parsed = 1;
            }
            if (parsed > 5) {
                parsed = 5;
            }
            overallInput.value = parsed;
            return parsed;
        }

        function syncFinalDisplay() {
            var value = Number(overallInput.value || 0);
            if (!Number.isFinite(value)) {
                value = 0;
            }

            var isHire = value >= 3;
            resultLabel.textContent = isHire ? "HIRE" : "REJECT";
            hireRadio.checked = isHire;
            rejectRadio.checked = !isHire;
        }

        overallInput.addEventListener("blur", function () {
            if (!overallInput.value) {
                return;
            }
            normalizeOverall();
            syncFinalDisplay();
        });

        overallInput.addEventListener("change", syncFinalDisplay);
        overallInput.addEventListener("input", syncFinalDisplay);

        syncFinalDisplay();
    }

    function init() {
        var form = document.querySelector(".oje-form[data-oje-scope]");
        if (!form) {
            return;
        }

        // Defensive fix: ensure page scroll is available even if stale styles are cached.
        document.documentElement.style.overflowY = "auto";
        document.documentElement.style.height = "auto";
        document.body.style.overflowY = "auto";
        document.body.style.height = "auto";

        var scope = form.getAttribute("data-oje-scope");
        if (scope === "store_staff") {
            initStaffForm(form);
        } else if (scope === "store_management") {
            initManagementForm(form);
        }
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", init);
    } else {
        init();
    }
})();
