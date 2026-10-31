from odoo import _, models, fields, api
from odoo.exceptions import ValidationError

from .ua_tax_ids import ua_digits


def _code_field(model):
    """Стандартне поле коду ЄДРПОУ / РНОКПП цієї серії Odoo (`ua_tax_ids.py`): 18/19 — `company_registry`,
    20 — `vat`."""
    return 'company_registry' if 'company_registry' in model._fields else 'vat'


class ResPartner(models.Model):
    _inherit = 'res.partner'

    # 🔴 31.10.2026: до цього `edrpou` було власним полем 3A-dealer, і код бачив лише 3A-dealer — ні конектор ЄДР,
    # ні Bank Sync, ні сама Odoo (пошук, «компанія», дублі). Тепер код лежить у стандартному полі серії
    # (`ua_tax_ids.py`), а `edrpou` — його псевдонім для друкованих форм і коду, що вже його читає. Дані
    # старого стовпчика переносить міграція 1.22.0.
    edrpou = fields.Char(
        string='EDRPOU / RNOKPP',
        compute='_compute_edrpou', inverse='_inverse_edrpou', search='_search_edrpou',
        help='EDRPOU code (8 digits) of a company or RNOKPP (10 digits) of an individual. Stored in the '
             'standard field of this Odoo version (Company ID up to Odoo 19, Tax ID in Odoo 20).',
    )
    ua_code_in_vat = fields.Boolean(
        compute='_compute_ua_code_in_vat',
        help='Technical: the EDRPOU / RNOKPP code is the Tax ID itself (Odoo 20), so the form does not '
             'show it twice.',
    )

    driver_license = fields.Char(
        string='Driver License',
        help="Driver's license number (for individuals)"
    )

    partners_contacts = fields.Many2many(
        'res.partner',
        'res_partner_contacts_rel',
        'partner_id',
        'contact_id',
        string='Partner contacts',
        domain=[('type', '=', 'contact')],
        help='Contacts linked to this partner (type contact)'
    )
    # Поле partners_contacts створює звʼязок "багато-до-багатьох" between партнерами.
    # Це дозволяє одному партнеру мати декілька контактів (типу contact), і навпаки.
    # Використовується допоміжна таблиця res_partner_contacts_rel з полями partner_id and contact_id.
    # Поле відображається як "Partner contacts" і дозволяє вибирати лише партнерів з типом "contact".
    #
    # Приклад використання в коді:
    # partner = self.env['res.partner'].browse(1)
    # contacts = partner.partners_contacts  # Отримаємо всі контакти партнера
    # partner.partners_contacts = [(6, 0, [2, 3])]  # Призначити контакти з id 2 and 3 партнеру
    #
    # Приклад у вигляді XML (view):
    # <field name="partners_contacts" widget="many2many_tags"/>

    partner_vehicles = fields.One2many(
        'fleet.vehicle',
        'partner_id',
        string='Partner vehicles',
        help='Vehicles owned by this partner'
    )
    # Поле partner_vehicles створює звʼязок "один-до-багатьох" between партнером and автомобілями.
    # Це дозволяє одному партнеру мати багато автомобілів.
    # Зв'язок встановлюється через поле 'partner_id' у моделі 'fleet.vehicle'.

    @api.depends(lambda self: [_code_field(self)])
    def _compute_edrpou(self):
        field = _code_field(self)
        for rec in self:
            code = ua_digits(rec[field])
            # В Odoo 20 у `vat` можуть лежати ще не перенесені 12 цифр ІПН — це не код.
            rec.edrpou = code if len(code) in (8, 9, 10) else False

    def _inverse_edrpou(self):
        field = _code_field(self)
        for rec in self:
            if rec.edrpou and len(ua_digits(rec.edrpou)) not in (8, 10):
                raise ValidationError(_(
                    'The EDRPOU code "%s" has %s characters, but it must have 8 '
                    '(a company) or 10 (an individual). Check the code against '
                    'the registration documents.', rec.edrpou, len(rec.edrpou)))
            rec[field] = ua_digits(rec.edrpou) or False

    def _search_edrpou(self, operator, value):
        field = _code_field(self)
        if isinstance(value, str) and operator in ('=', '!=', 'like', 'ilike', '=like', '=ilike'):
            value = ua_digits(value) or value
        return [(field, operator, value)]

    def _compute_ua_code_in_vat(self):
        for rec in self:
            rec.ua_code_in_vat = 'company_registry' not in rec._fields