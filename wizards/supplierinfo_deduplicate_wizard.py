from collections import defaultdict

from odoo import _, api, fields, models


class SupplierinfoDeduplicateWizard(models.TransientModel):
    _name = "supplierinfo.deduplicate.wizard"
    _description = "Предпросмотр удаления дубликатов прайс-листа поставщика"

    selected_count = fields.Integer(string="Проверено строк", readonly=True)
    duplicate_count = fields.Integer(string="Точных дубликатов для удаления", readonly=True)
    conflict_count = fields.Integer(string="Опасных конфликтов кода", readonly=True)
    summary = fields.Text(string="Результат проверки", readonly=True)
    source_ids = fields.Many2many("product.supplierinfo", string="Проверяемые строки", readonly=True)

    @api.model
    def _analyse_records(self, records):
        records = records.exists().sorted(key=lambda record: record.id)
        exact_groups = defaultdict(list)
        code_groups = defaultdict(list)

        for record in records:
            exact_groups[record._exact_duplicate_key()].append(record)
            normalized_code = (record.product_code or "").strip()
            if normalized_code:
                code_groups[(record.partner_id.commercial_partner_id.id, normalized_code)].append(record)

        duplicates = self.env["product.supplierinfo"]
        duplicate_lines = []
        for group in exact_groups.values():
            if len(group) > 1:
                keeper = group[0]
                to_delete = group[1:]
                duplicates |= self.env["product.supplierinfo"].browse([record.id for record in to_delete])
                duplicate_lines.append(
                    "• %s / %s / код %s — оставить ID %s, удалить ID %s"
                    % (
                        keeper.partner_id.display_name,
                        (keeper.product_id or keeper.product_tmpl_id).display_name,
                        keeper.product_code or "—",
                        keeper.id,
                        ", ".join(str(record.id) for record in to_delete),
                    )
                )

        conflict_lines = []
        for (_vendor_id, code), group in code_groups.items():
            products = {
                (record.product_id or record.product_tmpl_id)._name + ":" + str(
                    (record.product_id or record.product_tmpl_id).id
                )
                for record in group
            }
            if len(products) > 1:
                products_text = ", ".join(
                    sorted({(record.product_id or record.product_tmpl_id).display_name for record in group})
                )
                conflict_lines.append(
                    "• %s / код %s → %s"
                    % (group[0].partner_id.display_name, code, products_text)
                )

        sections = [
            "Проверяются только выбранные записи прайс-листа.",
            "",
            "ТОЧНЫЕ ДУБЛИКАТЫ, КОТОРЫЕ МОЖНО УДАЛИТЬ: %s" % len(duplicates),
        ]
        sections.extend(duplicate_lines[:50] or ["• Не найдены."])
        if len(duplicate_lines) > 50:
            sections.append("• …показаны первые 50 групп.")

        sections.extend([
            "",
            "ОПАСНЫЕ КОНФЛИКТЫ (НЕ УДАЛЯЮТСЯ АВТОМАТИЧЕСКИ): %s" % len(conflict_lines),
        ])
        sections.extend(conflict_lines[:50] or ["• Не найдены."])
        if len(conflict_lines) > 50:
            sections.append("• …показаны первые 50 конфликтов.")

        return duplicates, conflict_lines, "\n".join(sections)

    @api.model
    def default_get(self, field_list):
        values = super().default_get(field_list)
        records = self.env["product.supplierinfo"].browse(self.env.context.get("active_ids", [])).exists()
        duplicates, conflicts, summary = self._analyse_records(records)
        values.update({
            "selected_count": len(records),
            "duplicate_count": len(duplicates),
            "conflict_count": len(conflicts),
            "summary": summary,
            "source_ids": [(6, 0, records.ids)],
        })
        return values

    def action_delete_exact_duplicates(self):
        self.ensure_one()
        duplicates, _conflicts, _summary = self._analyse_records(self.source_ids)
        count = len(duplicates)
        duplicates.unlink()
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Очистка прайс-листа завершена"),
                "message": _("Удалено точных дубликатов: %s. Опасные конфликты автоматически не удаляются.") % count,
                "type": "success",
                "sticky": True,
                "next": {"type": "ir.actions.act_window_close"},
            },
        }
