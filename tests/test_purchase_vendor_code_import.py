from odoo.exceptions import ValidationError
from odoo.tests import TransactionCase


class TestPurchaseVendorCodeImport(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.vendor = cls.env["res.partner"].create({
            "name": "CHINASS Test Vendor",
            "supplier_rank": 1,
        })
        cls.other_vendor = cls.env["res.partner"].create({
            "name": "Other Test Vendor",
            "supplier_rank": 1,
        })
        cls.product_a = cls.env["product.product"].create({
            "name": "Test Cola 330 ml",
            "purchase_ok": True,
            "type": "consu",
        })
        cls.product_b = cls.env["product.product"].create({
            "name": "Test Water 500 ml",
            "purchase_ok": True,
            "type": "consu",
        })
        cls.supplierinfo_a = cls.env["product.supplierinfo"].create({
            "partner_id": cls.vendor.id,
            "product_id": cls.product_a.id,
            "product_code": "SUP-A001",
            "price": 0.8781,
        })
        cls.order = cls.env["purchase.order"].create({
            "partner_id": cls.vendor.id,
        })

    def _create_import_line(self, code, order=None):
        return self.env["purchase.order.line"].create({
            "order_id": (order or self.order).id,
            "vendor_product_code_import": code,
            "product_qty": 24,
            "price_unit": 0.8781,
        })

    def test_create_line_resolves_product_from_vendor_code(self):
        """Creating a PO line by vendor code must populate product_id."""
        line = self._create_import_line("  SUP-A001  ")

        self.assertEqual(line.product_id, self.product_a)
        self.assertEqual(line.vendor_product_code_import, "  SUP-A001  ")

    def test_real_orm_import_resolves_product_from_vendor_code(self):
        """Test the Odoo import engine route, not only direct record creation."""
        self.env["ir.model.data"].create({
            "module": "purchase_vendor_code_import_test",
            "name": "vendor_chinass",
            "model": "res.partner",
            "res_id": self.vendor.id,
            "noupdate": True,
        })

        result = self.env["purchase.order"].load(
            [
                "name",
                "partner_id/id",
                "order_line/vendor_product_code_import",
                "order_line/product_qty",
                "order_line/price_unit",
            ],
            [[
                "P-IMPORT-VENDOR-CODE-001",
                "purchase_vendor_code_import_test.vendor_chinass",
                "SUP-A001",
                "24",
                "0.8781",
            ]],
        )

        self.assertFalse(result.get("messages"), result.get("messages"))
        order = self.env["purchase.order"].browse(result["ids"][0])
        self.assertEqual(order.partner_id, self.vendor)
        self.assertEqual(order.order_line.product_id, self.product_a)

    def test_code_is_scoped_to_purchase_order_vendor(self):
        """The same vendor code belonging only to another vendor must be rejected."""
        self.env["product.supplierinfo"].create({
            "partner_id": self.other_vendor.id,
            "product_id": self.product_b.id,
            "product_code": "OTHER-ONLY",
            "price": 1.10,
        })

        with self.assertRaises(ValidationError):
            self._create_import_line("OTHER-ONLY")

    def test_duplicate_vendor_code_for_different_products_is_rejected(self):
        """Import must stop if one vendor code points to two different products."""
        self.env["product.supplierinfo"].create({
            "partner_id": self.vendor.id,
            "product_id": self.product_b.id,
            "product_code": "SUP-A001",
            "price": 0.50,
        })

        with self.assertRaises(ValidationError):
            self._create_import_line("SUP-A001")
