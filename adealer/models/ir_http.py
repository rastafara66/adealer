# -*- coding: utf-8 -*-
from odoo import models


class IrHttp(models.AbstractModel):
    _inherit = 'ir.http'

    def session_info(self):
        res = super().session_info()
        try:
            val = self.env['ir.config_parameter'].sudo().get_param('adealer.sidebar_enabled', 'True')
            res['adealer_sidebar_enabled'] = val in ('True', 'true', '1')
        except Exception:
            res['adealer_sidebar_enabled'] = False
        if res.get('uid') and not res.get('home_action_id'):
            home = self._adealer_home_action_id(self.env.user)
            if home:
                res['home_action_id'] = home
        return res

    def _adealer_home_action_id(self, user):
        """Що відкрити після входу, якщо людина сама нічого не вибрала.

        🔴 Правило власника 15.09.2026: **менеджер після входу потрапляє на
        дашборд 3A-dealer**, а бухгалтер — на дашборд бухгалтерського додатка.
        Без цього Odoo відкриває перший застосунок у сітці — для менеджера
        салону це найчастіше «Обговорення», і першу хвилину робочого дня він
        шукає, де його наряди.

        Порядок пріоритетів — так, щоб він не залежав від порядку завантаження
        модулів і модулі не знали один про одного:

        * явний вибір людини («Home page» у Налаштуваннях, `res.users.action_id`)
          — завжди перший, його не чіпає ніхто;
        * бухгалтерський додаток ставить свою головну бухгалтерам ЗАВЖДИ;
        * 3A-dealer ставить свою лише тоді, коли ніхто інший ще не поставив
          (перевірка `home_action_id` у `session_info` вище).

        Хто б не виконався першим, бухгалтер опиниться в бухгалтерії, а
        менеджер — тут.
        """
        if user.action_id or not user._is_internal():
            return False
        if not user.has_group('adealer.group_adealer_user'):
            return False
        action = self.env.ref('adealer.action_dashboard', raise_if_not_found=False)
        return action.id if action else False
