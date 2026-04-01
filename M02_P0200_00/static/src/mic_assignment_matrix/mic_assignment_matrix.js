/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Component, useState, onWillStart } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";

export class MicAssignmentMatrix extends Component {
    setup() {
        this.orm = useService("orm");
        this.notification = useService("notification");
        
        const today = new Date();
        this.state = useState({
            currentMonth: today.getMonth() + 1,
            currentYear: today.getFullYear(),
            currentPosId: null,
            posConfigs: [],
            months: [
                { value: 1, label: "Tháng 01" }, { value: 2, label: "Tháng 02" },
                { value: 3, label: "Tháng 3" }, { value: 4, label: "Tháng 4" },
                { value: 5, label: "Tháng 5" }, { value: 6, label: "Tháng 6" },
                { value: 7, label: "Tháng 7" }, { value: 8, label: "Tháng 8" },
                { value: 9, label: "Tháng 9" }, { value: 10, label: "Tháng 10" },
                { value: 11, label: "Tháng 11" }, { value: 12, label: "Tháng 12" },
            ],
            years: [today.getFullYear() - 1, today.getFullYear(), today.getFullYear() + 1],
            matrix: [],
            shifts: [],
            managers: [],
            activeMicId: 0,
            brushMode: false,
            isLoading: false,
        });

        onWillStart(async () => {
            await this._loadInitialData();
            await this._loadMatrixData();
        });
    }

    async _loadInitialData() {
        // Load POS Configs
        const posConfigs = await this.orm.searchRead(
            "pos.config",
            [],
            ["id", "name"]
        );
        this.state.posConfigs = posConfigs;
        if (posConfigs.length > 0) {
            this.state.currentPosId = posConfigs[0].id;
        }

        // Load Managers (MIC Candidates)
        // Lấy nhân viên thuộc department OPS và có role quản lý (tạm thời lấy tất cả NV)
        const managers = await this.orm.searchRead(
            "hr.employee",
            [],
            ["id", "name"]
        );
        this.state.managers = managers;
    }

    async _loadMatrixData() {
        if (!this.state.currentPosId) return;
        
        this.state.isLoading = true;
        console.log("Loading Matrix Data for POS:", this.state.currentPosId, "Month:", this.state.currentMonth);
        try {
            const data = await this.orm.call(
                "shift.log",
                "get_matrix_data",
                [this.state.currentMonth, this.state.currentYear, this.state.currentPosId],
                {}
            );
            console.log("Matrix Data Loaded:", data);
            this.state.matrix = data.matrix;
            this.state.shifts = data.shifts;
        } catch (e) {
            console.error("Failed to load matrix data:", e);
            this.notification.add(_t("Không thể tải dữ liệu ma trận. Vui lòng kiểm tra log."), { type: "danger" });
        } finally {
            this.state.isLoading = false;
        }
    }

    // --- Formatters ---
    getDateLabel(dateStr) {
        return dateStr.split("-")[2];
    }

    getConflictTitle(type) {
        if (type === 'leave') return _t("Nhân viên đang nghỉ phép!");
        if (type === 'planning') return _t("Trùng lịch Planning khác!");
        return _t("Xung đột lịch làm việc!");
    }

    isBrushActive(date, shiftId) {
        return this.state.brushMode && this.state.activeMicId;
    }
    async onRefresh() {
        await this._loadMatrixData();
    }

    async onChangePos(ev) {
        this.state.currentPosId = parseInt(ev.target.value);
        await this._loadMatrixData();
    }

    async onChangeMonth(ev) {
        this.state.currentMonth = parseInt(ev.target.value);
        await this._loadMatrixData();
    }

    async onChangeYear(ev) {
        this.state.currentYear = parseInt(ev.target.value);
        await this._loadMatrixData();
    }

    onSelectActiveMic(ev) {
        this.state.activeMicId = parseInt(ev.target.value);
    }

    toggleBrushMode() {
        if (!this.state.activeMicId) {
            this.notification.add(_t("Vui lòng chọn 1 MIC trước khi dùng chế độ Brush!"), { type: "danger" });
            return;
        }
        this.state.brushMode = !this.state.brushMode;
    }

    async onCellSelectMic(ev, cell) {
        const micId = parseInt(ev.target.value);
        await this._assignMicToCell(cell, micId);
    }

    async onCellClick(row, shift) {
        const cell = row.shifts[shift.id];
        if (!cell) return;

        if (this.state.brushMode) {
            await this._assignMicToCell(cell, this.state.activeMicId);
        } else {
            if (!this.state.activeMicId) {
                this.notification.add(_t("Hãy chọn MIC ở bảng bên phải để gán!"), { type: "info" });
                return;
            }
            await this._assignMicToCell(cell, this.state.activeMicId);
        }
    }

    async onCellMouseEnter(row, shift) {
        if (this.state.brushMode && this.state.activeMicId) {
            const cell = row.shifts[shift.id];
            if (cell && cell.mic_id !== this.state.activeMicId) {
                await this._assignMicToCell(cell, this.state.activeMicId);
            }
        }
    }

    async _assignMicToCell(cell, micId) {
        this.state.isLoading = true;
        try {
            await this.orm.write("shift.log", [cell.log_id], {
                mic_id: micId,
            });
            // Update local state
            cell.mic_id = micId;
            const mic = this.state.managers.find(m => m.id === micId);
            cell.mic_name = mic ? mic.name : "Trống";
        } catch (e) {
            console.error("Error saving MIC:", e);
        } finally {
            this.state.isLoading = false;
        }
    }

    async onFillDown() {
        // Lấy ngày đầu tiên có log trong matrix
        if (!this.state.matrix.length) return;
        const fromDate = this.state.matrix[0].date;
        const toDates = this.state.matrix.slice(1).map(r => r.date);
        
        this.state.isLoading = true;
        try {
            await this.orm.call(
                "shift.log",
                "action_copy_day_schedule",
                [],
                {
                    from_date: fromDate,
                    to_dates: toDates,
                    pos_config_id: this.state.currentPosId,
                }
            );
            this.notification.add(_t("Đã copy lịch ngày đầu tiên cho cả tháng!"), { type: "success" });
            await this._loadMatrixData();
        } finally {
            this.state.isLoading = false;
        }
    }

    async onClearMonth() {
        if (!confirm(_t("Bạn có chắc chắn muốn xóa tất cả MIC trong tháng này?"))) return;
        
        const logIds = this.state.matrix.flatMap(r => Object.values(r.shifts).filter(s => s).map(s => s.log_id));
        if (!logIds.length) return;

        this.state.isLoading = true;
        try {
            await this.orm.write("shift.log", logIds, { mic_id: false });
            this.notification.add(_t("Đã xóa trắng MIC của tháng!"), { type: "success" });
            await this._loadMatrixData();
        } finally {
            this.state.isLoading = false;
        }
    }

    async onGenerateLogs() {
        // Mở wizard generate log
        this.notification.add(_t("Vui lòng sử dụng Wizard Generate Shift Log để tạo dữ liệu."), { type: "info" });
    }

    async onSyncPlanning() {
        this.notification.add(_t("Tính năng đồng bộ từ Planning đang được phát triển..."), { type: "info" });
    }
}

MicAssignmentMatrix.template = "mic_assignment_matrix.Main";
MicAssignmentMatrix.components = {};

registry.category("actions").add("mic_assignment_matrix", MicAssignmentMatrix);
