# -*- coding: utf-8 -*-
"""Сказати користувачеві, що вийшла новіша версія — і про надбудови теж.

🔴 Навіщо. Odoo для сторонніх модулів оновлень не перевіряє: її кнопка
«Оновити» порівнює встановлене з тим, що **вже лежить на диску**, і магазин не
питає ніколи. Покупець, який завантажив збірку з помилкою, житиме з нею вічно,
доки випадково не зайде на сторінку додатка. У Bank Sync так і сталося: збій
виправили й опублікували протягом години, а всі наявні інсталяції лишились
зламаними.

🔴 Чого бракувало саме тут. Перевірка в `app_update.py` є з самого початку, але
вона дивиться **лише на сам `adealer`** — читає його маніфест на GitHub. Шість
платних надбудов (€49..€149, разом €624) не покривала жодна: їхні покупці не
могли дізнатися про виправлення взагалі ніяк. Для платного це прямо втрачені
гроші — людина не просить повернення, вона просто не оновлюється.

Приватний репозиторій надбудов через raw.githubusercontent не читається, тому
джерело тут інше: спільний приймач лінійки, який бере версії з маніфестів гілки
`19.0`, тобто з того, що справді роздає магазин.

Властивості перевірки (ті самі, що в Bank Sync і «Активі»):

* **GET без ідентифікатора** — ні install id, ні назви бази, ні навіть вашої
  версії. Єдине, що їде, — серія Odoo, і вона однакова в усіх інсталяцій серії.
  Тут нема чого зважувати, тому ввімкнено типово, на відміну від звітів про
  помилки;
* **раз на добу** плановою дією, ніколи під час відкриття сторінки;
* **ніколи не падає**: невдача поглинається, база без відповіді просто не
  показує банера. Виняток — ручна перевірка: людині, яка натиснула кнопку,
  треба сказати причину, інакше «у вас найновіше» і «запит не пішов» виглядають
  однаково.

Встановити банер нічого не може — модуль, покладений у теку руками, замінюється
так само руками, — тож обіцяти оновлення в один клік було б брехнею.
"""
import json
import logging

from odoo import _, api, fields, models

from .addon_hint import ADDONS

_logger = logging.getLogger(__name__)

PARAM_UPDATE_CHECK = 'adealer.update_check'
PARAM_LATEST = 'adealer.latest_versions'
PARAM_URL = 'adealer.versions_url'
PARAM_CHECKED = 'adealer.latest_checked'

# Той самий приймач, що й у решти лінійки: він читає версії з маніфестів гілки
# 19.0 — з того, що роздає магазин. Другий сервіс заради другого продукту був би
# другим місцем, яке треба памʼятати оновити.
DEFAULT_URL = 'https://yellow.in.ua/bank-sync/latest'

CHECK_TIMEOUT = 10

# 🔴 Список НЕ пишемо вручну: платні надбудови вже перелічені в `ADDONS` —
# там, де живуть підказки про них. Другий рукописний список неминуче розійшовся
# б із першим, і розійшовся б мовчки: забутий рядок нічого не ламає, просто
# покупці того модуля ніколи не дізнаються про виправлення. Саме так
# `bank_sync_privat` пролежав чотири дні.
KNOWN_MODULES = ('adealer', 'adealer_theme') + tuple(sorted(ADDONS))


def series_of(version):
    """``"19.0.1.11.0"`` -> ``"19.0"``. Порожньо, коли читати нема чого.

    Порівнювати версії різних серій не можна: як числа `19.0.1.0.0` більше за
    `18.0.9.9.9`, тож інсталяція старішої серії отримала б пропозицію оновитись
    на модуль, який вона встановити НЕ МОЖЕ. `adealer` зараз лише на 19.0, але
    коштує це один рядок, а пастка спрацьовує тихо й одразу для всіх.
    """
    parts = (version or '').split('.')
    return '.'.join(parts[:2]) if len(parts) >= 2 else ''


