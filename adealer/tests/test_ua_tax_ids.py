# -*- coding: utf-8 -*-
"""Код ЄДРПОУ / РНОКПП і ІПН платника ПДВ — правило `models/ua_tax_ids.py` у кожній серії Odoo.

🔴 Файл лежить байт у байт у ядрі кожного продукту (як і сам `ua_tax_ids.py`); копії звіряє гейт 3A
`tools/store/check_ua_tax_ids.py`. Номери вигадані.
"""
from odoo.tests import TransactionCase, tagged

from ..models.ua_tax_ids import UA_VAT

CODE, RNOKPP, IPN = "12345678", "1234567890", "123456789012"


@tagged("post_install", "-at_install")
class TestUaTaxIds(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.ua = cls.env.ref("base.ua")
        cls.Partner = cls.env["res.partner"].with_context(tracking_disable=True)
        cls.series20 = "company_registry" not in cls.Partner._fields

    def partner(self, name, code=None, ipn=None, **vals):
        return self.Partner.create({"name": name, "country_id": self.ua.id, **vals,
                                    **self.Partner._l10n_ua_tax_vals(code=code, ipn=ipn)})

    def test_codes_go_to_the_series_fields(self):
        firm = self.partner("ТОВ «Тест»", code=CODE, ipn=IPN)
        self.assertEqual(firm._l10n_ua_tax_codes(), (CODE, IPN))
        if self.series20:
            self.assertEqual(firm.vat, CODE, "Odoo 20: код — у податковому номері")
            self.assertEqual((firm.additional_identifiers or {}).get(UA_VAT), IPN, "ІПН — додатковий ідентифікатор")
        else:
            self.assertEqual(firm.company_registry, CODE, "Odoo 18/19: код — у company_registry")
            self.assertEqual(firm.vat, IPN, "ІПН — у vat")
        firm.write(self.Partner._l10n_ua_tax_vals(ipn="", identifiers=firm.additional_identifiers
                                                  if self.series20 else None))
        self.assertEqual(firm._l10n_ua_tax_codes(), (CODE, ""), "ІПН очищено, код лишився")

    def test_contact_and_empty_record_read_the_commercial_partner(self):
        firm = self.partner("ТОВ «Батько»", code=CODE, ipn=IPN)
        contact = self.Partner.create({"name": "Бухгалтерія", "parent_id": firm.id})
        self.assertEqual(contact._l10n_ua_tax_codes(), (CODE, IPN))
        self.assertEqual(self.Partner.browse()._l10n_ua_tax_codes(), ("", ""))

    def test_foreign_partner_has_no_ukrainian_codes(self):
        foreign = self.Partner.create({"name": "GmbH", "country_id": self.env.ref("base.de").id,
                                       "vat": "DE123456788"})
        self.assertEqual(foreign._l10n_ua_tax_codes(), ("", ""))

    def test_company_by_code_length_in_odoo_20(self):
        firm = self.partner("ТОВ «Компанія»", code=CODE)
        fop = self.partner("ФОП Тест", code=RNOKPP, ipn=RNOKPP)
        person = self.partner("Іван Тест", code=RNOKPP)
        if self.series20:
            self.assertTrue(firm.is_company, "8 цифр — юрособа")
            self.assertFalse(fop.is_company, "ФОП — фізособа, хоч і платник ПДВ")
            self.assertFalse(person.is_company)
        self.assertEqual(fop._l10n_ua_tax_codes(), (RNOKPP, RNOKPP))

    def test_legacy_numbers_are_read_and_moved(self):
        """Дані до 31.10.2026: `vat` вважали ІПН. Читаються правильно й до переносу; перенос їх розкладає."""
        if self.series20:
            old = self.Partner.create({"name": "ТОВ «Старе»", "country_id": self.ua.id, "vat": IPN})
            fop = self.Partner.create({"name": "ФОП Старий", "country_id": self.ua.id, "vat": RNOKPP})
            self.assertEqual(old._l10n_ua_tax_codes(), ("", IPN), "12 цифр у vat — це ІПН")
            report = self.Partner._l10n_ua_normalize_tax_ids(legacy_vat_is_ipn=True)
            self.assertFalse(old.vat, "коду в старій картці не було — поле коду порожнє")
            self.assertEqual(old.additional_identifiers.get(UA_VAT), IPN)
            self.assertIn(old.id, report["no_code"], "ІПН без коду — у звіті переносу")
            self.assertEqual((fop.vat, fop.additional_identifiers.get(UA_VAT)), (RNOKPP, RNOKPP),
                             "ФОП-платник: РНОКПП лишається кодом і стає ІПН")
            self.assertFalse(fop.is_company)
        else:
            misplaced = self.Partner.create({"name": "ТОВ «Не туди»", "country_id": self.ua.id, "vat": CODE})
            fop = self.Partner.create({"name": "ФОП Старий", "country_id": self.ua.id, "vat": RNOKPP})
            self.assertEqual(misplaced._l10n_ua_tax_codes(), (CODE, CODE), "8 цифр у полі ІПН — це код")
            self.Partner._l10n_ua_normalize_tax_ids(legacy_vat_is_ipn=True)
            self.assertEqual((misplaced.company_registry, misplaced.vat), (CODE, False))
            self.assertEqual((fop.company_registry, fop.vat), (RNOKPP, RNOKPP))
        again = self.Partner._l10n_ua_normalize_tax_ids(legacy_vat_is_ipn=True)
        self.assertEqual((again["code"], again["ipn"]), (0, 0), "повторний перенос нічого не міняє")

    def test_vat_label_follows_the_series(self):
        self.Partner._l10n_ua_tax_labels()
        label = self.ua.with_context(lang="en_US").vat_label
        self.assertEqual(label, "EDRPOU / RNOKPP" if self.series20 else "VAT payer IPN")

    def test_wrong_field_warns_on_the_form(self):
        wrong = IPN if self.series20 else CODE
        partner = self.Partner.new({"name": "Нова картка", "country_id": self.ua.id, "vat": wrong})
        warning = partner._l10n_ua_onchange_vat_slot()
        self.assertTrue(warning and warning.get("warning"), "номер не в тому полі — попередження на формі")
        partner.vat = CODE if self.series20 else IPN
        self.assertFalse(partner._l10n_ua_onchange_vat_slot())
