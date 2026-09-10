# -*- coding: utf-8 -*-
"""Документ-підстава і структура підпорядкованості — як в 1С.

🔴 НАВІЩО ОКРЕМА МОДЕЛЬ, а не ще одне поле.

`document_chain.py` уже тримає зв'язок «ввод на підставі», але **окремим полем
на кожну пару**: `account.move.source_repair_order_id`,
`stock.picking.source_repair_order_id`, `repair.order.source_sale_order_id`.
Це працює, доки пар три. Кожна нова пара — нове поле, міграція і ще одна
гілка в коді, який будує ланцюг.

А головне — так не виражається те, заради чого все й почалось: **платіж**.
У 1С оплата закриває борг посиланням `ДокументРасчетовСКонтрагентом`, і на
живій базі замовника воно веде переважно на **наряд-замовлення**
(29 800 рядків із 36 645), а не на видаткову (6 512). Наряд-замовлення там —
основний документ. Поля `account.payment.source_repair_order_id` у нас немає,
тож зіставити нічим, і в списку реалізацій **усі** рядки стоять «Не оплачено»,
хоч у 1С вони оплачені.

Тому зв'язок зберігається парою (модель, запис) з обох боків: одна таблиця
описує будь-яку пару документів і обходиться в ОБИДВА боки. Другий бік
обов'язковий — без нього дерево не побудуєш: від документа треба бачити і
чим він породжений, і що породив він.

⚠️ Типовані поля з `document_chain.py` НЕ прибираємо. Вони вже в базах
покупців, на них стоять `One2many` і кнопки. Дерево читає обидва джерела.
"""
from odoo import _, api, fields, models

#: Пари «модель → поле, що вказує на документ-підставу», які існували до цієї
#: моделі. Дерево має показувати й старі дані, інакше воно збреше порожнечею
#: там, де зв'язок насправді є.
LEGACY_PARENTS = [
    ("account.move", "source_repair_order_id", "repair.order"),
    ("stock.picking", "source_repair_order_id", "repair.order"),
    ("repair.order", "source_sale_order_id", "sale.order"),
]


class DocLink(models.Model):
    """Одне ребро графа документів: підстава -> похідний."""

    _name = "adealer.doc.link"
    _description = "Document basis link"
    _rec_name = "child_ref"

    parent_model = fields.Char(required=True, index=True)
    parent_res_id = fields.Many2oneReference(
        model_field="parent_model", required=True, index=True,
        string="Basis document")
    child_model = fields.Char(required=True, index=True)
    child_res_id = fields.Many2oneReference(
        model_field="child_model", required=True, index=True,
        string="Derived document")

    #: Чим саме зчеплені — 1С розрізняє ці випадки, і зливати їх не можна:
    #: «створено на підставі» і «цим платежем закрито» — різні твердження.
    kind = fields.Selection(
        [("basis", "Entered on the basis of"),
         ("settlement", "Settles this document"),
         ("deal", "Belongs to the deal")],
        default="basis", required=True, index=True)

    parent_ref = fields.Char(compute="_compute_refs", string="Basis")
    child_ref = fields.Char(compute="_compute_refs", string="Derived")

    _sql_constraints = [
        ("doc_link_unique",
         "unique(parent_model, parent_res_id, child_model, child_res_id, kind)",
         "This link already exists."),
    ]

    @api.depends("parent_model", "parent_res_id", "child_model", "child_res_id")
    def _compute_refs(self):
        for link in self:
            link.parent_ref = link._display(link.parent_model, link.parent_res_id)
            link.child_ref = link._display(link.child_model, link.child_res_id)

    def _display(self, model, res_id):
        """Назва документа — або чесне «немає», якщо запис уже видалено.

        ⚠️ Порожній рядок тут читався б як «зв'язку немає», а це не так:
        зв'язок є, зник документ. Мовчазна порожнеча — окремий клас помилок
        (конвенції §7), тому вона тут проговорюється словом.
        """
        if not model or not res_id or model not in self.env:
            return _("(unknown document)")
        record = self.env[model].browse(res_id).exists()
        if not record:
            return _("(deleted document)")
        return record.display_name

    # ------------------------------------------------------------------
    @api.model
    def link(self, parent, child, kind="basis"):
        """Зчепити два записи. Повторний виклик нічого не дублює.

        Повертає ребро — і те, що вже було, і щойно створене, щоб виклик
        можна було робити з імпорту скільки завгодно разів.
        """
        if not parent or not child:
            return self.browse()
        parent.ensure_one()
        child.ensure_one()
        values = {
            "parent_model": parent._name, "parent_res_id": parent.id,
            "child_model": child._name, "child_res_id": child.id,
            "kind": kind,
        }
        found = self.search([(key, "=", value) for key, value in values.items()], limit=1)
        return found or self.create(values)

    @api.model
    def parents_of(self, record):
        """Чим породжений цей документ — з нової таблиці і зі старих полів."""
        out = []
        for link in self.search([("child_model", "=", record._name),
                                 ("child_res_id", "=", record.id)]):
            target = self.env[link.parent_model].browse(link.parent_res_id).exists()
            if target:
                out.append((target, link.kind))
        for model, field, _target_model in LEGACY_PARENTS:
            if record._name != model or field not in record._fields:
                continue
            parent = record[field]
            if parent:
                out.append((parent, "basis"))
        return out

    @api.model
    def children_of(self, record):
        """Що породжено цим документом — теж з обох джерел."""
        out = []
        for link in self.search([("parent_model", "=", record._name),
                                 ("parent_res_id", "=", record.id)]):
            target = self.env[link.child_model].browse(link.child_res_id).exists()
            if target:
                out.append((target, link.kind))
        for model, field, target_model in LEGACY_PARENTS:
            if record._name != target_model or model not in self.env:
                continue
            found = self.env[model].search([(field, "=", record.id)])
            out += [(rec, "basis") for rec in found]
        return out
