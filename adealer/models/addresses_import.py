import pandas as pd
import re
import os
from datetime import datetime
from odoo import models, api, _
from odoo.exceptions import UserError

LOG_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'log', 'import.log')

def write_log(msg):
    with open(LOG_PATH, 'a', encoding='utf-8') as f:
        f.write(msg + '\n')

def parse_address_list(address_str):
    """
    Парсити рядок адреси у словник з полями: zip, country, city, state, street, house, apartment
    """
    result = {
        'zip': '',
        'country': '',
        'city': '',
        'state': '',
        'street': '',
        'house': '',
        'apartment': '',
    }
    if not address_str or not isinstance(address_str, str):
        return result

    parts = [p.strip() for p in address_str.split(',') if p and p.strip()]
    if not parts:
        return result

    idx = 0
    if re.match(r'^\d{5}$', parts[0]):
        result['zip'] = parts[0]
        idx += 1
    if idx < len(parts) and parts[idx].lower() == 'україна':
        result['country'] = 'Україна'
        idx += 1
    if idx < len(parts):
        if parts[idx].startswith('м.') or parts[idx].startswith('смт.'):
            result['city'] = parts[idx]
            idx += 1
        elif not result['city'] and not result['zip'] and not result['country']:
            result['city'] = parts[idx]
            idx += 1

    for part in parts[idx:]:
        part = part.strip()
        if part.startswith('вул.'):
            result['street'] = part
        elif part.startswith('будинок'):
            result['house'] = part
        elif part.startswith('кв.'):
            result['apartment'] = part
        elif part.endswith('район') or part.endswith('р-н'):
            result['state'] = part

    # Якщо країна не вказана, ставимо "Україна"
    if not result['country']:
        result['country'] = 'Україна'

    street_parts = []
    if result['street']:
        street_parts.append(result['street'])
    if result['house']:
        street_parts.append(result['house'])
    if result['apartment']:
        street_parts.append(result['apartment'])
    result['street_full'] = ', '.join(street_parts)

    return result

