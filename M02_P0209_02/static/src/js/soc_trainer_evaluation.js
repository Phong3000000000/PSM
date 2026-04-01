/** @odoo-module **/

import publicWidget from "@web/legacy/js/public/public_widget";
import { rpc } from "@web/core/network/rpc";

publicWidget.registry.SocTrainerEvaluation = publicWidget.Widget.extend({
    selector: '.o_soc_trainer_form',
    events: {
        'click .btn-submit-soc': '_onSubmit',
    },

    _onSubmit: async function (ev) {
        ev.preventDefault();
        const $btn = $(ev.currentTarget);
        $btn.prop('disabled', true);

        const form = document.getElementById('socForm');
        const formData = new FormData(form);
        const results = {};

        formData.forEach(function (value, key) {
            results[key] = value;
        });

        const slideId = parseInt(formData.get('slide_id'));
        const employeeId = parseInt(formData.get('employee_id'));

        try {
            const data = await rpc("/soc/trainer/submit", {
                slide_id: slideId,
                employee_id: employeeId,
                results: results,
            });

            if (data.success) {
                // Fallback: If result_code is undefined (backend not reloaded), check message text
                let isPass = false;
                if (data.result_code) {
                    isPass = (data.result_code === 'pass');
                } else {
                    isPass = (data.message && data.message.includes("Result: PASS"));
                }

                const title = isPass ? "SOC PASSED!" : "SOC FAILED";
                const score = data.score !== undefined ? data.score : (isPass ? 100.0 : 0.0);

                this._showResultModal(isPass, title, score, data.message, data.skill_message, data.redirect, data.recommendation, employeeId);
            } else {
                this._showResultModal(false, "ERROR", 0, data.error || "Unknown Error", "", null, null, null);
                $btn.prop('disabled', false);
            }
        } catch (err) {
            console.error(err);
            this._showResultModal(false, "SYSTEM ERROR", 0, "Unexpected error occurred.", "", null, null, null);
            $btn.prop('disabled', false);
        }
    },

    _showResultModal: function (isSuccess, title, score, message, skillMessage, redirectUrl, recommendation, employeeId) {
        const $modal = $('#resultModal');
        const $header = $('#resultModalHeader');
        const $icon = $('#resultIcon');
        const $btn = $('#btnResultOk');
        const $recContainer = $('#recommendationContainer');
        const $btnNominate = $('#btnNominate');

        // Reset classes
        $header.removeClass('bg-success bg-danger bg-warning text-dark');
        $icon.removeClass('fa-check-circle fa-times-circle fa-exclamation-triangle text-success text-danger text-warning');
        $btn.removeClass('btn-success btn-danger btn-secondary');
        $recContainer.addClass('d-none');
        $btnNominate.addClass('d-none');

        if (title.includes("ERROR")) {
            $header.addClass('bg-warning text-dark');
            $icon.addClass('fa-exclamation-triangle text-warning');
            $btn.addClass('btn-secondary');
            $('#resultScore').hide();
        } else if (isSuccess) {
            $header.addClass('bg-success');
            $icon.addClass('fa-check-circle text-success');
            $btn.addClass('btn-success');
            $('#resultScore').show();
        } else {
            $header.addClass('bg-danger');
            $icon.addClass('fa-times-circle text-danger');
            $btn.addClass('btn-danger');
            $('#resultScore').show();
        }

        $('#resultModalTitle').text(title);
        $('#resultScore').text(score + '%');
        $('#resultMessage').text(message);
        $('#skillMessage').text(skillMessage || '');

        // Logic Recommendation
        if (recommendation) {
            $recContainer.removeClass('d-none');
            $('#recommendationMessage').text(recommendation.message);

            if (recommendation.type === 'nominate' && employeeId) {
                $btnNominate.removeClass('d-none');
                $btnNominate.off('click').on('click', async () => {
                    // Confirm dialog
                    if (!confirm("Are you sure you want to nominate this employee for the Potential List?")) {
                        return;
                    }

                    try {
                        const res = await rpc("/soc/trainer/nominate", { employee_id: employeeId });
                        if (res.success) {
                            alert("Nomination Successful! Employee added to Potential List.");
                            $modal.modal('hide');
                            if (redirectUrl) window.location.href = redirectUrl;
                        } else {
                            alert("Error: " + (res.error || "Unknown Error"));
                        }
                    } catch (e) {
                        console.error(e);
                        alert("Network Error: Failed to nominate");
                    }
                });
            }
        }

        // Handle Click OK
        $btn.off('click').on('click', function () {
            $modal.modal('hide');
            if (redirectUrl) {
                window.location.href = redirectUrl;
            }
        });

        $modal.modal('show');
    }
});
