import pandas as pd
import math
from odoo import models, api, _
from odoo.exceptions import UserError
import logging
import os
import re

# TODO: Додати імпорт коментарів
_logger = logging.getLogger(__name__)

LOG_PATH = os.path.join(os.path.dirname(__file__), '..', 'log', 'import.log')

def write_log(msg):
    # msg - це str, тут явно кодуємо в utf-8
    with open(LOG_PATH, 'a', encoding='utf-8') as f:
        f.write(msg + '\n')

def safe_val(val, cast_func=None):
    if val is None:
        return False
    if isinstance(val, float) and math.isnan(val):
        return False
    if isinstance(val, str) and not val.strip():
        return False
    if cast_func:
        try:
            return cast_func(val)
        except Exception:
            return False
    return val

class PartnerImport(models.TransientModel):
    _name = 'res.partner.import'
    _description = 'Import partners from Excel'

    @api.model
    def import_partners_from_excel(self):
        # TODO: Додати вибір файлу через діалог
        write_log(f"=== Початок імпорту контрагентів з Excel ===")
        file_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'import_partners.xlsx')
        write_log(f"Файл: {file_path}")

        try:
            df = pd.read_excel(file_path)
        except Exception as e:
            raise UserError(_('Could not open the file: %s') % e)

        return self.import_partners_from_dataframe(df)

    @api.model
    def import_partners_from_dataframe(self, df):
        skipped_no_data = 0
        skipped_duplicate = 0
        added = 0

        for idx, row in df.iterrows():
            name = safe_val(row.get('Наименование'))
            phone = safe_val(row.get('Телефон'))
            email = safe_val(row.get('E-mail'))
            inn = safe_val(row.get('ИНН'))
            address = safe_val(row.get('Адрес'))
            raw_edrpou = safe_val(row.get('Код по ЕГРПОУ'))
            edrpou = False
            edrpou_note = ''
            if raw_edrpou:
                # Залишаємо тільки цифри
                edrpou_clean = re.sub(r'\D', '', str(raw_edrpou))
                # Перевіряємо довжину
                if len(edrpou_clean) in (8, 10):
                    edrpou = edrpou_clean
                else:
                    edrpou_note = f"Некоректний код ЄДРПОУ з файлу: {raw_edrpou}"

            def to_str(val):
                if isinstance(val, str):
                    return val
                try:
                    return str(val)
                except Exception:
                    return ''
            log_row = f"Рядок: {to_str(name)}, {to_str(phone)}, {to_str(email)}, {to_str(inn)}, {to_str(address)}, {to_str(edrpou)}"

            if not name:
                write_log(f"Пропущено рядок без імені: {log_row}")
                continue

            if not any([phone, email, inn, address, edrpou]):
                write_log(f"Пропущено рядок без даних: {log_row}")
                skipped_no_data += 1
                continue

            # Динамічний пошук по edrpou, vat, name
            search_domain = []
            if edrpou:
                search_domain.append(('edrpou', '=', edrpou))
            if inn:
                search_domain.append(('vat', '=', inn))
            if name:
                search_domain.append(('name', '=', name))

            # Partner
            partner = None
            if search_domain:
                domain = ['|'] * (len(search_domain) - 1) + search_domain
                partner = self.env['res.partner'].search(domain, limit=1)

            if partner:
                updated = False
                # Якщо у партнера немає edrpou, але він є у файлі — дописати
                if edrpou and not partner.edrpou:
                    partner.edrpou = edrpou
                    updated = True
                # Якщо тип не співпадає — виправити
                is_company_should = True if edrpou else False
                if partner.is_company != is_company_should:
                    partner.is_company = is_company_should
                    updated = True
                if updated:
                    write_log(f"Оновлено партнера: {log_row}")
                else:
                    write_log(f"Дубльований партнер: {log_row}")
                skipped_duplicate += 1
                continue

            vals = {
                'name': name,
                'phone': phone,
                'email': email,
                'vat': inn,
                'street': address,
                'edrpou': edrpou,
                'is_company': True if edrpou else False,
                'parent_id': False,  # Створюємо тільки основні контакти
            }
            if edrpou_note:
                vals['comment'] = edrpou_note

            partner = self.env['res.partner'].create(vals)
            write_log(f"Додано партнера: {log_row}")
            added += 1

        write_log(f"=== Імпорт завершено ===")
        write_log(f"Пропущено без даних: {skipped_no_data}")
        write_log(f"Дубльованих: {skipped_duplicate}")
        write_log(f"Додано партнерів: {added}")
        return {
            'skipped_no_data': skipped_no_data,
            'skipped_duplicate': skipped_duplicate,
            'added': added,
        }