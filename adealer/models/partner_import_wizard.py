from odoo import models, fields, api, _
from odoo.exceptions import UserError
import base64
from .excel_util import read_xlsx_rows
from .error_report import report_errors

class PartnerImportWizard(models.TransientModel):
    _name = 'partner.import.wizard'
    _description = 'Partner import wizard (Excel)'

    file = fields.Binary(string="Excel file", required=True)
    file_name = fields.Char(string="File name")
    result_summary = fields.Text(string="Результат імпорту", readonly=True)

    @report_errors('wizard_import_partners')
    def action_import_partners(self):
        """Імпортувати й ПОКАЗАТИ звіт.

        🔴 Раніше метод повертав словник лічильників. Odoo не вміє його
        показати — вікно просто зачинялось, і людина не знала ні скільки
        додано, ні що частину рядків пропущено. Найгірший різновид
        «мовчазної порожнечі» (конвенції §7): результат є, але його ніхто
        не бачить.
        """
        self.ensure_one()
        if not self.file:
            raise UserError(_("Оберіть файл для імпорту."))
        if self.file_name and not self.file_name.lower().endswith(('.xls', '.xlsx')):
            raise UserError(_(
                "Формат файлу не підходить: «%s».\n\n"
                "Потрібен Excel — .xls або .xlsx. Якщо файл у CSV, "
                "збережіть його як книгу Excel.", self.file_name))

        try:
            file_content = base64.b64decode(self.file)
            df = read_xlsx_rows(file_content)
        except Exception as e:
            raise UserError(_(
                "Не вдалося прочитати файл: %s\n\n"
                "Найчастіші причини: файл пошкоджений, захищений паролем "
                "або збережений у старому форматі. Відкрийте його в Excel і "
                "збережіть як .xlsx.", e))

        import_model = self.env['res.partner.import']
        result = import_model.import_partners_from_dataframe(df)
        self.result_summary = import_model.format_import_report(result)

        # Лишаємось у тому ж вікні — зі звітом на екрані.
        return {
            "type": "ir.actions.act_window",
            "res_model": self._name,
            "res_id": self.id,
            "view_mode": "form",
            "views": [[False, "form"]],
            "target": "new",
        }