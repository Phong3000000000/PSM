from odoo import models


class AccountMove(models.Model):
    _inherit = ["account.move", "approval.mixin"]

    def action_post(self):
        # Minimal override: block posting until approved
        self._approval_check_before_action("action_post")
        return super().action_post()

    def _apply_native_transition_after_final_approval(self, request):
        # Auto-post after final approval if pending action was post
        if request and request.pending_action == "action_post":
            return self.with_context(approval_engine_bypass=True).action_post()
        return super()._apply_native_transition_after_final_approval(request)