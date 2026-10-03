from odoo import models, fields, api, _
from odoo.exceptions import UserError
import base64
from .excel_util import read_xlsx_rows
from .error_report import report_errors

class PartnerImportWizard(models.TransientModel):
    _name = 'partner.import.wizard'
    _description = 'Partner import wizard (Excel)'

    file = fields.Binary(string="Excel file", required=True,
                         help='The counterparties as an Excel file (.xls or .xlsx).')
    file_name = fields.Char(string="File name",
                            help='Tells .xls and .xlsx apart.')
    result_summary = fields.Text(string="Import result", readonly=True,
                                 help='How many counterparties were added or updated, and every row that needs attention, with the reason.')

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
            raise UserError(_("Choose the file to import."))
        if self.file_name and not self.file_name.lower().endswith(('.xls', '.xlsx')):
            raise UserError(_(
                'The file format does not fit: "%s".\n\n'
                "An Excel file is needed, .xls or .xlsx. If the file is a CSV, "
                "open it in Excel and save it as a workbook.", self.file_name))

        try:
            file_content = base64.b64decode(self.file)
            df = read_xlsx_rows(file_content)
        except Exception as e:
            raise UserError(_(
                "Could not read the file: %s\n\n"
                "The usual causes: the file is damaged, password-protected or "
                "saved in an old format. Open it in Excel and save it as "
                ".xlsx.", e))

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