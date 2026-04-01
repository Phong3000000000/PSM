/** @odoo-module **/

import { Component, onWillStart, onMounted, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

export class PsmDbSyncDashboard extends Component {
    static template = "psm_db_sync.dashboard_template";

    setup() {
        this.rpc = useService("rpc");
        this.notification = useService("notification");
        this.action = useService("action");
        this.state = useState({
            loading: true,
            data: {
                overview: {},
                recent_logs: [],
                connections: []
            },
            showAllLogs: false,
            maxLogsDisplay: 5
        });

        onWillStart(async () => {
            await this.loadDashboardData();
        });

        onMounted(() => {
            this.setupAutoRefresh();
        });
    }

    async loadDashboardData() {
        try {
            this.state.loading = true;
            const result = await this.rpc("/psm_db_sync/dashboard/data", {});

            if (result.success) {
                this.state.data = result.data;
            } else {
                this.notification.add(
                    `Lỗi tải dữ liệu dashboard: ${result.error}`,
                    { type: "danger" }
                );
            }
        } catch (error) {
            console.error("Error loading dashboard data:", error);
            this.notification.add(
                "Lỗi tải dữ liệu dashboard",
                { type: "danger" }
            );
        } finally {
            this.state.loading = false;
        }
    }

    get displayedLogs() {
        if (this.state.showAllLogs) {
            return this.state.data.recent_logs;
        }
        return this.state.data.recent_logs.slice(0, this.state.maxLogsDisplay);
    }

    get hasMoreLogs() {
        return this.state.data.recent_logs.length > this.state.maxLogsDisplay;
    }

    toggleShowAllLogs() {
        this.state.showAllLogs = !this.state.showAllLogs;
    }

    async viewAllLogs() {
        await this.action.doAction({
            type: 'ir.actions.act_window',
            res_model: 'psm.db.sync.log',
            views: [[false, 'list'], [false, 'form']],
            name: 'Nhật ký đồng bộ',
            target: 'current',
        });
    }

    getDbTypeIcon(dbType) {
        const icons = {
            'mysql': 'fa fa-database text-primary',
            'postgresql': 'fa fa-database text-info',
            'mssql': 'fa fa-database text-warning',
            'oracle': 'fa fa-database text-danger',
            'mariadb': 'fa fa-database text-success'
        };
        return icons[dbType] || 'fa fa-database text-muted';
    }

    getLogStatusIcon(status) {
        const icons = {
            'running': 'fa fa-spinner fa-spin text-primary',
            'completed': 'fa fa-check-circle text-success',
            'failed': 'fa fa-times-circle text-danger',
            'cancelled': 'fa fa-exclamation-triangle text-warning'
        };
        return icons[status] || 'fa fa-circle text-muted';
    }

    formatDateTime(dateTimeStr) {
        if (!dateTimeStr) return '';
        try {
            return new Date(dateTimeStr).toLocaleString('vi-VN', {
                year: 'numeric',
                month: '2-digit',
                day: '2-digit',
                hour: '2-digit',
                minute: '2-digit'
            });
        } catch (e) {
            return dateTimeStr;
        }
    }

    setupAutoRefresh() {
        // Refresh dashboard every 30 seconds
        setInterval(() => {
            if (!this.state.loading) {
                this.loadDashboardData();
            }
        }, 30000);
    }

    async testConnection(connectionId) {
        try {
            const result = await this.rpc("/psm_db_sync/connection/test", {
                connection_id: connectionId
            });

            if (result.success) {
                this.notification.add(result.message, { type: "success" });
                await this.loadDashboardData(); // Refresh data
            } else {
                this.notification.add(`Lỗi kết nối: ${result.error}`, { type: "danger" });
            }
        } catch (error) {
            console.error("Error testing connection:", error);
            this.notification.add("Lỗi kiểm tra kết nối", { type: "danger" });
        }
    }

    async startSync(syncId) {
        try {
            const result = await this.rpc("/psm_db_sync/sync/start", {
                sync_id: syncId
            });

            if (result.success) {
                this.notification.add(result.message, { type: "success" });
                await this.loadDashboardData(); // Refresh data
            } else {
                this.notification.add(`Lỗi đồng bộ: ${result.error}`, { type: "danger" });
            }
        } catch (error) {
            console.error("Error starting sync:", error);
            this.notification.add("Lỗi bắt đầu đồng bộ", { type: "danger" });
        }
    }
}

registry.category("actions").add("psm_db_sync_dashboard", PsmDbSyncDashboard);