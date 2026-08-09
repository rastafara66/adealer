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

    @report_errors('wizard_import_partners')
    def action_import_partners(self):
        if not self.file:
            raise UserError(_("Please select a file to import."))
        if self.file_name and not self.file_name.lower().endswith(('.xls', '.xlsx')):
            raise UserError(_("Select a file in Excel format (.xls or .xlsx)"))

        # Зчитування Excel з Binary
        try:
            file_content = base64.b64decode(self.file)
            df = read_xlsx_rows(file_content)
        except Exception as e:
            raise UserError(_("Could not read the Excel file: %s") % e)

        # Викликати логіку імпорту з PartnerImport, передаючи DataFrame
        import_model = self.env['res.partner.import']
        return import_model.import_partners_from_dataframe(df)