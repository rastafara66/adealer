# -*- coding: utf-8 -*-
"""1.22.0: код ЄДРПОУ / РНОКПП — у стандартне поле серії, ІПН — у своє (`models/ua_tax_ids.py`).

До 31.10.2026 код лежав у власному полі 3A-dealer `edrpou`, якого не бачили ні Odoo, ні конектор ЄДР, ні Bank Sync.
Odoo 18/19: код → `company_registry`; Odoo 20: код → `vat`, ІПН з `vat` → додатковий ідентифікатор. Старий
стовпчик `edrpou` лишається в базі як був. Тека — версією без серії: виконується в 18.0/19.0/20.0; повторний запуск
нічого не міняє.
"""
import logging

from odoo.api import SUPERUSER_ID, Environment

# Ім'я — у гілці `odoo`: логер з `__name__` файла міграції лежить поза нею, і рядок звіту губився.
_logger = logging.getLogger("odoo.addons.adealer.migrations")


def migrate(cr, version):
    report = Environment(cr, SUPERUSER_ID, {})["res.partner"]._l10n_ua_normalize_tax_ids(legacy_vat_is_ipn=True)
    _logger.info("Номери контрагентів: кодів заповнено %s, ІПН перенесено %s; ІПН без коду — %s, різні коди в "
                 "двох полях — %s", report["code"], report["ipn"], len(report["no_code"]), len(report["conflict"]))
