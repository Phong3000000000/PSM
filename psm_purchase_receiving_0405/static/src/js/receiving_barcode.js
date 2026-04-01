/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { ListController } from "@web/views/list/list_controller";
import { FormController } from "@web/views/form/form_controller";
import { KanbanController } from "@web/views/kanban/kanban_controller";
import { listView } from "@web/views/list/list_view";
import { formView } from "@web/views/form/form_view";
import { kanbanView } from "@web/views/kanban/kanban_view";
import { registry } from "@web/core/registry";
import { useBus, useService } from "@web/core/utils/hooks";
import { Dialog } from "@web/core/dialog/dialog";
import { Component, useState, useRef, onMounted, xml } from "@odoo/owl";

// 1. IMPORT QUAN TRỌNG: Component Camera cho trình duyệt
import { BarcodeVideoScanner } from "@web/core/barcode/barcode_video_scanner";

// ============================================================
// 1. ĐỊNH NGHĨA COMPONENT MANUAL BARCODE SCANNER (WEB CAM)
// ============================================================
export class ManualBarcodeScanner extends Component {
    setup() {
        this.state = useState({
            barcode: "",
            isScanning: false, // Biến bật/tắt camera
            cameraError: null,
        });
        this.inputRef = useRef("input");
        this.notification = useService("notification");

        onMounted(() => {
            // Auto-start camera if prop is set
            if (this.props.autoStartCamera) {
                this.tryStartCamera();
            }
            if (this.inputRef.el) this.inputRef.el.focus();
        });
    }

    /**
     * Try to start camera (check HTTPS first)
     */
    tryStartCamera() {
        if (window.location.protocol !== 'https:' &&
            window.location.hostname !== 'localhost' &&
            window.location.hostname !== '127.0.0.1') {
            this.state.cameraError = _t("Camera cần HTTPS hoặc localhost");
            return false;
        }
        this.state.isScanning = true;
        return true;
    }

    /**
     * Bật/Tắt Camera Webcam
     */
    toggleCamera() {
        if (this.state.isScanning) {
            this.state.isScanning = false;
        } else {
            this.tryStartCamera();
        }
    }

    /**
     * Sự kiện khi Camera quét được mã
     */
    onBarcodeVideoScanned(event) {
        const { barcode } = event.detail;
        if (barcode) {
            // Rung nhẹ
            if ("vibrate" in window.navigator) window.navigator.vibrate(100);

            this.state.barcode = barcode;
            this.state.isScanning = false; // Tắt cam sau khi quét xong
            this.confirm();
        }
    }

    async confirm() {
        if (this.state.barcode) {
            // Pass close callback to controller - let it close after action completes
            await this.props.onResult(this.state.barcode, this.props.close);
        } else {
            this.notification.add(_t("Vui lòng nhập mã barcode"), { type: "danger" });
        }
    }

    onKeydown(ev) {
        if (ev.key === "Enter") {
            this.confirm();
        }
    }
}

ManualBarcodeScanner.template = xml`
    <Dialog title="props.title || 'Quét Barcode'" contentClass="'o_barcode_manual_dialog'" size="'md'">
        <div class="p-3">
            <!-- CAMERA ERROR MESSAGE -->
            <t t-if="state.cameraError">
                <div class="alert alert-warning mb-3">
                    <i class="fa fa-exclamation-triangle me-2"/>
                    <span t-esc="state.cameraError"/>
                </div>
            </t>
            
            <!-- VÙNG CAMERA: Hiện khi isScanning = true -->
            <t t-if="state.isScanning">
                <div class="mb-3 border rounded overflow-hidden position-relative bg-black" style="height: 280px;">
                    <BarcodeVideoScanner 
                        facingMode="'environment'"
                        onResult="(barcode) => this.onBarcodeVideoScanned({detail: {barcode}})"
                        onError="(error) => this.notification.add(error.message, {type: 'danger'})"
                    />
                    <button class="btn btn-sm btn-danger position-absolute top-0 end-0 m-2" 
                            style="z-index: 999;"
                            t-on-click="toggleCamera">
                        <i class="fa fa-times"/> Tắt Camera
                    </button>
                </div>
            </t>

            <!-- VÙNG NHẬP LIỆU -->
            <div class="mb-3">
                <label class="form-label" t-esc="props.placeholder || 'Nhập hoặc quét mã'"/>
                <div class="input-group">
                    <input type="text" 
                           class="form-control" 
                           t-model="state.barcode" 
                           t-ref="input"
                           t-on-keydown="onKeydown"
                           placeholder="Nhập mã..."/>
                    
                    <!-- Nút Bật Camera - CHỈ HIỆN KHI KHÔNG AUTO-START -->
                    <t t-if="!props.autoStartCamera">
                        <button class="btn btn-secondary" t-on-click="toggleCamera">
                            <i class="fa fa-camera"/> 
                            <span class="ms-1" t-if="!state.isScanning">Mở Cam</span>
                            <span class="ms-1" t-else="">Tắt Cam</span>
                        </button>
                    </t>
                </div>
            </div>
        </div>
        <t t-set-slot="footer">
            <button class="btn btn-primary" t-on-click="confirm">Xác nhận</button>
            <button class="btn btn-secondary" t-on-click="props.close">Đóng</button>
        </t>
    </Dialog>
`;
// Đăng ký component con BarcodeVideoScanner
ManualBarcodeScanner.components = { Dialog, BarcodeVideoScanner };

