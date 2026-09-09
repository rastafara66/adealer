from .excel_util import read_xlsx_rows
from .error_report import report_errors
import math
from odoo import models, api, _
from odoo.exceptions import UserError
import logging
import os
import re

# TODO: Додати імпорт коментарів
_logger = logging.getLogger(__name__)

def write_log(msg):
    """Технічний слід імпорту — у журнал Odoo.

    🔴 Раніше писалось у файл ВСЕРЕДИНІ теки модуля (`adealer/log/import.log`).
    Дві біди. По-перше, у більшості установок `addons` доступна лише для
    читання, і тоді `open(..., 'a')` валив увесь імпорт помилкою запису, яка
    не має жодного стосунку до даних. По-друге, це був ЄДИНИЙ слід того, які
    рядки пропущено, — тобто користувач не бачив їх ніколи.

    Тепер слід іде в журнал сервера, а те, що стосується користувача,
    повертається йому звітом (конвенції §9).
    """
    _logger.info("[adealer import] %s", msg)

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
    @report_errors('import_partners')
    def import_partners_from_excel(self):
        # TODO: Додати вибір файлу через діалог
        write_log(f"=== Початок імпорту контрагентів з Excel ===")
        file_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'import_partners.xlsx')
        write_log(f"Файл: {file_path}")

        try:
            df = read_xlsx_rows(file_path)
        except Exception as e:
            raise UserError(_('Could not open the file: %s') % e)

        return self.import_partners_from_dataframe(df)

    @api.model
    def import_partners_from_dataframe(self, df):
        """Імпорт із ЗВІТОМ: що додано, що пропущено і чому саме.

        🔴 Конвенції §9. Раніше метод повертав словник лічильників, який
        Odoo нікуди не показувала, а причини пропусків писались у файл
        збоку. Тобто користувач бачив рівно нічого: рядки зникали мовчки,
        і дізнатись про це можна було, лише перерахувавши контрагентів.

        Тепер кожен пропущений рядок називає СЕБЕ — номером у файлі,
        причиною і тим, що з цим робити.
        """
        skipped_no_data = 0
        skipped_duplicate = 0
        added = 0
        updated_count = 0
        problems = []

        def note(idx, what, why, howto):
            # Номер рядка ЯК У ФАЙЛІ: заголовок + нумерація з одиниці.
            problems.append({
                "row": idx + 2, "what": what, "why": why, "howto": howto,
            })

        for idx, row in enumerate(df):
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
                note(idx, _("немає назви"),
                     _("контрагента без назви створити не можна"),
                     _("заповніть колонку «Наименование» або приберіть рядок"))
                skipped_no_data += 1
                continue

            if not any([phone, email, inn, address, edrpou]):
                write_log(f"Пропущено рядок без даних: {log_row}")
                note(idx, _("«%s» — лише назва") % name,
                     _("немає жодного реквізиту: ні телефону, ні пошти, "
                       "ні коду, ні адреси"),
                     _("додайте хоч один реквізит — інакше контрагента "
                       "не буде з чим зіставити"))
                skipped_no_data += 1
                continue

            if edrpou_note:
                note(idx, _("«%s» — код ЄДРПОУ не взято") % name,
                     _("у файлі «%s»: має бути 8 або 10 цифр") % raw_edrpou,
                     _("контрагента створено без коду; виправте код у файлі "
                       "й повторіть імпорт, або допишіть код у картці"))

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
                    updated_count += 1
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

        write_log("=== Імпорт завершено ===")
        write_log(f"Пропущено без даних: {skipped_no_data}")
        write_log(f"Дубльованих: {skipped_duplicate}")
        write_log(f"Додано партнерів: {added}")
        return {
            'rows': len(df),
            'skipped_no_data': skipped_no_data,
            'skipped_duplicate': skipped_duplicate,
            'updated': updated_count,
            'added': added,
            'problems': problems,
        }

    @api.model
    def format_import_report(self, result):
        """Звіт для людини: спершу обсяг, потім кожен рядок із причиною.

        ⚠️ Порядок навмисний. Обсяг першим — щоб було видно, скільки роботи,
        ще до читання переліку; без нього людина читає двадцять рядків, аби
        зрозуміти, що їх двадцять.
        """
        lines = [
            _("Оброблено рядків: %s") % result.get('rows', 0),
            _("Додано контрагентів: %s") % result.get('added', 0),
            _("Оновлено: %s") % result.get('updated', 0),
            _("Пропущено як дублікати: %s") % result.get('skipped_duplicate', 0),
            _("Пропущено без даних: %s") % result.get('skipped_no_data', 0),
        ]
        problems = result.get('problems') or []
        if problems:
            lines.append("")
            lines.append(_("Потребують уваги — %s:") % len(problems))
            for p in problems:
                lines.append(_("Рядок %(row)s: %(what)s\n    Чому: %(why)s\n"
                               "    Що зробити: %(howto)s",
                               row=p['row'], what=p['what'],
                               why=p['why'], howto=p['howto']))
        else:
            # 🔴 Успіх теж пояснює себе: «нічого не сказали» і «все чисто»
            # мусять виглядати по-різному.
            lines.append("")
            lines.append(_("Рядків із проблемами немає."))
        return "\n".join(lines)