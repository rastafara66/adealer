# -*- coding: utf-8 -*-

from . import controllers
from . import models


def post_init_hook(env):
    """Призначити вбудовані логотипи наявним маркам авто при встановленні
    та зробити дашборд «Головна» стартовою сторінкою за замовчуванням."""
    env['fleet.vehicle.model.brand'].search([])._apply_bundled_logo()
    _set_default_home(env)
    # Номери контрагентів, що вже є в базі, — за правилом «код ЄДРПОУ/РНОКПП і ІПН» (models/ua_tax_ids.py).
    env['res.partner']._l10n_ua_normalize_tax_ids()
    # Групи товарів, що були в базі до встановлення, — іконки за назвою.
    env['product.category'].search([('adealer_icon', '=', False)])._adealer_pick_icon()


def _set_default_home(env):
    """Дашборд «Головна» як home-дія для внутрішніх користувачів без своєї стартової.
    Не чіпає тих, хто вже обрав власну стартову сторінку (action_id заповнений)."""
    action = env.ref('adealer.action_dashboard', raise_if_not_found=False)
    if not action:
        return
    users = env['res.users'].search([('share', '=', False), ('action_id', '=', False)])
    if users:
        users.write({'action_id': action.id})