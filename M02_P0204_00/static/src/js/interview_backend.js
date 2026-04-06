/* eslint-disable no-undef */
(function () {
    function parseScoreValue(value) {
        var parsed = Number(value || 0);
        if (!Number.isFinite(parsed)) {
            return 0;
        }
        parsed = Math.floor(parsed);
        if (parsed < 1 || parsed > 5) {
            return 0;
        }
        return parsed;
    }

    function initInterviewForm(form) {
        var count1 = document.getElementById("interview_count_1");
        var count2 = document.getElementById("interview_count_2");
        var count3 = document.getElementById("interview_count_3");
        var count4 = document.getElementById("interview_count_4");
        var count5 = document.getElementById("interview_count_5");
        var weightedTotal = document.getElementById("interview_weighted_total");
        var finalScore = document.getElementById("interview_final_score");
        var finalResult = document.getElementById("interview_final_result");

        if (!count1 || !count2 || !count3 || !count4 || !count5 || !weightedTotal || !finalScore || !finalResult) {
            return;
        }

        function recalc() {
            var checked = form.querySelectorAll("input[type='radio'][name$='_score']:checked");
            var c1 = 0;
            var c2 = 0;
            var c3 = 0;
            var c4 = 0;
            var c5 = 0;

            checked.forEach(function (input) {
                var score = parseScoreValue(input.value);
                if (score === 1) {
                    c1 += 1;
                } else if (score === 2) {
                    c2 += 1;
                } else if (score === 3) {
                    c3 += 1;
                } else if (score === 4) {
                    c4 += 1;
                } else if (score === 5) {
                    c5 += 1;
                }
            });

            var ratedCount = c1 + c2 + c3 + c4 + c5;
            var weighted = (1 * c1) + (2 * c2) + (3 * c3) + (4 * c4) + (5 * c5);
            var score = ratedCount > 0 ? (weighted / ratedCount) : 0;

            count1.value = (1 * c1);
            count2.value = (2 * c2);
            count3.value = (3 * c3);
            count4.value = (4 * c4);
            count5.value = (5 * c5);
            weightedTotal.textContent = String(ratedCount);
            finalScore.value = score.toFixed(2);
            finalResult.value = score >= 3 ? "PASS" : "REJECT";
        }

        form.addEventListener("change", function (ev) {
            if (!ev.target || !ev.target.name || !ev.target.name.endsWith("_score")) {
                return;
            }
            recalc();
        });

        recalc();
    }

    function init() {
        var form = document.querySelector(".interview-form[data-interview-mode='edit']");
        if (!form) {
            return;
        }
        initInterviewForm(form);
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", init);
    } else {
        init();
    }
})();
