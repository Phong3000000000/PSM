/** @odoo-module **/

import { Component, useState, onMounted } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { rpc } from "@web/core/network/rpc";

// ─── Refuse Modal ─────────────────────────────────────────────────────────────
class RefuseModal extends Component {
    static template = "M02_P0207_02.RefuseModal";
    static props = {
        payslip: Object,
        onConfirm: Function,
        onCancel: Function,
    };
    setup() {
        this.state = useState({ reason: "" });
    }
    confirm() {
        if (!this.state.reason.trim()) return;
        this.props.onConfirm(this.props.payslip.id, this.state.reason);
    }
}

// ─── Main Component ───────────────────────────────────────────────────────────
class PayslipApprovalAction extends Component {
    static template = "M02_P0207_02.PayslipApprovalAction";
    static components = { RefuseModal };

    setup() {
        this.notification = useService("notification");
        this.actionService = useService("action");  // H2: navigate to payslip form

        this.state = useState({
            runs: [],
            selectedRunId: null,
            payslips: [],
            loading: false,
            refusingPayslip: null,
        });

        onMounted(() => this._loadRuns());
    }

    // ── Data loading ──────────────────────────────────────────────────────────
    async _loadRuns() {
        this.state.loading = true;
        try {
            const runs = await rpc("/web/dataset/call_kw", {
                model: "hr.payslip.run",
                method: "search_read",
                args: [[["state", "=", "waiting_approval"]]],
                kwargs: { fields: ["id", "name", "date_start", "date_end", "state"], limit: 50 },
            });
            this.state.runs = runs;
            // Pre-select from context (when opened via approval.request smart button)
            const ctxRunId = this.props.action?.context?.default_run_id;
            if (ctxRunId && runs.find(r => r.id === ctxRunId)) {
                this.state.selectedRunId = ctxRunId;
            } else if (runs.length > 0) {
                this.state.selectedRunId = runs[0].id;
            }
            if (this.state.selectedRunId) {
                await this._loadPayslips(this.state.selectedRunId);
            }
        } finally {
            this.state.loading = false;
        }
    }

    async _loadPayslips(runId) {
        this.state.loading = true;
        try {
            const payslips = await rpc("/web/dataset/call_kw", {
                model: "hr.payslip",
                method: "search_read",
                args: [[["payslip_run_id", "=", runId]]],
                kwargs: {
                    fields: [
                        "id", "employee_id", "employer_cost", "gross_wage", "net_wage",
                        "state", "x_approval_state", "x_refusal_reason",
                    ],
                },
            });
            this.state.payslips = payslips;
        } finally {
            this.state.loading = false;
        }
    }

    // ── Event handlers ────────────────────────────────────────────────────────
    async onRunChange(ev) {
        const runId = parseInt(ev.target.value);
        this.state.selectedRunId = runId;
        await this._loadPayslips(runId);
    }

    // H2: Click row → open payslip form
    openPayslip(payslipId) {
        this.actionService.doAction({
            type: "ir.actions.act_window",
            res_model: "hr.payslip",
            res_id: payslipId,
            views: [[false, "form"]],
            target: "current",
        });
    }

    async approvePayslip(payslipId) {
        await rpc("/web/dataset/call_kw", {
            model: "hr.payslip",
            method: "action_approve_payslip",
            args: [[payslipId]],
            kwargs: {},
        });
        // H3: log approve action
        await rpc("/web/dataset/call_kw", {
            model: "hr.payslip",
            method: "action_create_approval_log",
            args: [[payslipId], "approved"],
            kwargs: { reason: "", stage: "HR/C-Level" },
        });
        this.notification.add("Payslip đã được duyệt.", { type: "success" });
        await this._loadPayslips(this.state.selectedRunId);
        await this._checkAndFinalize(this.state.selectedRunId);
        await this._loadRuns();
    }

    openRefuseModal(payslipId) {
        this.state.refusingPayslip = this.state.payslips.find(p => p.id === payslipId) || null;
    }

    closeRefuseModal() {
        this.state.refusingPayslip = null;
    }

    async onRefuseConfirm(payslipId, reason) {
        // Gọi Python method: vừa cập nhật state, vừa notify C&B
        await rpc("/web/dataset/call_kw", {
            model: "hr.payslip",
            method: "action_refuse_hr_approval",
            args: [[payslipId], reason],
            kwargs: {},
        });
        // Log vào approval history
        await rpc("/web/dataset/call_kw", {
            model: "hr.payslip",
            method: "action_create_approval_log",
            args: [[payslipId], "refused"],
            kwargs: { reason: reason, stage: "HR" },
        });
        this.state.refusingPayslip = null;
        this.notification.add("Payslip đã bị từ chối — C&B sẽ được thông báo.", { type: "warning" });
        await this._loadPayslips(this.state.selectedRunId);
        await this._checkAndFinalize(this.state.selectedRunId);
    }

    /**
     * When all payslips are decided (no pending left), auto-trigger finalization.
     * Works for both HR Approval (waiting_approval) and C-Level (waiting_c_level):
     *   - Refused payslips → cancelled + attendance sheet reverted to 'confirmed'
     *   - Approved payslips → advance to next step
     */
    async _checkAndFinalize(runId) {
        const pending = this.state.payslips.filter(p => p.x_approval_state === "pending").length;
        const refused = this.state.payslips.filter(p => p.x_approval_state === "refused").length;
        // Only finalize when ALL payslips are approved (none pending, none refused/waiting)
        if (pending > 0 || refused > 0 || this.state.payslips.length === 0) return;

        const run = this.state.runs.find(r => r.id === runId);
        const finalizableStates = ["waiting_approval", "waiting_c_level"];
        if (!run || !finalizableStates.includes(run.state)) return;

        await rpc("/web/dataset/call_kw", {
            model: "hr.payslip.run",
            method: "action_finalize_approval",
            args: [[runId]],
            kwargs: {},
        });
        this.notification.add(
            "Hoàn tất phê duyệt. Phiếu bị từ chối đã gửi về bảng công.",
            { type: "info" }
        );
        await this._loadRuns();
    }

    // ── Helpers ───────────────────────────────────────────────────────────────
    get stats() {
        const ps = this.state.payslips;
        return {
            total: ps.length,
            approved: ps.filter(p => p.x_approval_state === "approved").length,
            pending: ps.filter(p => p.x_approval_state === "pending").length,
            refused: ps.filter(p => p.x_approval_state === "refused").length,
        };
    }

    get progressPct() {
        const s = this.stats;
        return s.total ? Math.round((s.approved / s.total) * 100) : 0;
    }

    approvalLabel(state) {
        return { pending: "Chờ duyệt", approved: "Đã duyệt", refused: "Từ chối" }[state] || state;
    }

    approvalClass(state) {
        return { pending: "badge-warning", approved: "badge-success", refused: "badge-danger" }[state] || "badge-secondary";
    }

    stateLabel(state) {
        return { draft: "Nháp", verify: "Đang tính", done: "Xác nhận", validated: "Đã duyệt", paid: "Đã trả" }[state] || state;
    }

    formatMoney(val) {
        if (!val && val !== 0) return "—";
        return new Intl.NumberFormat("vi-VN", { style: "currency", currency: "VND" }).format(val);
    }
}

registry.category("actions").add("payslip_approval_action", PayslipApprovalAction);

