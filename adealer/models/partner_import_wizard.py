from odoo import models, fields, api, _
from odoo.exceptions import UserError
import base64
import pandas as pd
import io

class PartnerImportWizard(models.TransientModel):
    _name = 'partner.import.wizard'
    _description = 'Майстер імпорту контрагентів з Excel'

    file = fields.Binary(string="Excel файл", required=True)
    file_name = fields.Char(string="Назва файлу")

    def action_import_partners(self):
        if not self.file:
            raise UserError(_("Будь ласка, виберіть файл для імпорту."))
        if self.file_name and not self.file_name.lower().endswith(('.xls', '.xlsx')):
            raise UserError(_("Оберіть файл у форматі Excel (.xls або .xlsx)"))

        # Зчитування Excel з Binary
        try:
            file_content = base64.b64decode(self.file)
            df = pd.read_excel(io.BytesIO(file_content))
        except Exception as e:
            raise UserError(_("Не вдалося прочитати Excel файл: %s") % e)

        # Викликати логіку імпорту з PartnerImport, передаючи DataFrame
        import_model = self.env['res.partner.import']
        return import_model.import_partners_from_dataframe(df)