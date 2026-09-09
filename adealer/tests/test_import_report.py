# -*- coding: utf-8 -*-
"""Імпорт мусить ЗВІТУВАТИ, а не мовчки ковтати рядки (конвенції §9).

🔴 Що було. `import_partners_from_dataframe` повертав словник лічильників,
а майстер віддавав його як результат дії. Odoo такий словник показати не
вміє — вікно просто зачинялось. Причини пропусків писались у файл усередині
теки модуля, тобто користувач не бачив їх узагалі, а на установці з
доступною лише для читання `addons` імпорт іще й падав на записі журналу.

Найгірше тут не втрачені рядки, а те, що втрату **не видно**: контрагенти
просто не з'являлись, і помітити це можна було, лише перерахувавши їх.
"""
from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestPartnerImportReport(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.model = cls.env["res.partner.import"]

    @staticmethod
    def _rows():
        """Файл із трьома проблемними рядками й одним нормальним."""
        return [
            {"Наименование": "ТОВ «Нормальне»", "Телефон": "0501234567",
             "Код по ЕГРПОУ": "12345678"},
            {"Наименование": "", "Телефон": "0509999999"},          # без назви
            {"Наименование": "ТОВ «Тільки назва»"},                  # без даних
            {"Наименование": "ТОВ «Кривий код»", "Телефон": "0507777777",
             "Код по ЕГРПОУ": "123"},                                # код не той
        ]

    def test_every_skipped_row_explains_itself(self):
        result = self.model.import_partners_from_dataframe(self._rows())
        problems = result["problems"]
        self.assertEqual(len(problems), 3,
                         "кожен проблемний рядок мусить назвати себе")
        for p in problems:
            self.assertTrue(p["what"] and p["why"] and p["howto"],
                            "пункт звіту мусить сказати що / чому / що зробити")

    def test_row_numbers_match_the_file(self):
        """Номер рядка мусить збігатися з тим, що людина бачить в Excel.

        ⚠️ Заголовок — перший рядок файлу, тож дані починаються з другого.
        Номер, зміщений на одиницю, гірший за відсутній: людина виправляє
        не той рядок і не розуміє, чому проблема лишилась.
        """
        result = self.model.import_partners_from_dataframe(self._rows())
        rows = [p["row"] for p in result["problems"]]
        self.assertEqual(rows, [3, 4, 5])

    def test_report_names_the_volume_first(self):
        result = self.model.import_partners_from_dataframe(self._rows())
        text = self.model.format_import_report(result)
        self.assertIn("Оброблено рядків: 4", text)
        self.assertIn("Потребують уваги — 3", text)
        self.assertIn("Чому:", text)
        self.assertIn("Що зробити:", text)

    def test_clean_import_says_so_out_loud(self):
        """🔴 «Нічого не сказали» і «все чисто» мусять виглядати по-різному."""
        result = self.model.import_partners_from_dataframe([
            {"Наименование": "ТОВ «Чисте»", "Телефон": "0501112233"},
        ])
        text = self.model.format_import_report(result)
        self.assertIn("Рядків із проблемами немає", text)

    def test_bad_code_does_not_lose_the_partner(self):
        """Кривий код ЄДРПОУ — привід попередити, а не викинути контрагента."""
        before = self.env["res.partner"].search_count([])
        result = self.model.import_partners_from_dataframe([
            {"Наименование": "ТОВ «Кривий код»", "Телефон": "0507777777",
             "Код по ЕГРПОУ": "123"},
        ])
        self.assertEqual(result["added"], 1)
        self.assertEqual(self.env["res.partner"].search_count([]), before + 1)
        self.assertEqual(len(result["problems"]), 1)

    def test_wizard_shows_the_report_instead_of_closing(self):
        """Майстер мусить лишити звіт на екрані, а не зачинитись."""
        import base64
        import io as _io

        try:
            import openpyxl
        except ImportError:
            self.skipTest("openpyxl недоступний — файл не зібрати")

        book = openpyxl.Workbook()
        sheet = book.active
        sheet.append(["Наименование", "Телефон", "Код по ЕГРПОУ"])
        sheet.append(["ТОВ «З файлу»", "0501234567", "12345678"])
        sheet.append(["", "0509999999", ""])
        buf = _io.BytesIO()
        book.save(buf)

        wizard = self.env["partner.import.wizard"].create({
            "file": base64.b64encode(buf.getvalue()),
            "file_name": "partners.xlsx",
        })
        action = wizard.action_import_partners()
        self.assertEqual(action.get("res_model"), "partner.import.wizard")
        self.assertTrue(wizard.result_summary, "звіт порожній")
        self.assertIn("Оброблено рядків", wizard.result_summary)
