from odoo import models


class ProductSupplierinfo(models.Model):
    _inherit = "product.supplierinfo"

    def _exact_duplicate_key(self):
        """Fields whose equality means rows are commercially identical."""
        self.ensure_one()
        return (
            self.partner_id.id,
            self.product_tmpl_id.id,
            self.product_id.id or False,
            self.product_name or "",
            self.product_code or "",
            self.sequence,
            self.product_uom_id.id,
            self.min_qty,
            self.price,
            self.currency_id.id,
            self.company_id.id or False,
            self.date_start or False,
            self.date_end or False,
            self.delay,
            self.discount,
        )

    def action_open_exact_duplicate_wizard(self):
        records = self.exists()
        if not records:
            records = self.search([])
        wizard = self.env["supplierinfo.deduplicate.wizard"].with_context(
            active_ids=records.ids,
            active_model=self._name,
        ).create({})
        return {
            "name": "Удалить точные дубликаты прайс-листа",
            "type": "ir.actions.act_window",
            "res_model": "supplierinfo.deduplicate.wizard",
            "res_id": wizard.id,
            "view_mode": "form",
            "target": "new",
        }
