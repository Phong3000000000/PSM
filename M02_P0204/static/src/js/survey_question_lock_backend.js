/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { QuestionPageListRenderer } from "@survey/question_page/question_page_list_renderer";

function isLockedOnCustomRow(record) {
    return Boolean(record && record.data && record.data.x_psm_0204_is_locked_on_custom_ui);
}

patch(QuestionPageListRenderer.prototype, {
    displayDeleteIcon(record) {
        if (isLockedOnCustomRow(record)) {
            return false;
        }
        return super.displayDeleteIcon(...arguments);
    },

    async onCellClicked(record, column, ev, newWindow) {
        if (isLockedOnCustomRow(record)) {
            return;
        }
        return super.onCellClicked(record, column, ev, newWindow);
    },

    async onDeleteRecord(record) {
        if (isLockedOnCustomRow(record)) {
            return;
        }
        return super.onDeleteRecord(...arguments);
    },
});
