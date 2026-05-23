from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class PurchaseOrderLine(models.Model):
    _inherit = "purchase.order.line"

    vendor_product_code_import = fields.Char(
        string="Код товара поставщика для импорта",
        copy=False,
        index=True,
        help=(
            "Код товара, используемый поставщиком. При импорте Odoo находит "
            "товар по коду в прайс-листе поставщика, указанного в заказе."
        ),
    )

    @api.model
    def _get_product_from_vendor_code_import(self, vendor_code, order):
        code = (vendor_code or "").strip()
        if not code:
            raise ValidationError(_("Код товара поставщика для импорта не может быть пустым."))

        if not order or not order.partner_id:
            raise ValidationError(
                _("Перед использованием кода товара поставщика укажите продавца в заказе.")
            )

        commercial_vendor = order.partner_id.commercial_partner_id
        supplier_infos = self.env["product.supplierinfo"].with_company(order.company_id).search([
            ("product_code", "=", code),
            "|",
            ("company_id", "=", False),
            ("company_id", "=", order.company_id.id),
        ])
        supplier_infos = supplier_infos.filtered(
            lambda info: info.partner_id.commercial_partner_id == commercial_vendor
        )

        if not supplier_infos:
            raise ValidationError(
                _(
                    "Для продавца '%(vendor)s' не найдена строка прайс-листа "
                    "с кодом товара '%(code)s'. Сначала добавьте код на вкладке "
                    "«Покупка» карточки товара."
                )
                % {"vendor": order.partner_id.display_name, "code": code}
            )

        products = self.env["product.product"]
        ambiguous_templates = self.env["product.template"]
        for info in supplier_infos:
            if info.product_id:
                products |= info.product_id
            elif info.product_tmpl_id.product_variant_count == 1:
                products |= info.product_tmpl_id.product_variant_id
            else:
                ambiguous_templates |= info.product_tmpl_id

        if ambiguous_templates:
            raise ValidationError(
                _(
                    "Код поставщика '%(code)s' назначен шаблону с несколькими "
                    "вариантами: %(templates)s. Назначьте код конкретному варианту."
                )
                % {
                    "code": code,
                    "templates": ", ".join(ambiguous_templates.mapped("display_name")),
                }
            )

        products = products.filtered("purchase_ok")
        if not products:
            raise ValidationError(
                _("Код поставщика '%s' найден, но соответствующий товар недоступен для покупки.")
                % code
            )

        if len(products) != 1:
            raise ValidationError(
                _(
                    "Код поставщика '%(code)s' соответствует нескольким товарам "
                    "продавца '%(vendor)s': %(products)s. Перед импортом исправьте прайс-лист."
                )
                % {
                    "code": code,
                    "vendor": order.partner_id.display_name,
                    "products": ", ".join(products.mapped("display_name")),
                }
            )

        return products

    @api.model_create_multi
    def create(self, vals_list):
        prepared_vals_list = []
        for vals in vals_list:
            values = dict(vals)
            code = values.get("vendor_product_code_import")
            if code:
                order = self.env["purchase.order"].browse(values.get("order_id")).exists()
                if not order:
                    raise ValidationError(
                        _("Заказ должен существовать до определения товара по коду поставщика '%s'.")
                        % code
                    )

                product = self._get_product_from_vendor_code_import(code, order)
                imported_product_id = values.get("product_id")
                if imported_product_id and imported_product_id != product.id:
                    raise ValidationError(
                        _(
                            "Импортированный товар конфликтует с кодом поставщика '%s'. "
                            "Удалите колонку товара из файла либо исправьте данные."
                        )
                        % code
                    )
                values["product_id"] = product.id
            prepared_vals_list.append(values)

        return super().create(prepared_vals_list)