def parse_version(text):
    """``"19.0.1.2.10"`` -> ``(19, 0, 1, 2, 10)``.

    🔴 Числами, а не текстом: як рядок ``"19.0.1.2.10"`` стоїть **нижче** за
    ``"19.0.1.2.9"``, і десяте виправлення серії перестало б пропонуватись —
    саме тоді, коли виправлень уже десять і оновитись найважливіше.
    """
    parts = []
    for chunk in (text or '').split('.'):
        try:
            parts.append(int(chunk))
        except ValueError:
            parts.append(0)
    return tuple(parts)


class AdealerUpdate(models.AbstractModel):
    _name = 'adealer.update'
    _description = '3A-dealer version check'

    @api.model
    def _known_modules(self):
        """Список як метод моделі, а не імпорт константи.

        `app_update.py` імпортується раніше за цей файл, а `addon_hint`, з якого
        береться перелік, — навмисно найпізніше. Виклик через реєстр робить
        порядок імпортів неважливим.
        """
        return KNOWN_MODULES

    @api.model
    def _enabled(self):
        # Незаданий параметр означає «увімкнено»: запит не несе нічого про
        # користувача, а перевірка, про яку ніхто не знає, ніколи б не вмикалась.
        return self.env['ir.config_parameter'].sudo().get_param(
            PARAM_UPDATE_CHECK, 'on') != 'off'

    @api.model
    def _series(self):
        module = self.env['ir.module.module'].sudo().search(
            [('name', '=', 'adealer')], limit=1)
        return series_of(module.installed_version)

    @api.model
    def _run_check(self):
        """Виконати перевірку й сказати, що сталося. Повертає ``(ok, причина)``."""
        if not self._enabled():
            return False, _("Version checking is switched off.")
        params = self.env['ir.config_parameter'].sudo()
        url = params.get_param(PARAM_URL, DEFAULT_URL)
        if not url:
            return False, _("No address is configured for the version check.")

        import requests
        series = self._series()
        try:
            response = requests.get(url, timeout=CHECK_TIMEOUT,
                                    params={'series': series} if series else None)
            response.raise_for_status()
            published = response.json()
        except Exception as error:  # noqa: BLE001 — пропущена перевірка не подія
            return False, _("Could not reach %(url)s: %(error)s",
                            url=url, error=error)
        if not isinstance(published, dict):
            return False, _("%s answered with something that is not a version "
                            "list.", url)

        # Лише наші, і лише зі своєї серії. Номер із чужої гілки веде на модуль,
        # який ця база встановити не може, — це гірше за мовчання.
        clean = {name: str(published[name])[:32]
                 for name in KNOWN_MODULES
                 if isinstance(published.get(name), str)
                 and (not series or series_of(published[name]) == series)}
        if not clean:
            return False, _("%(url)s knows of no %(series)s version of these "
                            "modules.", url=url, series=series or '?')
        params.set_param(PARAM_LATEST, json.dumps(clean))
        params.set_param(PARAM_CHECKED,
                         fields.Datetime.to_string(fields.Datetime.now()))
        return True, ''

    @api.model
    def _cron_check(self):
        """Добова задача: ніколи не падає, нічого не звітує, тихо оновлює кеш."""
        ok, reason = self._run_check()
        if not ok and reason:
            _logger.info("3A-dealer version check skipped: %s", reason)
        return ok

    @api.model
    def _published(self):
        raw = self.env['ir.config_parameter'].sudo().get_param(PARAM_LATEST)
        try:
            return json.loads(raw) if raw else {}
        except ValueError:
            return {}

    @api.model
    def _outdated(self):
        """Наші встановлені модулі, для яких опубліковано новішу версію.

        Повертає ``[(модуль, встановлено, опубліковано)]``.
        """
        published = self._published()
        if not published:
            return []
        modules = self.env['ir.module.module'].sudo().search(
            [('name', 'in', KNOWN_MODULES), ('state', '=', 'installed')])
        out = []
        for module in modules:
            latest = published.get(module.name)
            if not latest:
                continue
            # Друга перевірка серії, цього разу на кешованих даних: збережена
            # відповідь переживає запит, що її приніс, і після переїзду бази на
            # іншу серію Odoo почала б рекламувати стару гілку.
            if series_of(latest) != series_of(module.installed_version):
                continue
            if parse_version(latest) > parse_version(module.installed_version):
                out.append((module.name, module.installed_version, latest))
        return out

    @api.model
    def _store_url(self, name, series):
        """Адреса сторінки в магазині — з правильної РОДИНИ і правильної СЕРІЇ.

        🔴 Дві пастки, обидві дають посилання в нікуди, і обидві тихі:

        1. **Тема — не модуль.** Теми лежать під `/apps/themes/`, звичайні
           додатки — під `/apps/modules/`. `adealer_theme` має категорію
           `Themes/Backend`, і посилання «модульного» виду на неї віддає 404.
           Я на цьому спіймався 05.09.2026 навпаки: перевіряв тему модульною
           адресою, отримав 404 і сказав власникові, що тему не опубліковано.
           Вона була опублікована весь час.
        2. **Серія.** Сторінка є для кожної серії окремо, і посилати
           інсталяцію 16.0 на сторінку 19.0 означає пропонувати збірку, яку
           вона встановити не може, — та сама помилка, від якої захищає
           `series_of()` у порівнянні версій.

        Родину визначаємо з категорії самого модуля, а не зі списку назв:
        список довелося б памʼятати оновлювати, а категорія вже лежить у базі.
        """
        category = self.env['ir.module.module'].sudo().search(
            [('name', '=', name)], limit=1).category_id
        family = 'modules'
        # Категорія 'Themes/Backend' у базі — це дитина 'Backend' у батька
        # 'Themes', тож дивимось і на предків.
        while category:
            if (category.name or '').strip().lower() == 'themes':
                family = 'themes'
                break
            category = category.parent_id
        return 'https://apps.odoo.com/apps/%s/%s/%s/' % (
            family, series or '19.0', name)

    @api.model
    def _banner_for(self, name, installed, latest):
        """Текст і посилання для одного модуля.

        🔴 Назва — та, що в магазині, а не технічне ім'я: «adealer_pro_sales»
        покупцеві ні про що не каже, він купував «3A-dealer Sales Pro» і саме це
        шукатиме на сторінці. `ADDONS` уже тримає ці назви для підказок.
        """
        title = ADDONS.get(name, {}).get('title') or name
        return _("A newer version of %(module)s is available: %(latest)s "
                 "(you have %(installed)s).",
                 module=title, latest=latest, installed=installed), \
            self._store_url(name, series_of(installed))

    @api.model
    def update_banner(self):
        """Текст банера й посилання, або ``(False, False)``.

        Коли застаріло кілька модулів, називаємо перший і кажемо, скільки ще:
        повний список перетворює банер на стіну тексту, яку не читають.
        """
        outdated = self._outdated()
        if not outdated:
            return False, False
        message, url = self._banner_for(*outdated[0])
        if len(outdated) > 1:
            message += ' ' + _("%s more of your 3A-dealer modules can be "
                               "updated too.", len(outdated) - 1)
        return message, url


class DealerCarUpdateBanner(models.Model):
    """Банер — на картці авто: центральний екран салону, його відкривають щодня.

    У налаштуваннях його побачив би лише той, хто вже пішов шукати оновлення, —
    а це рівно та проблема, через яку штатна кнопка «Оновити» й не рятує.
    """
    _inherit = 'dealer.car'

    update_message = fields.Char(compute='_compute_update_message')
    update_url = fields.Char(compute='_compute_update_message')

    def _compute_update_message(self):
        # Питаємо один раз на весь набір: відповідь не залежить від запису.
        message, url = self.env['adealer.update'].update_banner()
        for car in self:
            car.update_message = message
            car.update_url = url


class RepairOrderUpdateBanner(models.Model):
    """Те саме в наряді — другий екран, за яким сидять цілий день."""
    _inherit = 'repair.order'

    update_message = fields.Char(compute='_compute_update_message')
    update_url = fields.Char(compute='_compute_update_message')

    def _compute_update_message(self):
        message, url = self.env['adealer.update'].update_banner()
        for order in self:
            order.update_message = message
            order.update_url = url
