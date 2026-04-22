/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { ListRenderer } from "@web/views/list/list_renderer";

patch(ListRenderer.prototype, {
    async onCellClicked(record, column, ev, newWindow) {
        const resModel = this.props.list && this.props.list.resModel;
        const resId = (record && (record.resId || (record.data && record.data.id))) || false;
        if (
            resModel === "x_psm_applicant_evaluation" &&
            record &&
            resId &&
            !ev.target.special_click &&
            !record.isInEdition
        ) {
            const url = `/recruitment/office-interview/evaluation/${resId}`;
            if (newWindow || ev.ctrlKey || ev.metaKey) {
                window.open(url, "_blank");
            } else {
                window.location.assign(url);
            }
            return;
        }
        return super.onCellClicked(record, column, ev, newWindow);
    },
});