// ============================================================
// 2. GLOBAL FAB MANAGER FOR PURCHASE VIEWS
// ============================================================

/**
 * Singleton quản lý FAB cho tất cả Purchase views (List, Kanban)
 * Inject FAB một lần duy nhất và reuse cho mọi view
 */
class PurchaseFABManager {
    constructor() {
        this.fab = null;
        this.activeController = null;
    }

    injectFAB() {
        // Chỉ inject trên mobile
        if (window.innerWidth > 767) return;

        // Đã tồn tại rồi, không inject lại
        if (this.fab && document.body.contains(this.fab)) return;

        // Tạo FAB
        this.fab = document.createElement('button');
        this.fab.className = 'o_mobile_fab o_purchase_scan_fab btn btn-primary rounded-circle shadow';
        this.fab.style.position = 'fixed';
        this.fab.style.bottom = '20px';
        this.fab.style.right = '20px';
        this.fab.style.width = '56px';
        this.fab.style.height = '56px';
        this.fab.style.zIndex = '9999';
        this.fab.title = 'Scan Receipt';
        this.fab.innerHTML = '<i class="fa fa-barcode fa-lg"></i>';

        // Click handler sẽ gọi active controller
        this.fab.addEventListener('click', () => {
            if (this.activeController && this.activeController.openBarcodeScanner) {
                this.activeController.openBarcodeScanner();
            }
        });

        document.body.appendChild(this.fab);
    }

    setActiveController(controller) {
        this.activeController = controller;
    }

    removeFAB() {
        if (this.fab && document.body.contains(this.fab)) {
            document.body.removeChild(this.fab);
            this.fab = null;
        }
    }
}

// Singleton instance
const purchaseFABManager = new PurchaseFABManager();

// ============================================================
// 3. PURCHASE BARCODE LIST CONTROLLER
// ============================================================

export class PurchaseBarcodeListController extends ListController {
    setup() {
        super.setup();
        this.actionService = useService("action");
        this.notification = useService("notification");
        this.orm = useService("orm");
        this.barcodeService = useService("barcode");
        this.dialogService = useService("dialog");

        useBus(this.barcodeService.bus, "barcode_scanned", (event) => this.onBarcodeScanned(event));

        onMounted(() => {
            this.injectMobileFAB();
        });
    }

    injectMobileFAB() {
        if (window.innerWidth > 767) return;
        if (document.querySelector('.o_purchase_scan_fab')) return;

        const fab = document.createElement('button');
        fab.className = 'o_mobile_fab o_purchase_scan_fab btn btn-primary rounded-circle shadow';
        fab.style.position = 'fixed';
        fab.style.bottom = '20px';
        fab.style.right = '20px';
        fab.style.width = '56px';
        fab.style.height = '56px';
        fab.style.zIndex = '9999';
        fab.title = 'Scan Receipt';
        fab.innerHTML = '<i class="fa fa-barcode fa-lg"></i>';
        fab.addEventListener('click', () => this.openBarcodeScanner());

        document.body.appendChild(fab);
    }

