from odoo import models, fields, api
from odoo.exceptions import ValidationError

class ResPartner(models.Model):
    _inherit = 'res.partner'

    edrpou = fields.Char(
        string='EDRPOU',
        help='ЄДРПОУ (Єдиний державний реєстр підприємств та організацій України)',
        size=10
    )

    driver_license = fields.Char(
        string='Driver License',
        help='Номер водійського посвідчення (для фізичних осіб)'
    )

    partners_contacts = fields.Many2many(
        'res.partner',
        'res_partner_contacts_rel',
        'partner_id',
        'contact_id',
        string='Контакти партнера',
        domain=[('type', '=', 'contact')],
        help='Контакти, пов’язані з цим партнером (тип contact)'
    )
    # Поле partners_contacts створює звʼязок "багато-до-багатьох" між партнерами.
    # Це дозволяє одному партнеру мати декілька контактів (типу contact), і навпаки.
    # Використовується допоміжна таблиця res_partner_contacts_rel з полями partner_id та contact_id.
    # Поле відображається як "Контакти партнера" і дозволяє вибирати лише партнерів з типом "contact".
    #
    # Приклад використання в коді:
    # partner = self.env['res.partner'].browse(1)
    # contacts = partner.partners_contacts  # Отримаємо всі контакти партнера
    # partner.partners_contacts = [(6, 0, [2, 3])]  # Призначити контакти з id 2 та 3 партнеру
    #
    # Приклад у вигляді XML (view):
    # <field name="partners_contacts" widget="many2many_tags"/>

    partner_vehicles = fields.One2many(
        'fleet.vehicle',
        'partner_id',
        string='Автомобілі партнера',
        help='Автомобілі, що належать цьому партнеру'
    )
    # Поле partner_vehicles створює звʼязок "один-до-багатьох" між партнером та автомобілями.
    # Це дозволяє одному партнеру мати багато автомобілів.
    # Зв'язок встановлюється через поле 'partner_id' у моделі 'fleet.vehicle'.

    @api.constrains('edrpou')
    def _check_edrpou_length(self):
        for rec in self:
            if rec.edrpou and len(rec.edrpou) not in (8, 10):
                raise ValidationError("EDRPOU має містити тільки 8 або 10 символів.")