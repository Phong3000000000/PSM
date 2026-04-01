# -*- coding: utf-8 -*-
from odoo import models


class PurchaseOrder(models.Model):
    _inherit = ["purchase.order", "approval.mixin"]

    def button_confirm(self):
        # Minimal override: block confirm until approved
        self._approval_check_before_action("button_confirm")
        return super().button_confirm()

    def _apply_native_transition_after_final_approval(self, request):
        # If submission was intended to confirm, auto-confirm after final approval
        if request and request.pending_action == "button_confirm":
            return self.with_context(approval_engine_bypass=True).button_confirm()
        return super()._apply_native_transition_after_final_approval(request)
