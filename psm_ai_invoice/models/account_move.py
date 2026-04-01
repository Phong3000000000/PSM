class AccountMove(models.Model):
    _inherit = "account.move"

    @api.model
    def _get_or_create_service(self, product_name):

        product = self.env["product.product"].search([("name", "=", product_name)], limit=1)
        if product:
            return product


        auto_add_service = self.env["ir.config_parameter"].sudo().get_param("psm_ai_invoice.auto_add_service")
        if not auto_add_service or auto_add_service in ["False", False]:
            raise UserError(_("Product '%s' not found, and auto-add service is disabled.") % product_name)


        product = self.env["product.product"].create({
            "name": product_name,
            "type": "service",
            "invoice_policy": "order",
            "sale_ok": False,
            "purchase_ok": True,
            "default_code": product_name[:32],
        })
        return product

    def action_process_ai_invoice(self, ai_data):
  
        for move in self:
            for line in ai_data.get("lines", []):
                product_name = line.get("product") or _("Unnamed Service")
                product = move._get_or_create_service(product_name)

                self.env["account.move.line"].create({
                    "move_id": move.id,
                    "product_id": product.id,
                    "name": product_name,
                    "quantity": line.get("qty", 1),
                    "price_unit": line.get("price", 0.0),
                })