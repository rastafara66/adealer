# -*- coding: utf-8 -*-
"""«Структура підпорядкованості документа» — те саме вікно, що в 1С.

Показує ВЕСЬ ланцюг, а не сусідів: від кореня (документа, який нічим не
породжений) вниз до останнього похідного. Саме так це виглядає в 1С, і саме
так на нього дивиться бухгалтер: замовлення -> реалізація -> платіжка ->
податкова накладна.

⚠️ Обхід МУСИТЬ мати захист від циклу. Це не теоретична обережність: на живій
базі замовника `ДокументРасчетовСКонтрагентом` двічі вказує на сам платіж
(`_document304` на `_document304`). Наївний обхід там не падає — він зависає,
що гірше за помилку.
"""
from odoo import _, api, fields, models


#: Поля дати в порядку спадання довіри. Різні документи звуть її по-різному,
#: а ланцюг мусить шикуватися за часом незалежно від моделі.
_DATE_FIELDS = ("invoice_date", "date", "date_order", "schedule_date", "create_date")


def _doc_date(record):
    """Дата документа з Odoo — запасний варіант, коли моменту 1С немає.

    ⚠️ Тут лише ДАТА: `invoice_date` і `account.payment.date` — поля типу
    Date. Два документи одного дня цим не впорядкуються, і це не недогляд
    сортування, а брак даних. Справжній порядок дає `child_time` зі зв'язку.
    """
    for name in _DATE_FIELDS:
        if name in record._fields:
            value = record[name]
            if value:
                return str(value)[:10]
    return "0000-00-00"


class DocChain(models.TransientModel):
    _name = "adealer.doc.chain"
    _description = "Document subordination structure"

    origin_model = fields.Char(required=True)
    origin_res_id = fields.Integer(required=True)
    origin_ref = fields.Char(string="Document", readonly=True)
    line_ids = fields.One2many("adealer.doc.chain.line", "chain_id", readonly=True)

    @api.model
    def open_for(self, record):
        """Зібрати ланцюг навколо запису і відкрити вікно.

        ⚠️ `target` — САМЕ `current`, не діалог. Кожен рядок структури
        відкривається кліком, а перехід з модального вікна лишає документ
        під сірою заслінкою. Повернутись до структури дають хлібні крихти.
        """
        chain = self.create({
            "origin_model": record._name,
            "origin_res_id": record.id,
            "origin_ref": record.display_name,
        })
        chain._build(record)
        return {
            "type": "ir.actions.act_window",
            "name": _("Document structure"),
            "res_model": self._name,
            "res_id": chain.id,
            "view_mode": "form",
            "target": "current",
        }

    # ------------------------------------------------------------------
    def _roots(self, record):
        """Догори до документів, які вже нічим не породжені."""
        links = self.env["adealer.doc.link"]
        seen, frontier, roots = {(record._name, record.id)}, [record], []
        while frontier:
            current = frontier.pop()
            parents = links.parents_of(current)
            if not parents:
                roots.append(current)
                continue
            for parent, _kind, _when in parents:
                key = (parent._name, parent.id)
                if key in seen:      # цикл: далі не йдемо, але й не губимо гілку
                    roots.append(current)
                    continue
                seen.add(key)
                frontier.append(parent)
        return roots or [record]

    def _build(self, record):
        links = self.env["adealer.doc.link"]
        rows, seen = [], set()

        def walk(node, level, kind):
            key = (node._name, node.id)
            if key in seen:
                return
            seen.add(key)
            rows.append((0, 0, {
                "level": level,
                # 🔴 Відступ — НЕРОЗРИВНИМИ пробілами. Звичайні HTML
                # схлопує в один, і дерево злипається в стовпчик без жодної
                # помилки: рядки на місці, ієрархії немає.
                "prefix": (" " * 4 * level) + ("└ " if level else ""),
                "doc_ref": "%s,%s" % (node._name, node.id),
                "model_label": self.env["ir.model"]._get(node._name).name or node._name,
                "kind": kind,
                "is_current": key == (record._name, record.id),
            }))
            # 🔴 ПОРЯДОК — ЗА ДАТОЮ ДОКУМЕНТА, а не за порядком запису в базі.
            # Власник: «зазвичай спочатку наряд іде, а потім оплата». Ланцюг
            # читають як історію, і рядки не в тому порядку читаються як
            # помилка даних, хоч дані правильні.
            for child, child_kind, when in sorted(
                    links.children_of(node),
                    key=lambda row: str(row[2] or "") or _doc_date(row[0])):
                walk(child, level + 1, child_kind)

        for root in self._roots(record):
            walk(root, 0, "basis")
        self.line_ids = rows


class DocChainLine(models.TransientModel):
    _name = "adealer.doc.chain.line"
    _description = "Document structure line"
    _order = "id"

    chain_id = fields.Many2one("adealer.doc.chain", required=True, ondelete="cascade")

    #: Відступ і гілка дерева — ОКРЕМОЮ колонкою від назви. Якщо домалювати
    #: пробіли в саму назву, посилання поведе туди ж, але виглядатиме зламаним.
    prefix = fields.Char(readonly=True)
    level = fields.Integer(readonly=True)

    #: 🔴 Саме `Reference`, а не пара Char+Integer із кнопкою «Відкрити» поруч.
    #: У readonly Odoo малює його компонентом `Many2One`, а той віддає
    #: `<a class="o_form_uri">` і відкриває запис ПО КЛІКУ (звірено в
    #: `web/static/src/views/fields/many2one/many2one.xml`). Тобто клікається
    #: сама назва документа, а не кнопка збоку.
    doc_ref = fields.Reference(
        selection="_selection_doc_model", string="Document", readonly=True)

    model_label = fields.Char(string="Type", readonly=True)
    kind = fields.Selection(
        [("basis", "Entered on the basis of"),
         ("settlement", "Settles this document"),
         ("deal", "Belongs to the deal")], readonly=True)
    is_current = fields.Boolean(readonly=True)

    @api.model
    def _selection_doc_model(self):
        """Будь-яка модель: ланцюг перетинає межі модулів.

        Жорсткий перелік означав би, що податкова накладна з «Актива» чи
        платіжка з Bank Sync у структурі просто не відкриється — і мовчки.
        """
        return [(model.model, model.name)
                for model in self.env["ir.model"].sudo().search([])]
