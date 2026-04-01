from odoo import api, fields, models, _

class AccountMove(models.Model):
    _inherit = "account.move"

    psm_ai_last_result = fields.Text(readonly=True)

    def action_psm_ai_analyze(self):
        """Button on bill form: analyze first attachment via AI."""
        self.ensure_one()
        atta = self.env["ir.attachment"].search([
            ("res_model", "=", "account.move"),
            ("res_id", "=", self.id),
            ("type", "=", "binary")
        ], limit=1)
        if not atta:
            return {"warning": {"title": _("No Attachment"), "message": _("Please attach an invoice file first.")}}
        result = self.env["psm.ai.invoice.service"].process_attachment(atta, link_to_move_id=self.id)
        self.message_post(body=_("AI processed invoice."))
        self.write({"psm_ai_last_result": str(result)})
        return True
