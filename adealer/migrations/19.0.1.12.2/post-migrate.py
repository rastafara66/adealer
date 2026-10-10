# -*- coding: utf-8 -*-
"""Доприкласти під'єднання наших груп до штатних — того, чого XML не може.

🔴 ЧОМУ ЦЕ НЕ РОБИТЬСЯ ЗВИЧАЙНИМ ЗАПИСОМ У XML.

`base.group_user` має в `ir_model_data` прапорець **`noupdate=True`** (а
`base.group_system` — ні, тому та половина працювала). Odoo застосовує такі
записи при ПЕРШОМУ встановленні модуля й мовчки пропускає при ОНОВЛЕННІ.

Наслідок, зміряний 10.09.2026:

    чиста база, `-i adealer`:   base.group_user -> Користувач = True   ✔
    наявна база, `-u adealer`:  base.group_user -> Користувач = False  ✘

Тобто новий покупець отримував робочий модуль, а кожен наявний — «Помилка
доступу: у вас немає доступу до записів «Рядок наряду» (repair.line)» на
кожному документі. Меню на місці, дані на місці, модуль «встановлено».

⚠️ І цього не видно звідти, звідки дивляться: інсталл у чисту базу (§4)
проходив бездоганно, тести зелені (§7 — вони під superuser), збірка чиста.
Ламалось рівно те, чого жодна перевірка не робила: оновлення наявної бази.

Власник, 10.09.2026: «це НАЙПОШИРЕНІША помилка всіх додатків в магазині»,
«треба — встановив і ВСЕ працює».
"""
import logging

_logger = logging.getLogger(__name__)

#: (штатна група, наша група) — кого чим наділяємо.
WIRING = [
    ("base.group_user", "adealer.group_adealer_user"),
    ("base.group_system", "adealer.group_adealer_manager"),
    # 🔴 І навпаки: наш «Користувач» успадковує штатні групи тих додатків,
    # меню яких ми показуємо. Без цього співробітник не відкриває навіть
    # наряд-замовлення: меню наше, а права на модель дає чужа група.
    # Зміряно: 35 недоступних моделей із 52, до яких ведуть наші меню.
    # ⚠️ Окремої групи «Ремонт» в Odoo 19 НЕМАЄ: наряд-замовлення
    # відкриває stock.group_stock_user. Вигаданий xmlid валить
    # завантаження реєстру цілком («External ID not found»).
    ("adealer.group_adealer_user", "sales_team.group_sale_salesman"),
    ("adealer.group_adealer_user", "purchase.group_purchase_user"),
    ("adealer.group_adealer_user", "stock.group_stock_user"),
    ("adealer.group_adealer_user", "fleet.fleet_group_user"),
    ("adealer.group_adealer_user", "account.group_account_invoice"),
]


def migrate(cr, version):
    if not version:
        return                      # перше встановлення — XML уже все зробив

    from odoo import api, SUPERUSER_ID
    env = api.Environment(cr, SUPERUSER_ID, {})

    fixed = []
    for base_xid, our_xid in WIRING:
        base_group = env.ref(base_xid, raise_if_not_found=False)
        our_group = env.ref(our_xid, raise_if_not_found=False)
        if not base_group or not our_group:
            _logger.warning("групи %s або %s немає — пропускаю", base_xid, our_xid)
            continue
        if our_group in base_group.implied_ids:
            continue                # ідемпотентно: уже під'єднано
        base_group.write({"implied_ids": [(4, our_group.id)]})
        fixed.append("%s -> %s" % (base_xid, our_xid))

    if fixed:
        _logger.info("доприкладено під'єднання груп: %s", "; ".join(fixed))
    else:
        _logger.info("під'єднання груп уже на місці")
