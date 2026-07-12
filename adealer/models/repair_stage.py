# -*- coding: utf-8 -*-
"""Стадії наряду (kanban-дошка СТО) та журнал станів
(аналог 1С «Альфа-Авто»: Перечисление.СостояниеЗаказНаряда +
РегистрСведений.ЖурналСостояний).

Нативний repair.order має технічний state (draft/confirmed/done/cancel).
Тут додаємо бізнесову стадію (stage_id) з довільним набором станів СТО —
для наочної kanban-дошки завантаження сервісу та історії переходів.
"""
from odoo import models, fields, api


class RepairStage(models.Model):
    _name = 'adealer.repair.stage'
    _description = 'Стадія наряду'
    _order = 'sequence, id'

    name = fields.Char('Назва', required=True, translate=True)
    sequence = fields.Integer('Порядок', default=10)
    fold = fields.Boolean('Згорнута у kanban',
                          help='Згорнути колонку на дошці (для фінальних стадій)')
    is_closing = fields.Boolean('Завершальна',
                                help='Наряд у цій стадії вважається закритим')
    description = fields.Text('Опис')
    active = fields.Boolean(default=True)


class RepairStageHistory(models.Model):
    _name = 'adealer.repair.stage.history'
    _description = 'Історія станів наряду'
    _order = 'change_date desc, id desc'

    repair_id = fields.Many2one('repair.order', 'Наряд', required=True,
                                ondelete='cascade', index=True)
    stage_id = fields.Many2one('adealer.repair.stage', 'Стадія')
    change_date = fields.Datetime('Дата зміни', default=fields.Datetime.now)
    user_id = fields.Many2one('res.users', 'Хто змінив', default=lambda self: self.env.user)


class RepairOrderStage(models.Model):
    _inherit = 'repair.order'

    # БЕЗ Python-default: інакше при оновленні модуля default застосується до
    # всіх наявних нарядів і зробить SELECT з ще не створеної таблиці стадій.
    # Стадію за замовчуванням ставимо у create() (виконується під час роботи).
    stage_id = fields.Many2one('adealer.repair.stage', 'Стадія',
                               group_expand='_read_group_stage_ids',
                               tracking=True, copy=False, index=True)
    stage_history_ids = fields.One2many('adealer.repair.stage.history', 'repair_id',
                                        'Історія станів')

    @api.model
    def _read_group_stage_ids(self, stages, domain):
        return stages.search([], order='sequence, id')

    @api.model_create_multi
    def create(self, vals_list):
        default_stage = self.env['adealer.repair.stage'].search([], order='sequence, id', limit=1)
        for vals in vals_list:
            if not vals.get('stage_id') and default_stage:
                vals['stage_id'] = default_stage.id
        return super().create(vals_list)

    def write(self, vals):
        if 'stage_id' in vals and vals.get('stage_id'):
            history = self.env['adealer.repair.stage.history']
            for order in self:
                if order.stage_id.id != vals['stage_id']:
                    history.create({
                        'repair_id': order.id,
                        'stage_id': vals['stage_id'],
                    })
        return super().write(vals)
