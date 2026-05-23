from odoo.tests import TransactionCase


class TestSupplierinfoDeduplicate(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.vendor = cls.env["res.partner"].create({
            "name": "CHINASS Test Vendor for Deduplication",
            "supplier_rank": 1,
        })
        cls.product_a = cls.env["product.product"].create({
            "name": "Dedup Cola 330 ml",
            "purchase_ok": True,
            "type": "consu",
        })
        cls.product_b = cls.env["product.product"].create({
            "name": "Dedup Water 500 ml",
            "purchase_ok": True,
            "type": "consu",
        })

    def _supplierinfo(self, product, code="DUP-001", min_qty=1.0, price=0.88):
        return self.env["product.supplierinfo"].create({
            "partner_id": self.vendor.id,
            "product_id": product.id,
            "product_code": code,
            "min_qty": min_qty,
            "price": price,
        })

    def _wizard_for(self, records):
        Wizard = self.env["supplierinfo.deduplicate.wizard"].with_context(
            active_model="product.supplierinfo",
            active_ids=records.ids,
        )
        defaults = Wizard.default_get([
            "selected_count",
            "duplicate_count",
            "conflict_count",
            "summary",
            "source_ids",
        ])
        return Wizard.create(defaults)

    def test_exact_duplicate_is_deleted_and_one_record_remains(self):
        first = self._supplierinfo(self.product_a)
        duplicate = self._supplierinfo(self.product_a)
        different_quantity_tier = self._supplierinfo(self.product_a, min_qty=100.0, price=0.79)

        wizard = self._wizard_for(first | duplicate | different_quantity_tier)

        self.assertEqual(wizard.duplicate_count, 1)
        self.assertEqual(wizard.conflict_count, 0)

        wizard.action_delete_exact_duplicates()

        self.assertTrue(first.exists())
        self.assertFalse(duplicate.exists())
        self.assertTrue(different_quantity_tier.exists())

    def test_same_code_for_different_products_is_reported_not_deleted(self):
        cola = self._supplierinfo(self.product_a, code="CONFLICT-01")
        water = self._supplierinfo(self.product_b, code="CONFLICT-01")

        wizard = self._wizard_for(cola | water)

        self.assertEqual(wizard.duplicate_count, 0)
        self.assertEqual(wizard.conflict_count, 1)

        wizard.action_delete_exact_duplicates()

        self.assertTrue(cola.exists())
        self.assertTrue(water.exists())

    def test_different_price_is_not_an_exact_duplicate(self):
        regular_price = self._supplierinfo(self.product_a, code="PRICE-01", price=0.88)
        changed_price = self._supplierinfo(self.product_a, code="PRICE-01", price=0.92)

        wizard = self._wizard_for(regular_price | changed_price)

        self.assertEqual(wizard.duplicate_count, 0)
        self.assertTrue(regular_price.exists())
        self.assertTrue(changed_price.exists())