    async onBarcodeScanned(event) {
        const { barcode } = event.detail;
        if (barcode) {
            await this.searchAndOpenPicking(barcode);
        }
    }

    async searchAndOpenPicking(barcode) {
        try {
            console.log("[DEBUG] Calling search_picking_by_barcode with:", barcode);

            const result = await this.orm.call(
                "stock.picking",
                "search_picking_by_barcode",
                [barcode]
            );

            console.log("[DEBUG] Server response:", result);

            if (result && result.warning) {
                console.log("[DEBUG] Warning result:", result.message);
                this.notification.add(result.message, {
                    type: "warning",
                    title: _t("Receipt Not Found"),
                });
            } else if (result && result.type === 'ir.actions.act_window') {
                console.log("[DEBUG] Executing action:", result);

                try {
                    await this.actionService.doAction(result);
                    console.log("[DEBUG] Action executed successfully");
                } catch (actionError) {
                    console.error("[ERROR] Failed to execute action:", actionError);
                    console.error("[ERROR] Action object was:", result);
                    throw actionError; // Re-throw để bắt ở outer catch
                }
            } else {
                console.log("[DEBUG] Unexpected response format:", result);
                this.notification.add(_t("No receipt found or invalid response."), {
                    type: "warning",
                    title: _t("Not Found"),
                });
            }
        } catch (error) {
            console.error("[ERROR] Barcode Scanner Error:", error);
            console.error("[ERROR] Error details:", {
                message: error.message,
                stack: error.stack,
                cause: error.cause,
                name: error.name
            });

            this.notification.add(_t("System Error: ") + (error.message || String(error)), {
                type: "danger",
                title: _t("Error"),
            });
        }
    }

    async openBarcodeScanner() {
        this.dialogService.add(ManualBarcodeScanner, {
            title: _t("Tìm Phiếu Nhập"),
            placeholder: _t("Nhập mã phiếu nhập (VD: WH/IN/00001)"),
            onResult: async (barcode, closeDialog) => {
                if (barcode) {
                    await this.searchAndOpenPicking(barcode);
                    // Close dialog AFTER action completes
                    if (closeDialog) closeDialog();
                }
            },
        });
    }
}

export const purchaseBarcodeListView = {
    ...listView,
    Controller: PurchaseBarcodeListController,
    buttonTemplate: "psm_purchase_receiving.ListButtons",
};

registry.category("views").add("purchase_barcode_list", purchaseBarcodeListView);

// ============================================================
// 2B. PURCHASE BARCODE KANBAN CONTROLLER (FOR MOBILE)
// ============================================================

export class PurchaseBarcodeKanbanController extends KanbanController {
    setup() {
        super.setup();
        this.actionService = useService("action");
        this.notification = useService("notification");
        this.orm = useService("orm");
        this.barcodeService = useService("barcode");
        this.dialogService = useService("dialog");

        // Listen to keyboard scanner
        useBus(this.barcodeService.bus, "barcode_scanned", (event) => this.onBarcodeScanned(event));

        // Inject FAB for mobile
        onMounted(() => {
            this.injectMobileFAB();
        });
    }

    injectMobileFAB() {
        if (window.innerWidth > 767) return;
        if (document.querySelector('.o_purchase_scan_fab')) return;

        const fab = document.createElement('button');
        fab.className = 'o_mobile_fab o_purchase_scan_fab btn btn-primary rounded-circle shadow';
        fab.style.position = 'fixed';
        fab.style.bottom = '20px';
        fab.style.right = '20px';
        fab.style.width = '56px';
        fab.style.height = '56px';
        fab.style.zIndex = '9999';
        fab.title = 'Scan Receipt';
        fab.innerHTML = '<i class="fa fa-barcode fa-lg"></i>';
        fab.addEventListener('click', () => this.openBarcodeScanner());

        document.body.appendChild(fab);
    }

    async onBarcodeScanned(event) {
        const { barcode } = event.detail;
        if (barcode) {
            await this.searchAndOpenPicking(barcode);
        }
    }

