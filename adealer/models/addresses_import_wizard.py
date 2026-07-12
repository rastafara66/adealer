from odoo import models, fields, api, _
from odoo.exceptions import UserError

class PartnerAddressImportWizard(models.TransientModel):
    _name = 'partner.address.import.wizard'
    _description = 'Майстер імпорту адрес контрагентів'

    partner_type = fields.Selection([
        ('company', 'Юридичні особи'),
        ('person', 'Фізичні особи'),
        ('all', 'Всі')
    ], string='Тип контрагента', default='all', required=True)

    def action_import_addresses(self):
        # Знайти модель імпорту
        import_model = self.env['res.partner.address.import']
        # Викликати метод імпорту з фільтрацією
        wizard = import_model.create({})
        return wizard.import_addresses_from_excel_filtered(self.partner_type)