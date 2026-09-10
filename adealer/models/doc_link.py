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
#: 🔴 РІДНІ ЗВ'ЯЗКИ ODOO — щоб структура працювала БЕЗ 1С.
#:
#: Власник, 10.09.2026: «коли зв'язку з 1С не буде і всі документи будуть
#: заводитися в Odoo, треба щоб зв'язок будувався правильно».
#:
#: Тому таблиця `adealer.doc.link` — не єдине джерело, а лише те, куди
#: складають ПРИВЕЗЕНЕ з 1С. Те, що Odoo знає сам, читаємо з нього напряму:
#: оплата зчеплена з рахунком звіркою проводок, рахунок із замовленням —
#: штатним полем. Дублювати це в свою таблицю означало б завести другий
#: примірник правди, який мовчки розійдеться з першим.
#:
#: (модель-батько, поле з дочірніми записами, вид зв'язку)
NATIVE_CHILDREN = [
    ("sale.order", "invoice_ids", "basis"),
    ("sale.order", "picking_ids", "basis"),
    # Оплату з рахунком зв'язує сама звірка проводок — це і є «оплачено».
    ("account.move", "matched_payment_ids", "settlement"),
]

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

    #: 🔴 Момент документа-нащадка — з ГОДИНОЮ, бо порядок читають за часом.
    #:
    #: Власник: «треба на дату і час дивитися, що іде першим». Штатні поля
    #: Odoo часу не мають: `invoice_date` і `account.payment.date` — це Date.
    #: Тому момент тримає сам зв'язок: при перенесенні з 1С його беруть
    #: звідти, при створенні документа в нас — із моменту створення.
    #:
    #: ⚠️ Поле НЕ називається «час 1С» навмисно. Власник, 10.09.2026: «той
    #: зв'язок, що ми взяли з 1С, повинен повністю вкладатися в нашу логіку
    #: і працювати незалежно від імпорту». Щойно десь з'явиться «це поле для
    #: імпортованого», логіка розділиться надвоє — і половина без 1С
    #: перестане працювати.
    child_time = fields.Datetime(string="Document moment")

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
    def link(self, parent, child, kind="basis", when=None):
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
        if found:
            # Момент міг приїхати пізніше за саме ребро — дописуємо, але вже
            # відомий не перетираємо порожнім.
            if when and not found.child_time:
                found.child_time = when
            return found
        # Момент не переданий -> документ заводять у нас: беремо його власну
        # дату, а як і її немає — теперішній момент. Порожнє поле зробило б
        # рядок непорядкованим, тобто структура мовчки поставила б його
        # першим.
        return self.create(dict(values, child_time=when or self._moment_of(child)))

    @api.model
    def _moment_of(self, record):
        """Момент документа з його ж полів — коли зв'язок роблять не з 1С."""
        for name in ("create_date", "date_order", "invoice_date", "date"):
            if name in record._fields and record[name]:
                return record[name]
        return fields.Datetime.now()

    @api.model
    def parents_of(self, record):
        """Чим породжений цей документ — з нової таблиці і зі старих полів."""
        out = []
        for link in self.search([("child_model", "=", record._name),
                                 ("child_res_id", "=", record.id)]):
            target = self.env[link.parent_model].browse(link.parent_res_id).exists()
            if target:
                out.append((target, link.kind, link.child_time))
        for model, field, _target_model in LEGACY_PARENTS:
            if record._name != model or field not in record._fields:
                continue
            parent = record[field]
            if parent:
                out.append((parent, "basis", False))
        for model, field, kind in NATIVE_CHILDREN:
            if model not in self.env or field not in self.env[model]._fields:
                continue
            comodel = self.env[model]._fields[field].comodel_name
            if comodel != record._name:
                continue
            for parent in self.env[model].search([(field, "in", record.id)]):
                out.append((parent, kind, False))
        return out

    @api.model
    def children_of(self, record):
        """Що породжено цим документом — теж з обох джерел.

        🔴 Платіж, що належить угоді (`deal`) і водночас закриває конкретний
        документ (`settlement`), показується ПІД тим, що він закрив, а не
        поряд із ним. Інакше в структурі оплата стоїть врівень із нарядом,
        якого вона стосується, і ланцюг читається задом наперед.
        """
        out = []
        for link in self.search([("parent_model", "=", record._name),
                                 ("parent_res_id", "=", record.id)]):
            target = self.env[link.child_model].browse(link.child_res_id).exists()
            if not target:
                continue
            if link.kind == "deal" and self.search_count([
                    ("child_model", "=", link.child_model),
                    ("child_res_id", "=", link.child_res_id),
                    ("kind", "in", ("settlement", "basis"))]):
                continue
            out.append((target, link.kind, link.child_time))
        for model, field, target_model in LEGACY_PARENTS:
            if record._name != target_model or model not in self.env:
                continue
            found = self.env[model].search([(field, "=", record.id)])
            out += [(rec, "basis", False) for rec in found]
        for model, field, kind in NATIVE_CHILDREN:
            if record._name != model or field not in record._fields:
                continue
            out += [(rec, kind, False) for rec in record[field]]
        return out
