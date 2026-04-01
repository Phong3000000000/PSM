/** @odoo-module */

import { Component, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

/**
 * Component Popup đánh giá hiệu suất cuối ca
 * Hiển thị khi nhân viên bấm Check-out
 */
export class KioskRatingPopup extends Component {
    static template = "M02_P0206_00.RatingPopup";
    static props = {
        close: Function,
        employeeId: Number,
        onConfirm: Function,
    };

    setup() {
        this.rpc = useService("rpc");
        this.state = useState({
            rating: "3",
            note: "",
            confirmedHours: 0,
            isConfirmed: false,
        });
    }

    selectRating(rating) {
        this.state.rating = rating;
    }

    async confirm() {
        if (!this.state.isConfirmed) {
            alert("Vui lòng xác nhận giờ công trước khi hoàn tất!");
            return;
        }

        try {
            await this.rpc("/attendance/rating", {
                employee_id: this.props.employeeId,
                rating: this.state.rating,
                note: this.state.note,
                confirmed_hours: this.state.confirmedHours,
            });
            this.props.onConfirm();
            this.props.close();
        } catch (error) {
            console.error("Error saving rating:", error);
            alert("Lỗi khi lưu đánh giá!");
        }
    }

    cancel() {
        this.props.close();
    }
}

// Register as a dialog/popup component
registry.category("components").add("KioskRatingPopup", KioskRatingPopup);