class PartnerAddressImport(models.TransientModel):
    _name = 'res.partner.address.import'
    _description = 'Імпорт адрес контрагентів з Excel'

    @api.model
    def import_addresses_from_excel(self):
        # За замовчуванням режим - оновлювати існуючих контрагентів
        mode = 'update'

        # Додаємо дату і час початку імпорту та роздільник
        write_log("=====================")
        write_log(f"Початок імпорту: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        file_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'import_addresses.xlsx')
        try:
            df = pd.read_excel(file_path)
        except Exception as e:
            raise UserError(_('Не вдалося відкрити файл: %s') % e)

        created = 0
        updated = 0
        skipped = 0

        for idx, row in df.iterrows():
            # if idx < 1001 or idx > 3000:
            #     continue
            write_log("==========")
            name = str(row.get('Контрагент')).strip() if row.get('Контрагент') else ''
            addr_legal = str(row.get('Юридический адрес')).strip() if row.get('Юридический адрес') else ''
            addr_physical = str(row.get('Фактический адрес')).strip() if row.get('Фактический адрес') else ''
            addr_delivery = str(row.get('Адрес доставки')).strip() if row.get('Адреса доставки') else ''
            phone = str(row.get('Телефон')).strip() if row.get('Телефон') else ''
            email = str(row.get('E-Mail')).strip() if row.get('E-Mail') else ''

            write_log(f"Контрагент: {name}")
            write_log(f"Юридична адреса: {addr_legal}")
            write_log(f"Фізична адреса: {addr_physical}")
            write_log(f"Адреса доставки: {addr_delivery}")
            write_log(f"Телефон: {phone}")
            write_log(f"E-mail: {email}")

            if not name:
                skipped += 1
                write_log("Пропущено: немає назви контрагента")
                continue

            partner = self.env['res.partner'].search([('name', '=', name)], limit=1)
            if not partner:
                skipped += 1
                write_log("Пропущено: контрагента не знайдено")
                continue
            else:
                updated += 1
                write_log("Знайдено контрагента, оновлюємо адреси")

            # ОНОВЛЮЄМО ТЕЛЕФОН, EMAIL ТА ОСНОВНУ АДРЕСУ ГОЛОВНОГО ПАРТНЕРА
            vals = {}
            if phone:
                vals['phone'] = phone
            if email:
                vals['email'] = email
            # Оновлюємо основну адресу, якщо є юридична або фізична адреса
            main_addr = addr_legal if addr_legal else addr_physical
            main_addr_vals = parse_address_list(main_addr)
            if main_addr_vals.get('zip'):
                vals['zip'] = main_addr_vals['zip']
            if main_addr_vals.get('city'):
                vals['city'] = main_addr_vals['city']
            if main_addr_vals.get('street_full'):
                vals['street'] = main_addr_vals['street_full']
            if main_addr_vals.get('country'):
                country_id = self.env['res.country'].search([('name', '=', main_addr_vals['country'])], limit=1)
                if country_id:
                    vals['country_id'] = country_id.id
            if main_addr_vals.get('state'):
                state_id = self.env['res.country.state'].search([('name', '=', main_addr_vals['state'])], limit=1)
                if state_id:
                    vals['state_id'] = state_id.id
            if vals:
                partner.write(vals)

            main_addr_vals['phone'] = phone
            main_addr_vals['email'] = email

            if main_addr and any(main_addr_vals.values()):
                self._set_partner_address(partner, main_addr_vals, 'invoice')
                write_log(f"Оновлено основну адресу: {main_addr_vals}")
                # write_log(f"Розпарсена основна адреса: {main_addr_vals}")
            else:
                write_log("Пропущено: не розпарсовано адресу для оновлення")

            if addr_delivery:
                delivery_addr_vals = parse_address_list(addr_delivery)
                delivery_addr_vals['phone'] = phone
                delivery_addr_vals['email'] = email
                self._set_partner_address(partner, delivery_addr_vals, 'delivery')
                write_log(f"Оновлено delivery адресу: {delivery_addr_vals}")

        write_log("=== Імпорт адрес завершено ===")
        write_log(f"Знайдено контрагентів: {created + updated}")
        write_log(f"Оновлено контрагентів: {updated}")
        write_log(f"Пропущено контрагентів: {skipped}")
        return {
            'created': created,
            'updated': updated,
            'skipped': skipped,
        }

    @api.model
    def import_addresses_from_excel_filtered(self, partner_type='all'):
        """
        Імпорт адрес з Excel з фільтрацією по типу контрагента.
        partner_type: 'company', 'person', 'all'
        """
        mode = 'update'
        write_log("=====================")
        write_log(f"Початок імпорту: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        file_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'import_addresses.xlsx')
        try:
            df = pd.read_excel(file_path)
        except Exception as e:
            raise UserError(_('Не вдалося відкрити файл: %s') % e)

        created = 0
        updated = 0
        skipped = 0

        for idx, row in df.iterrows():
            name = str(row.get('Контрагент')).strip() if row.get('Контрагент') else ''
            if not name:
                skipped += 1
                continue
            partner = self.env['res.partner'].search([('name', '=', name)], limit=1)
            if not partner:
                skipped += 1
                continue

            # Фільтрація по типу
            if partner_type == 'company' and not partner.is_company:
                skipped += 1
                continue
            if partner_type == 'person' and partner.is_company:
                skipped += 1
                continue

            # Далі йде стандартна логіка імпорту адрес
            # Можна винести в окремий метод, або викликати self.import_addresses_from_excel() для одного партнера
            # Для простоти — скопіюємо основну частину з import_addresses_from_excel
            addr_legal = str(row.get('Юридический адрес')).strip() if row.get('Юридический адрес') else ''
            addr_physical = str(row.get('Фактичний адрес')).strip() if row.get('Фактичний адрес') else ''
            addr_delivery = str(row.get('Адрес доставки')).strip() if row.get('Адреса доставки') else ''
            phone = str(row.get('Телефон')).strip() if row.get('Телефон') else ''
            email = str(row.get('E-Mail')).strip() if row.get('E-Mail') else ''

            vals = {}
            if phone:
                vals['phone'] = phone
            if email:
                vals['email'] = email
            main_addr = addr_legal if addr_legal else addr_physical
            main_addr_vals = parse_address_list(main_addr)
            if main_addr_vals.get('zip'):
                vals['zip'] = main_addr_vals['zip']
            if main_addr_vals.get('city'):
                vals['city'] = main_addr_vals['city']
            if main_addr_vals.get('street_full'):
                vals['street'] = main_addr_vals['street_full']
            if main_addr_vals.get('country'):
                country_id = self.env['res.country'].search([('name', '=', main_addr_vals['country'])], limit=1)
                if country_id:
                    vals['country_id'] = country_id.id
            if main_addr_vals.get('state'):
                state_id = self.env['res.country.state'].search([('name', '=', main_addr_vals['state'])], limit=1)
                if state_id:
                    vals['state_id'] = state_id.id
            if vals:
                partner.write(vals)

            main_addr_vals['phone'] = phone
            main_addr_vals['email'] = email

            if main_addr and any(main_addr_vals.values()):
                self._set_partner_address(partner, main_addr_vals, 'invoice')
            if addr_delivery:
                delivery_addr_vals = parse_address_list(addr_delivery)
                delivery_addr_vals['phone'] = phone
                delivery_addr_vals['email'] = email
                self._set_partner_address(partner, delivery_addr_vals, 'delivery')
            updated += 1

        write_log("=== Імпорт адрес завершено ===")
        write_log(f"Знайдено контрагентів: {created + updated}")
        write_log(f"Оновлено контрагентів: {updated}")
        write_log(f"Пропущено контрагентів: {skipped}")
        return {
            'created': created,
            'updated': updated,
            'skipped': skipped,
        }

    def _set_partner_address(self, partner, addr_vals, addr_type):
        country_id = self.env['res.country'].search([('name', '=', addr_vals['country'])], limit=1) if addr_vals['country'] else False
        state_id = self.env['res.country.state'].search([('name', '=', addr_vals['state'])], limit=1) if addr_vals['state'] else False

        vals = {}
        if addr_type:
            vals['type'] = addr_type
        if addr_vals.get('zip'):
            vals['zip'] = addr_vals['zip']
        if addr_vals.get('city'):
            vals['city'] = addr_vals['city']
        if addr_vals.get('street_full'):
            vals['street'] = addr_vals['street_full']
        if country_id:
            vals['country_id'] = country_id.id
        if state_id:
            vals['state_id'] = state_id.id
        vals['parent_id'] = partner.id
        if addr_vals.get('phone'):
            vals['phone'] = addr_vals['phone']
        if addr_vals.get('email'):
            vals['email'] = addr_vals['email']

        existing = self.env['res.partner'].search([
            ('parent_id', '=', partner.id),
            ('type', '=', addr_type),
        ], limit=1)

        if existing:
            existing.write(vals)
        else:
            self.env['res.partner'].create(vals)