# -*- coding: utf-8 -*-
"""Перевірка версій — і головне, чи не випала з неї платна надбудова.

Odoo для сторонніх модулів оновлень не перевіряє, тож покупець живе з відомою
помилкою, доки випадково не зайде на сторінку додатка. Для платного це прямо
втрачені гроші: людина не просить повернення, вона просто не оновлюється.
"""
import json
import os
from unittest.mock import patch

from odoo.tests import TransactionCase, tagged

from ..models import adealer_update as updating
from ..models.addon_hint import ADDONS


class _Answer:
    """Замість відповіді requests — жоден тест не ходить у мережу."""

    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


@tagged('post_install', '-at_install')
class TestUpdateCheck(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Update = cls.env['adealer.update']
        cls.params = cls.env['ir.config_parameter'].sudo()

    def _publish(self, versions):
        self.params.set_param(updating.PARAM_LATEST, json.dumps(versions))

    def _installed_version(self):
        module = self.env['ir.module.module'].sudo().search(
            [('name', '=', 'adealer')], limit=1)
        return module.installed_version

    def _newer(self):
        """Вища за встановлену, але тієї самої серії."""
        return '%s.99.0.0' % updating.series_of(self._installed_version())

    # -- порівняння версій --------------------------------------------------
    def test_versions_compare_as_numbers_not_text(self):
        """Як рядок "19.0.1.2.10" стоїть НИЖЧЕ за "19.0.1.2.9"."""
        self.assertGreater(updating.parse_version('19.0.1.2.10'),
                           updating.parse_version('19.0.1.2.9'))

    def test_a_junk_version_does_not_raise(self):
        self.assertEqual(updating.parse_version('19.0.x.1'), (19, 0, 0, 1))
        self.assertEqual(updating.parse_version(''), (0,))
        self.assertEqual(updating.parse_version(None), (0,))

    def test_series_is_the_first_two_numbers(self):
        self.assertEqual(updating.series_of('19.0.1.11.0'), '19.0')
        self.assertEqual(updating.series_of('nonsense'), '')
        self.assertEqual(updating.series_of(None), '')

    # -- що бачить користувач ----------------------------------------------
    def test_newer_version_is_reported_as_outdated(self):
        self._publish({'adealer': self._newer()})
        self.assertIn('adealer', [row[0] for row in self.Update._outdated()])

    def test_same_version_is_not_reported(self):
        self._publish({'adealer': self._installed_version()})
        self.assertEqual(self.Update._outdated(), [])

    def test_older_published_version_is_not_reported(self):
        """Застаріла відповідь не має вмовляти на пониження версії."""
        self._publish({'adealer': '%s.0.0.0' % updating.series_of(
            self._installed_version())})
        self.assertEqual(self.Update._outdated(), [])

    def test_a_version_from_another_series_is_never_offered(self):
        """Номер із чужої гілки веде на модуль, який база встановити не може."""
        self._publish({'adealer': '99.0.1.0.0'})
        self.assertEqual(self.Update._outdated(), [])
        self.assertEqual(self.Update.update_banner(), (False, False))

    def test_only_our_modules_are_believed(self):
        self._publish({'account': '99.0', 'adealer': self._newer()})
        self.assertEqual([row[0] for row in self.Update._outdated()],
                         ['adealer'])

    def test_the_banner_names_the_addon_the_way_the_store_does(self):
        """У банері має стояти назва з магазину, а не технічне ім'я модуля.

        «adealer_pro_sales» покупцеві ні про що не каже — він купував
        «3A-dealer Sales Pro» і саме цю назву шукатиме на сторінці.
        """
        message, url = self.Update.with_context()._banner_for(
            'adealer_pro_sales', '19.0.1.1.2', '19.0.1.2.0')
        self.assertIn('Sales Pro', message)
        self.assertIn('adealer_pro_sales', url)

    # -- сама перевірка -----------------------------------------------------
    def test_check_is_skipped_when_switched_off(self):
        self.params.set_param(updating.PARAM_UPDATE_CHECK, 'off')
        with patch('requests.get') as get:
            self.assertFalse(self.Update._cron_check())
        get.assert_not_called()

    def test_unset_means_on(self):
        """Запит не несе нічого про користувача, тож база без відповіді перевіряє."""
        self.params.set_param(updating.PARAM_UPDATE_CHECK, False)
        self.assertTrue(self.Update._enabled())

    def test_an_unreachable_server_is_not_an_incident(self):
        self.params.set_param(updating.PARAM_UPDATE_CHECK, 'on')
        with patch('requests.get', side_effect=OSError('no route to host')):
            self.assertFalse(self.Update._cron_check())

    def test_a_failed_check_says_why(self):
        """Добова задача мовчить; людина з кнопкою — ні."""
        self.params.set_param(updating.PARAM_UPDATE_CHECK, 'on')
        with patch('requests.get', side_effect=OSError('no route to host')):
            ok, reason = self.Update._run_check()
        self.assertFalse(ok)
        self.assertIn('no route to host', reason)

    def test_a_good_answer_is_stored(self):
        self.params.set_param(updating.PARAM_UPDATE_CHECK, 'on')
        newer = self._newer()
        with patch('requests.get',
                   return_value=_Answer({'adealer': newer, 'evil': {'x': 1}})):
            self.assertTrue(self.Update._cron_check())
        self.assertEqual(self.Update._published(), {'adealer': newer})

    def test_the_request_asks_for_our_own_series(self):
        self.params.set_param(updating.PARAM_UPDATE_CHECK, 'on')
        with patch('requests.get',
                   return_value=_Answer({'adealer': self._newer()})) as get:
            self.Update._run_check()
        self.assertEqual(
            get.call_args.kwargs.get('params'),
            {'series': updating.series_of(self._installed_version())})


@tagged('post_install', '-at_install')
class TestPaidAddonsAreCovered(TransactionCase):
    """🔴 Те, заради чого все це й писалося.

    Перевірка в `app_update.py` існує з самого початку, але дивиться лише на сам
    `adealer`. Шість платних надбудов (€49..€149) не покривала жодна: їхні
    покупці не могли дізнатися про виправлення взагалі ніяк, і жоден тест на це
    не вказував — забутий модуль нічого не ламає.
    """

    def test_every_paid_addon_is_in_the_list(self):
        missing = set(ADDONS) - set(updating.KNOWN_MODULES)
        self.assertFalse(
            missing,
            "платні надбудови поза перевіркою версій: %s. Їхні покупці ніколи "
            "не дізнаються про виправлення." % ', '.join(sorted(missing)))

    def test_the_list_is_not_hand_written(self):
        """Список має походити з ADDONS, а не бути другою копією.

        Дві копії неминуче розходяться, і розходяться мовчки. Якщо тут колись
        зʼявиться рукописний перелік — цей тест впаде на першій же новій
        надбудові, доданій у підказки.
        """
        self.assertTrue(set(ADDONS).issubset(set(updating.KNOWN_MODULES)))
        self.assertIn('adealer', updating.KNOWN_MODULES)

    def test_every_module_on_disk_is_listed(self):
        """І навпаки: модуль, який лежить поруч, але ніде не згаданий.

        Сканує теки-сусіди, тож падає на НАСТУПНІЙ надбудові, а не лише на вже
        відомих. Саме так `bank_sync_privat` пролежав чотири дні непоміченим.
        """
        from odoo.addons import adealer

        addons = os.path.dirname(os.path.dirname(adealer.__file__))
        missing = ours_beside(addons) - set(updating.KNOWN_MODULES)
        self.assertFalse(
            missing,
            "модулі є, а в KNOWN_MODULES їх нема: %s" % ', '.join(sorted(missing)))

    def test_the_scan_is_not_vacuous(self):
        """Скан, який нічого не знаходить, проходить вхолосту.

        У покупця сусідніх модулів може не бути взагалі, тому «знайшлось
        нерівне нулю» тут стверджувати не можна — перевіряємо сам сканер на
        теці, зробленій для цього.
        """
        import tempfile

        def write(root, name, spec):
            os.makedirs(os.path.join(root, name))
            with open(os.path.join(root, name, '__manifest__.py'), 'w',
                      encoding='utf-8') as handle:
                handle.write(repr(spec))

        with tempfile.TemporaryDirectory() as root:
            write(root, 'adealer', {'author': 'chukhin', 'depends': []})
            write(root, 'adealer_new', {'author': 'chukhin',
                                        'depends': ['adealer']})
            write(root, 'adealer_theirs', {'author': 'someone',
                                           'depends': ['adealer']})
            write(root, 'bank_sync_base', {'author': 'chukhin',
                                           'depends': ['account']})
            os.makedirs(os.path.join(root, 'not_a_module'))

            self.assertEqual(ours_beside(root), {'adealer_new'})


def ours_beside(addons_dir):
    """Наші модулі поруч, які стоять на `adealer`.

    Обидві половини правила потрібні: автор не дає чужій надбудові валити нашу
    збірку, а залежність не пускає в цей список наш же модуль з іншої лінійки.
    """
    found = set()
    for name in sorted(os.listdir(addons_dir)):
        manifest = os.path.join(addons_dir, name, '__manifest__.py')
        if name == 'adealer' or not os.path.isfile(manifest):
            continue
        try:
            with open(manifest, encoding='utf-8') as handle:
                spec = eval(handle.read(), {'__builtins__': {}})  # noqa: S307
        except Exception:  # noqa: BLE001 — не маніфест, який ми вміємо читати
            continue
        if (isinstance(spec, dict) and spec.get('author') == 'chukhin'
                and 'adealer' in (spec.get('depends') or [])):
            found.add(name)
    return found


@tagged('post_install', '-at_install')
class TestBannerIsVisible(TransactionCase):
    """Банер, якого ніхто не бачить, — це відсутній банер.

    Тести читають поля напряму й під superuser, тож ані брак поля на формі, ані
    брак права доступу тут не спливе. Ці два хоча б доводять, що поле є на тій
    моделі, на яку його ставить вигляд.
    """

    def test_the_car_form_can_show_the_banner(self):
        for name in ('update_message', 'update_url'):
            self.assertIn(name, self.env['dealer.car']._fields)

    def test_the_repair_order_can_show_the_banner(self):
        for name in ('update_message', 'update_url'):
            self.assertIn(name, self.env['repair.order']._fields)

    def test_the_settings_page_actually_renders(self):
        view = self.env['res.config.settings'].get_view(view_type='form')
        self.assertIn('adealer_addons_status', view['arch'])

    def test_settings_never_claim_everything_is_current_without_checking(self):
        """🔴 Помилка, що виглядає точно як успіх.

        Без відповіді «усе свіже» — це здогад, поданий як факт, а покупець, який
        вірить, що в нього найновіше, — рівно те, чого ця перевірка має не
        допустити.
        """
        self.env['ir.config_parameter'].sudo().set_param(
            updating.PARAM_LATEST, False)
        status = self.env['res.config.settings']._adealer_addons_status()
        self.assertNotIn('up to date', status)
