/** @odoo-module **/

/**
 * Inline Barcode Action Widget
 * 
 * A custom field widget that displays an inline barcode scanner.
 * When user clicks "Scan", camera expands below the input field (inline, not popup).
 * 
 * Usage in XML:
 *   <field name="scan_filter_product_id" widget="inline_barcode_action"/>
 */

import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component, useState, useRef, xml } from "@odoo/owl";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { BarcodeVideoScanner } from "@web/core/barcode/barcode_video_scanner";

export class InlineBarcodeField extends Component {
    static template = xml`
        <div class="o_inline_barcode_field w-100">
            <!-- ERROR MESSAGE -->
            <t t-if="state.cameraError">
                <div class="alert alert-warning py-1 mb-2">
                    <i class="fa fa-exclamation-triangle me-2"/>
                    <span t-esc="state.cameraError"/>
                </div>
            </t>
            
            <!-- INPUT + BUTTONS -->
            <div class="input-group">
                <input type="text" 
                       class="form-control" 
                       t-on-keydown="onKeydown"
                       placeholder="Nhập mã hoặc bấm Scan..."
                       t-ref="input-barcode"/>
                
                <button class="btn btn-primary" t-on-click="toggleCamera" title="Bật/Tắt Camera">
                    <i class="fa fa-camera"/>
                    <span class="ms-1 d-none d-md-inline" t-if="state.isScanning">Đóng</span>
                    <span class="ms-1 d-none d-md-inline" t-else="">Scan</span>
                </button>
                
                <button class="btn btn-secondary" t-on-click="onSubmit" title="Tìm">
                    <i class="fa fa-search"/>
                </button>
                
                <t t-if="props.record.data[props.name]">
                    <button class="btn btn-outline-danger" t-on-click="clearFilter" title="Bỏ lọc">
                        <i class="fa fa-times"/>
                    </button>
                </t>
            </div>

            <!-- INLINE CAMERA (expands below input when active) -->
            <t t-if="state.isScanning">
                <div class="mt-2 border rounded bg-black position-relative overflow-hidden" 
                     style="height: 280px; width: 100%;">
                    
                    <BarcodeVideoScanner 
                        facingMode="'environment'"
                        onResult="(barcode) => this.onBarcodeScanned({detail: {barcode}})"
                        onError="(error) => this.notification.add(error.message, {type: 'danger'})"
                    />

                    <!-- Laser scanning line effect -->
                    <div class="position-absolute top-50 start-0 w-100 border-top border-danger border-2 opacity-75" 
                         style="z-index: 10;"/>
                    
                    <!-- Close button overlay -->
                    <button class="btn btn-sm btn-danger position-absolute top-0 end-0 m-2" 
                            style="z-index: 20;"
                            t-on-click="toggleCamera">
                        <i class="fa fa-times"/> Đóng
                    </button>
                </div>
            </t>
        </div>
    `;

    static components = { BarcodeVideoScanner };

    static props = {
        ...standardFieldProps,
    };

    setup() {
        this.orm = useService("orm");
        this.notification = useService("notification");

        this.state = useState({
            isScanning: false,
            cameraError: null,
        });

        this.inputRef = useRef("input-barcode");
    }

    /**
     * Toggle camera on/off (inline, not popup)
     */
    toggleCamera() {
        if (this.state.isScanning) {
            this.state.isScanning = false;
        } else {
            // Check HTTPS requirement
            if (window.location.protocol !== 'https:' &&
                window.location.hostname !== 'localhost' &&
                window.location.hostname !== '127.0.0.1') {
                this.state.cameraError = "Camera cần HTTPS hoặc localhost";
                return;
            }
            this.state.isScanning = true;
        }
    }

    /**
     * Called when barcode is scanned via camera
     */
    async onBarcodeScanned(event) {
        const { barcode } = event.detail;
        if (barcode) {
            // Vibrate feedback
            if (window.navigator.vibrate) window.navigator.vibrate(100);

            this.state.isScanning = false; // Auto-close camera

            // Apply filter with scanned barcode
            await this.applyBarcodeFilter(barcode);
        }
    }

    /**
     * Handle manual input and Enter key
     */
    async onKeydown(ev) {
        if (ev.key === "Enter") {
            const val = ev.target.value.trim();
            if (val) {
                await this.applyBarcodeFilter(val);
            }
        }
    }

    /**
     * Handle manual submit button click
     */
    async onSubmit() {
        const val = this.inputRef.el?.value?.trim();
        if (val) {
            await this.applyBarcodeFilter(val);
        }
    }

    /**
     * Apply barcode filter - find product and filter rows
     */
    async applyBarcodeFilter(barcode) {
        try {
            // Search for product by barcode or default_code
            const products = await this.orm.searchRead(
                "product.product",
                ['|', ["barcode", "=", barcode], ["default_code", "=", barcode]],
                ["id", "display_name"],
                { limit: 1 }
            );

            if (products.length > 0) {
                const product = products[0];

                // Update field value via props.record.update
                await this.props.record.update({ [this.props.name]: product.id });

                // Filter rows visually
                this.filterRowsVisual(product.display_name);

                this.notification.add("Đã lọc: " + product.display_name, { type: "success" });
            } else {
                this.notification.add("Không tìm thấy sản phẩm: " + barcode, { type: "warning" });
            }
        } catch (e) {
            console.error("Barcode filter error:", e);
            this.notification.add("Lỗi: " + e.message, { type: "danger" });
        }
    }

    /**
     * Filter operation rows visually (DOM manipulation)
     */
    filterRowsVisual(productName) {
        const rows = document.querySelectorAll('.o_notebook .tab-pane.active .o_list_table .o_data_row');
        if (rows.length === 0) return;

        rows.forEach(function (row) {
            const rowText = row.innerText || "";
            if (rowText.toLowerCase().includes(productName.toLowerCase())) {
                row.style.display = "";
            } else {
                row.style.display = "none";
            }
        });
    }

    /**
     * Clear filter
     */
    async clearFilter() {
        await this.props.record.update({ [this.props.name]: false });

        // Show all rows
        const rows = document.querySelectorAll('.o_notebook .tab-pane .o_list_table .o_data_row');
        rows.forEach(function (row) {
            row.style.display = "";
        });

        // Clear input
        if (this.inputRef.el) {
            this.inputRef.el.value = "";
        }

        this.notification.add("Đã bỏ lọc", { type: "info" });
    }
}

// Register as Odoo field widget (correct pattern)
export const inlineBarcodeActionField = {
    component: InlineBarcodeField,
    displayName: _t("Inline Barcode Scanner"),
    supportedTypes: ["many2one"],
    extractProps: ({ attrs }) => ({}),
};

registry.category("fields").add("inline_barcode_action", inlineBarcodeActionField);
