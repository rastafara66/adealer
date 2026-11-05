# -*- coding: utf-8 -*-
"""В'юхи модуля згадують лише ті стани документа, які є в ЦІЙ серії Odoo.

Набір станів у серіях різний: в Odoo 20 у наряду (repair.order) немає «Under Repair» — наряд у роботі
там «Confirmed». Умова в'юхи зі станом, якого немає, помилки не дає ніде: підсвітка просто ніколи не
спрацьовує, фільтр нічого не знаходить. Тест читає умови всіх в'юх модуля (атрибути й домени) і звіряє
кожне значення стану з вибором поля моделі цієї в'юхи.
"""
import re

from lxml import etree

from odoo.tests import TransactionCase, tagged

#: `state == 'x'`, `state != 'x'` (не `move_id.state`, не `parts_state`)
CMP = re.compile(r"(?<![\w.])state\s*[!=]=\s*['\"](\w+)['\"]")
#: `state in ('x', 'y')`, `state not in [...]`
IN = re.compile(r"(?<![\w.])state\s+(?:not\s+)?in\s*[(\[]([^)\]]*)[)\]]")
#: домен: `('state', '=', 'x')`, `('state', 'in', ('x', 'y'))`
DOM_CMP = re.compile(r"['\"]state['\"]\s*,\s*['\"](?:=|!=)['\"]\s*,\s*['\"](\w+)['\"]")
DOM_IN = re.compile(r"['\"]state['\"]\s*,\s*['\"](?:not in|in)['\"]\s*,\s*[(\[]([^)\]]*)[)\]]")
WORD = re.compile(r"['\"](\w+)['\"]")


def states_named(text):
    found = set(CMP.findall(text)) | set(DOM_CMP.findall(text))
    for group in IN.findall(text) + DOM_IN.findall(text):
        found |= set(WORD.findall(group))
    return found


@tagged('post_install', '-at_install')
class TestViewStatesExistInThisSeries(TransactionCase):

    def test_views_name_only_states_of_this_series(self):
        views = self.env['ir.ui.view'].browse(self.env['ir.model.data'].search([
            ('module', '=', 'adealer'), ('model', '=', 'ir.ui.view')]).mapped('res_id')).exists()
        self.assertTrue(views)
        missing = []
        for view in views:
            model = self.env[view.model] if view.model and view.model in self.env else None
            field = model._fields.get('state') if model is not None else None
            if field is None or field.type != 'selection':
                continue
            known = {key for key, _label in field._description_selection(self.env)}
            for el in etree.fromstring(view.arch_db.encode()).iter():
                # Усередині вкладеної в'юхи поля (рядки документа) `state` — це стан ІНШОЇ моделі.
                if not isinstance(el.tag, str) or any(a.tag == 'field' for a in el.iterancestors()):
                    continue
                values = list(el.attrib.items())
                if el.tag == 'attribute' and el.text:      # успадкування: <attribute name="invisible">…</attribute>
                    values.append((el.get('name'), el.text))
                for attr, value in values:
                    for state in states_named(value) - known:
                        missing.append('%s (%s): %s="%s" — стану «%s» у %s немає'
                                       % (view.xml_id or view.name, view.model, attr, value, state, view.model))
        self.assertFalse(missing, '\n'.join(missing))
