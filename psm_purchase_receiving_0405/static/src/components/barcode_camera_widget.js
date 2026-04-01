/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { scanBarcode } from "@web/core/barcode/barcode_dialog";
import { isBarcodeScannerSupported } from "@web/core/barcode/barcode_video_scanner";
import { Component } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

/**
 * Reusable Camera Barcode Widget
 * 
 * Provides a button to open camera-based barcode scanner on supported devices.
 * Falls back gracefully if camera is not available.
 */
export class BarcodeCameraWidget extends Component {
    static template = "psm_purchase_receiving.BarcodeCameraWidget";
    static props = {
        onBarcodeScanned: { type: Function },
        placeholder: { type: String, optional: true },
        buttonClass: { type: String, optional: true },
    };

    setup() {
        this.notification = useService("notification");
        this.isBarcodeScannerSupported = isBarcodeScannerSupported();
        this.scanBarcode = () => scanBarcode(this.env, this.facingMode);
    }

    get facingMode() {
        // "environment" = camera sau (cho mobile)
        // "user" = camera trước
        return "environment";
    }

    get placeholder() {
        return this.props.placeholder || _t("Quét mã");
    }

    get buttonClass() {
        return this.props.buttonClass || "btn-primary";
    }

    /**
     * Open camera scanner when button is clicked
     */
    async openCameraScanner() {
        let error = null;
        let barcode = null;

        try {
            barcode = await this.scanBarcode();
        } catch (err) {
            error = err.message;
            console.error("Camera scanning error:", err);
        }

        if (barcode) {
            // Gọi callback với barcode đã quét
            this.props.onBarcodeScanned(barcode);

            // Haptic feedback trên mobile (nếu hỗ trợ)
            if ("vibrate" in window.navigator) {
                window.navigator.vibrate(100);
            }
        } else {
            this.notification.add(error || _t("Vui lòng quét lại!"), {
                type: "warning",
            });
        }
    }
}
