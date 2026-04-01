/** @odoo-module **/

import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { registry } from "@web/core/registry";
import { STATIC_ACTIONS_GROUP_NUMBER } from "@web/search/action_menus/action_menus";
import { _t } from "@web/core/l10n/translation";

import { Component } from "@odoo/owl";

const cogMenuRegistry = registry.category("cogMenu");

/**
 * 'Sync Data' menu
 *
 * This component is used to sync data from external database.
 * @extends Component
 */
export class SyncData extends Component {
    static template = "psm_db_sync.SyncData";
    static components = { DropdownItem };

    //---------------------------------------------------------------------
    // Protected
    //---------------------------------------------------------------------

    async onSyncData() {
        try {
            const resModel = this.env.searchModel.resModel;
            console.log('🚀 Checking sync options for model:', resModel);

            // Tìm sync tasks cho model này (thay vì mapping)
            const syncTasks = await this.env.services.rpc("/web/dataset/call_kw", {
                model: "psm.db.sync",
                method: "search_read",
                args: [[
                    ["target_model", "=", resModel],
                    ["active", "=", true]
                ]],
                kwargs: {
                    fields: ["id", "name", "execution_type", "cron_id", "state", "mapping_model_id"]
                }
            });

            if (syncTasks.length === 0) {
                this.env.services.notification.add(
                    _t("Không tìm thấy nhiệm vụ đồng bộ cho model này"),
                    { type: "warning" }
                );
                return;
            }

            console.log('📋 Found sync tasks:', syncTasks);

            // LOGIC THÔNG MINH: Ưu tiên scheduled tasks có cron
            const scheduledTasks = syncTasks.filter(task =>
                task.execution_type === 'scheduled' &&
                task.cron_id &&
                task.cron_id[0] &&
                task.state !== 'running'
            );

            if (scheduledTasks.length > 0) {
                console.log('⚡ Found scheduled task, running automatically:', scheduledTasks[0]);
                await this._runScheduledTask(scheduledTasks[0]);
            } else {
                console.log('🧙‍♂️ No scheduled task, opening wizard');
                await this._openSyncWizard(syncTasks, resModel);
            }

        } catch (error) {
            console.error("❌ Error in sync data:", error);
            this.env.services.notification.add(
                _t("Lỗi đồng bộ dữ liệu: ") + error.message,
                { type: "danger" }
            );
        }
    }

    async _runScheduledTask(scheduledTask) {
        try {
            // Hiển thị notification bắt đầu
            this.env.services.notification.add(
                _t("🚀 Bắt đầu đồng bộ: ") + scheduledTask.name,
                { type: "info" }
            );

            console.log('🏃‍♂️ Running scheduled sync task:', scheduledTask.id);

            // Gọi action_sync_now trên sync task
            const result = await this.env.services.rpc("/web/dataset/call_kw", {
                model: "psm.db.sync",
                method: "action_sync_now",
                args: [scheduledTask.id],
                kwargs: {}
            });

            console.log('✅ Sync task result:', result);

            // Xử lý kết quả
            if (result && result.params) {
                this.env.services.notification.add(
                    result.params.message,
                    { type: result.params.type || "success" }
                );
            } else {
                this.env.services.notification.add(
                    _t("✅ Đã khởi động đồng bộ thành công"),
                    { type: "success" }
                );
            }

        } catch (error) {
            console.error("❌ Error running scheduled task:", error);
            this.env.services.notification.add(
                _t("❌ Lỗi chạy nhiệm vụ đồng bộ: ") + error.message,
                { type: "danger" }
            );
        }
    }

    async _openSyncWizard(syncTasks, resModel) {
        try {
            // Lấy mapping từ sync task đầu tiên
            const syncTask = syncTasks[0];
            const mappingId = syncTask.mapping_model_id[0];

            console.log('🧙‍♂️ Opening wizard with mapping:', mappingId);

            // Mở wizard với format action đúng
            const action = {
                type: "ir.actions.act_window",
                name: _t("Đồng bộ thủ công"),
                res_model: "psm.db.wizard",
                view_mode: "form",
                views: [[false, "form"]],
                target: "new",
                context: {
                    default_mapping_model_id: mappingId,
                    default_target_model: resModel,
                    from_action_menu: true,
                    available_sync_tasks: syncTasks.map(t => t.id)
                }
            };

            console.log('🎯 Action to execute:', action);
            await this.env.services.action.doAction(action);

        } catch (error) {
            console.error("❌ Error opening sync wizard:", error);
            this.env.services.notification.add(
                _t("Lỗi mở wizard đồng bộ: ") + error.message,
                { type: "danger" }
            );
        }
    }
}

export const syncDataItem = {
    Component: SyncData,
    groupNumber: STATIC_ACTIONS_GROUP_NUMBER,
    isDisplayed: async (env) => {
        // Chỉ hiện khi:
        // 1. Đang ở list view
        // 2. User có quyền
        // 3. Model này có sync tasks
        if (env.config.viewType !== "list") {
            return false;
        }

        try {
            // Kiểm tra quyền DB Sync
            const hasDbSyncGroup = await env.model.user.hasGroup("psm_db_sync.group_psm_db_sync_user");
            if (!hasDbSyncGroup) {
                return false;
            }

            // Kiểm tra có sync task cho model này không
            const resModel = env.searchModel.resModel;
            const count = await env.services.rpc("/web/dataset/call_kw", {
                model: "psm.db.sync",
                method: "search_count",
                args: [[
                    ["target_model", "=", resModel],
                    ["active", "=", true]
                ]],
                kwargs: {}
            });

            return count > 0;
        } catch (error) {
            console.error("Error checking sync availability:", error);
            return false;
        }
    },
};

cogMenuRegistry.add("sync-data-menu", syncDataItem, { sequence: 15 });