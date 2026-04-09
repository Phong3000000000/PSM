/* eslint-disable no-undef */
(function () {
    function initStaffForm(form) {
        var countNi = document.getElementById("staff_count_ni");
        var countGd = document.getElementById("staff_count_gd");
        var countEx = document.getElementById("staff_count_ex");
        var countOs = document.getElementById("staff_count_os");
        var warning = document.getElementById("staff_ni_warning");
        var rejectDecision = form.querySelector("input[name='staff_decision'][value='reject']");
        var hireDecision = form.querySelector("input[name='staff_decision'][value='hire']");
        var otherPositionDecision = form.querySelector("input[name='staff_decision'][value='other_position']");

        if (!countNi || !countGd || !countEx || !countOs) {
            return;
        }

        function setAutoDecision(value) {
            if (value) {
                form.dataset.autoDecision = value;
            } else {
                delete form.dataset.autoDecision;
            }
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

            if (rejectDecision && !rejectDecision.disabled && ni > 0) {
                if (!rejectDecision.checked) {
                    rejectDecision.checked = true;
                }
                setAutoDecision("reject");
                return;
            }

            if (ni === 0 && rejectDecision && hireDecision && !hireDecision.disabled) {
                if (form.dataset.autoDecision === "reject" && rejectDecision.checked) {
                    hireDecision.checked = true;
                    setAutoDecision("");
                    return;
                }

                // Backward compatibility for old records that were auto-rejected before this flag existed.
                if (
                    !form.dataset.autoDecision &&
                    form.dataset.staffDecisionTouched !== "1" &&
                    rejectDecision.checked &&
                    !(otherPositionDecision && otherPositionDecision.checked)
                ) {
                    hireDecision.checked = true;
                }
            }
        }

        form.addEventListener("change", function (ev) {
            if (!ev.target || !ev.target.name) {
                return;
            }

            if (ev.target.name === "staff_decision") {
                form.dataset.staffDecisionTouched = "1";
                setAutoDecision("");
                recalc();
                return;
            }

            if (ev.target.name.endsWith("_rating")) {
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
        var dimensionBlocks = form.querySelectorAll(".oje-management-dimension[data-management-dimension-id]");

        if (!overallInput || !resultLabel || !hireRadio || !rejectRadio) {
            return;
        }

        function formatRating(value) {
            if (!Number.isFinite(value)) {
                return "0.00";
            }
            return value.toFixed(2);
        }

        function recalc() {
            var overallTotal = 0;
            var overallCount = 0;

            dimensionBlocks.forEach(function (sectionBlock) {
                var sectionId = sectionBlock.getAttribute("data-management-dimension-id");
                var groupScores = {};

                sectionBlock.querySelectorAll("input[type='radio'][name$='_score']").forEach(function (input) {
                    if (!groupScores[input.name]) {
                        groupScores[input.name] = 0;
                    }
                    if (input.checked) {
                        var parsed = Number(input.value || 0);
                        if (Number.isFinite(parsed)) {
                            groupScores[input.name] = parsed;
                        }
                    }
                });

                var taskNames = Object.keys(groupScores);
                var sectionRating = 0;
                if (taskNames.length) {
                    var sectionTotal = 0;
                    taskNames.forEach(function (taskName) {
                        sectionTotal += groupScores[taskName];
                    });
                    sectionRating = sectionTotal / taskNames.length;
                    overallTotal += sectionRating;
                    overallCount += 1;
                }

                var sectionInput = sectionBlock.querySelector("[data-management-section-rating-input]");
                if (sectionInput) {
                    sectionInput.value = formatRating(sectionRating);
                }

                if (sectionId) {
                    var summaryCell = form.querySelector(
                        "[data-management-summary-section-id='" + sectionId + "']"
                    );
                    if (summaryCell) {
                        summaryCell.textContent = formatRating(sectionRating);
                    }
                }
            });

            var overallRating = overallCount ? overallTotal / overallCount : 0;
            overallInput.value = formatRating(overallRating);

            var isHire = overallRating >= 3;
            resultLabel.textContent = isHire ? "HIRE" : "REJECT";
            hireRadio.checked = isHire;
            rejectRadio.checked = !isHire;
        }

        form.addEventListener("change", function (ev) {
            if (!ev.target || !ev.target.name) {
                return;
            }

            if (ev.target.name.endsWith("_score")) {
                recalc();
            }
        });

        recalc();
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
