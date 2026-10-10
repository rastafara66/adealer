from odoo import models, fields, api, _
from odoo.exceptions import UserError
from .error_report import report_errors

class PartnerAddressImportWizard(models.TransientModel):
    _name = 'partner.address.import.wizard'
    _description = 'Partner address import wizard'

    partner_type = fields.Selection([
        ('company', 'Legal entities'),
        ('person', 'Individuals'),
        ('all', 'All')
    ], string='Counterparty type', default='all', required=True,
                                    help='Whose addresses to load: legal entities, individuals or all counterparties.')

    @report_errors('wizard_import_addresses')
    def action_import_addresses(self):
        # Знайти модель імпорту
        import_model = self.env['res.partner.address.import']
        # Викликати метод імпорту з фільтрацією
        wizard = import_model.create({})
        return wizard.import_addresses_from_excel_filtered(self.partner_type)