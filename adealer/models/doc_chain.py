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


class DocChain(models.TransientModel):
    _name = "adealer.doc.chain"
    _description = "Document subordination structure"

    origin_model = fields.Char(required=True)
    origin_res_id = fields.Integer(required=True)
    origin_ref = fields.Char(string="Document", readonly=True)
    line_ids = fields.One2many("adealer.doc.chain.line", "chain_id", readonly=True)

    @api.model
    def open_for(self, record):
        """Зібрати ланцюг навколо запису і відкрити вікно."""
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
            "target": "new",
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
            for parent, _kind in parents:
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
                "name": (" " * 4 * level) + ("└ " if level else "")
                        + node.display_name,
                "doc_model": node._name,
                "doc_res_id": node.id,
                "model_label": self.env["ir.model"]._get(node._name).name or node._name,
                "kind": kind,
                "is_current": key == (record._name, record.id),
            }))
            for child, child_kind in links.children_of(node):
                walk(child, level + 1, child_kind)

        for root in self._roots(record):
            walk(root, 0, "basis")
        self.line_ids = rows


class DocChainLine(models.TransientModel):
    _name = "adealer.doc.chain.line"
    _description = "Document structure line"
    _order = "id"

    chain_id = fields.Many2one("adealer.doc.chain", required=True, ondelete="cascade")
    name = fields.Char(string="Document", readonly=True)
    level = fields.Integer(readonly=True)
    model_label = fields.Char(string="Type", readonly=True)
    kind = fields.Selection(
        [("basis", "Entered on the basis of"),
         ("settlement", "Settles this document"),
         ("deal", "Belongs to the deal")], readonly=True)
    doc_model = fields.Char(readonly=True)
    doc_res_id = fields.Integer(readonly=True)
    is_current = fields.Boolean(readonly=True)

    def action_open(self):
        """Відкрити документ рядка — інакше дерево лише показує, а не веде."""
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "res_model": self.doc_model,
            "res_id": self.doc_res_id,
            "view_mode": "form",
        }