    async searchAndOpenPicking(barcode) {
        try {
            const result = await this.orm.call(
                "stock.picking",
                "search_picking_by_barcode",
                [barcode]
            );

            if (result && result.warning) {
                this.notification.add(result.message, {
                    type: "warning",
                    title: _t("Receipt Not Found"),
                });
            } else if (result && result.type === 'ir.actions.act_window') {
                await this.actionService.doAction(result);
            } else {
                this.notification.add(_t("No receipt found or invalid response."), {
                    type: "warning",
                    title: _t("Not Found"),
                });
            }
        } catch (error) {
            console.error("Barcode Scanner Error:", error);
            this.notification.add(_t("System Error: ") + (error.message || String(error)), {
                type: "danger",
                title: _t("Error"),
            });
        }
    }

    async openBarcodeScanner() {
        this.dialogService.add(ManualBarcodeScanner, {
            title: _t("Tìm Phiếu Nhập"),
            placeholder: _t("Nhập mã phiếu nhập (VD: WH/IN/00001)"),
            onResult: async (barcode, closeDialog) => {
                if (barcode) {
                    await this.searchAndOpenPicking(barcode);
                    if (closeDialog) closeDialog();
                }
            },
        });
    }
}

export const purchaseBarcodeKanbanView = {
    ...kanbanView,
    Controller: PurchaseBarcodeKanbanController,
};

registry.category("views").add("purchase_barcode_kanban", purchaseBarcodeKanbanView);

// ============================================================
// 3. STOCK PICKING BARCODE FILTER CONTROLLER
// ============================================================

export class StockPickingBarcodeFilterController extends FormController {
    setup() {
        super.setup();
        this.orm = useService("orm");
        this.notification = useService("notification");
        this.dialogService = useService("dialog");
    }

    async beforeExecuteActionButton(clickParams) {
        if (clickParams.name === "btn_scan_barcode_js") {
            this.openBarcodeScanner();
            return false;
        }
        if (clickParams.name === "action_clear_filter") {
            this.clearFilterVisual();
            return super.beforeExecuteActionButton(...arguments);
        }
        return super.beforeExecuteActionButton(...arguments);
    }

    /**
     * Open barcode scanner dialog with AUTO-START camera
     */
    openBarcodeScanner() {
        this.dialogService.add(ManualBarcodeScanner, {
            title: _t("Lọc Sản Phẩm"),
            placeholder: _t("Nhập mã sản phẩm"),
            autoStartCamera: true, // <-- Auto-open camera, hide "Mở Cam" button
            onResult: async (barcode, closeDialog) => {
                if (barcode) {
                    await this.applyFilter(barcode);
                    // Close dialog after filter is applied
                    if (closeDialog) closeDialog();
                }
            },
        });
    }

    async applyFilter(barcode) {
        try {
            let product = null;
            let products = await this.orm.searchRead(
                "product.product",
                [["barcode", "=", barcode]],
                ["id", "display_name"]
            );

            if (!products || products.length === 0) {
                products = await this.orm.searchRead(
                    "product.product",
                    [["default_code", "=", barcode]],
                    ["id", "display_name"]
                );
            }

            if (products && products.length > 0) {
                product = products[0];
            } else {
                this.notification.add(_t("Không tìm thấy sản phẩm: ") + barcode, { type: "warning" });
                return;
            }

            await this.model.root.update({
                scan_filter_product_id: product.id,
            });

            this.filterRowsVisual(product.display_name);
            this.notification.add(_t("Đã lọc: ") + product.display_name, { type: "success" });

        } catch (error) {
            console.error(error);
            this.notification.add(_t("Lỗi: ") + error.message, { type: "danger" });
        }
    }

    filterRowsVisual(productName) {
        const rows = document.querySelectorAll('.o_notebook .tab-pane.active .o_list_table .o_data_row');
        if (rows.length === 0) return;

        let foundCount = 0;
        rows.forEach(row => {
            const rowText = row.innerText || "";
            if (rowText.toLowerCase().includes(productName.toLowerCase())) {
                row.style.display = "";
                foundCount++;
            } else {
                row.style.display = "none";
            }
        });
    }

    clearFilterVisual() {
        const rows = document.querySelectorAll('.o_notebook .tab-pane .o_list_table .o_data_row');
        rows.forEach(row => {
            row.style.display = "";
        });
    }
}

export const stockPickingBarcodeFilterView = {
    ...formView,
    Controller: StockPickingBarcodeFilterController,
};

registry.category("views").add("stock_picking_barcode_filter", stockPickingBarcodeFilterView);