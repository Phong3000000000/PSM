/** @odoo-module **/

import publicWidget from "@web/legacy/js/public/public_widget";
import { rpc } from "@web/core/network/rpc";

publicWidget.registry.SocEvaluation = publicWidget.Widget.extend({
    selector: '.o_soc_evaluation_view',
    events: {
        'change .btn-check': '_onItemChange',
        'click #btn_submit_soc': '_onSubmit',
    },

    start: function () {
        this.totalItems = parseInt(this.$('#total_items_count').text()) || 0;
        this._updateSummary();
        return this._super.apply(this, arguments);
    },

    _onItemChange: function (ev) {
        // Find the parent row of the changed input
        const $row = $(ev.target).closest('.soc-item-row');
        const isCritical = $row.data('critical');
        const value = ev.target.value; // 'pass', 'fail', 'na'

        // UI Feedback: Highlight row based on status
        $row.removeClass('bg-success bg-danger bg-opacity-10');
        if (value === 'pass') {
            $row.addClass('bg-success bg-opacity-10');
        } else if (value === 'fail') {
            $row.addClass('bg-danger bg-opacity-10');
        }

        // Critical Check immediately
        if (isCritical && value === 'fail') {
            this._showCriticalFailAlert(true);
        } else {
            // Re-check if ANY critical is still failed
            this._checkAllCriticals();
        }

        this._updateSummary();
    },

    _checkAllCriticals: function () {
        let criticalFail = false;
        this.$('.soc-item-row[data-critical="True"]').each(function () {
            const val = $(this).find('input:checked').val();
            if (val === 'fail') {
                criticalFail = true;
            }
        });
        this._showCriticalFailAlert(criticalFail);
    },

    _showCriticalFailAlert: function (show) {
        if (show) {
            this.$('#critical_fail_alert').removeClass('d-none');
        } else {
            this.$('#critical_fail_alert').addClass('d-none');
        }
    },

    _updateSummary: function () {
        let failCount = 0;
        let passCount = 0;
        let naCount = 0;

        // Count totals
        const $rows = this.$('.soc-item-row');
        $rows.each(function () {
            const val = $(this).find('input:checked').val();
            if (val === 'fail') failCount++;
            else if (val === 'pass') passCount++;
            else if (val === 'na') naCount++;
        });

        this.$('#failed_count').text(failCount);

        // Calculate Score
        // Formula: (Pass / (Total - NA)) * 100
        const effectiveTotal = this.totalItems - naCount;
        let score = 0;
        if (effectiveTotal > 0) {
            score = Math.round((passCount / effectiveTotal) * 100);
        } else {
            score = 100; // Default if all N/A? Or 0? Let's say 100 if no items to fail.
        }

        const $scoreEl = this.$('#current_score');
        $scoreEl.text(score + '%');

        // Visual Color
        $scoreEl.removeClass('text-success text-warning text-danger');
        if (score >= 100) $scoreEl.addClass('text-success');
        else if (score >= 80) $scoreEl.addClass('text-warning');
        else $scoreEl.addClass('text-danger');
    },

    _onSubmit: async function () {
        const slideId = this.$el.data('slide-id');

        // Gather results
        const results = {};
        this.$('.soc-item-row').each(function () {
            const itemId = $(this).data('item-id');
            const val = $(this).find('input:checked').val();
            results[itemId] = val;
        });

        // Send to backend
        try {
            const result = await rpc('/slides/soc/submit', {
                slide_id: slideId,
                results: results,
            });

            if (result.success) {
                let msg = "SOC Submitted Successfully!";
                if (result.passed) {
                    msg += " You PASSED with score " + result.score + "%.";
                    if (result.skill_message) {
                        msg += "\n\n" + result.skill_message;
                    }
                } else {
                    msg += " You FAILED with score " + result.score + "%.";
                }

                alert(msg);
                window.location.href = "/slides/slide/" + slideId + "?soc_submitted=1";
            } else {
                alert("Error: " + (result.message || "Unknown error"));
            }

        } catch (error) {
            console.error("Submission Error", error);
            alert("Error submitting SOC. Please try again.");
        }
    }
});
