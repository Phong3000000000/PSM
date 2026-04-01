/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { session } from "@web/session";
import { SubscriptionManager } from "@web_enterprise/webclient/home_menu/enterprise_subscription_service";

const { DateTime } = luxon;

// Patch session object directly to fake expiration data
// This is critical because SubscriptionManager reads from session in constructor
Object.assign(session, {
    expiration_date: "2099-12-31 23:59:59",
    expiration_reason: "manual",
    warning: false,
});

// Patch SubscriptionManager to override computed properties and methods
patch(SubscriptionManager.prototype, {
    get daysLeft() {
        return 27375; // ~75 years
    },

    get unregistered() {
        return false;
    },

    get formattedExpirationDate() {
        return "December 31, 2099";
    },

    // Override hideWarning to ensure warning stays hidden
    hideWarning() {
        this.isWarningHidden = true;
    },

    // Override checkStatus to prevent real checks
    async checkStatus() {
        this.lastRequestStatus = "update";
        this.expirationDate = DateTime.utc().plus({ years: 75 });
        return Promise.resolve();
    },

    // Override submitCode to fake success
    async submitCode(enterpriseCode) {
        this.lastRequestStatus = "success";
        this.expirationDate = DateTime.utc().plus({ years: 75 });
        return Promise.resolve();
    },
});
