# -*- coding: utf-8 -*-
"""Сканер штрихкодів у документах: товар — рядком одним скануванням.

Звичайний сканер працює як клавіатура: швидко «набирає» код і Enter. Штатний
модуль Odoo `barcodes` (LGPL, є в Community) ловить такий набір і віддає код
формі через поле `_barcode_scanned` (віджет `barcode_handler`). Далі —
`on_barcode_scanned`: знайти товар за штрихкодом (немає — за артикулом) і
додати рядок; якщо цей товар у документі вже є — кількість +1.

🔴 Такий самий міксин є в «Активі» — на ті самі штатні документи. Модулі один
від одного не залежать, тож у базі, де стоять обидва:
* `on_barcode_scanned` НЕ кличе super(): спрацьовує рівно одна реалізація (та,
  що вище за MRO). Інакше кожен скан додавав би товар двічі. Гачки документів
  у кожного модуля свої (`_adealer_scan_*`), тож реалізація, що спрацювала,
  користується лише своїми;
* поле-віджет кожен модуль додає у форму сам, і їх може стати два — два
  віджети дали б два onchange на ОДИН скан. `_get_view` лишає перше.
"""
from odoo import _, api, models
from odoo.fields import Command


class AdealerBarcodeScan(models.AbstractModel):
    _name = 'adealer.barcode.scan'
    _inherit = ['barcodes.barcode_events_mixin']
    _description = 'Barcode scanning into document lines'

    @api.model
    def _get_view(self, view_id=None, view_type='form', **options):
        arch, view = super()._get_view(view_id, view_type, **options)
        if view_type == 'form':
            for node in arch.xpath("//field[@name='_barcode_scanned']")[1:]:
                node.getparent().remove(node)
        return arch, view

    # --- що задає кожен документ -------------------------------------------

    def _adealer_scan_target(self, product):
        """(поле рядків, поле кількості), куди йде цей товар."""
        raise NotImplementedError

    def _adealer_scan_editable(self):
        """Чи можна ще додавати рядки (документ не проведено й не скасовано)."""
        return True

    def _adealer_scan_product_problem(self, product):
        """Текст, чому товар у цей документ не можна (або None)."""
        return None

    def _adealer_scan_after_new_line(self, line):
        """Рядок створено в onchange документа — onchange самого рядка тут не
        біжать. Документ, чиї рядки рахують ціну в onchange, а не в compute,
        кличе його тут."""

    # --- спільне ------------------------------------------------------------

    def _adealer_scan_warning(self, title, message):
        return {'warning': {'title': title, 'message': message}}

    def _adealer_scan_find_product(self, code):
        """(товар, None) або (None, попередження) — усі причини словами."""
        Product = self.env['product.product']
        found = Product.search([('barcode', '=', code)], limit=2)
        if not found:
            found = Product.search([('default_code', '=', code)], limit=6)
        if not found:
            return None, self._adealer_scan_warning(
                _("Barcode not found"),
                _("No product has the barcode or internal reference \"%(code)s\". "
                  "Why: the code is not filled in on any product, or the product is archived. "
                  "What to do: open the product, fill in its Barcode field and scan again.",
                  code=code))
        if len(found) > 1:
            return None, self._adealer_scan_warning(
                _("Several products match"),
                _("The code \"%(code)s\" belongs to several products: %(names)s. "
                  "What to do: give each of them its own barcode and scan the barcode.",
                  code=code, names=", ".join(found[:5].mapped('display_name'))))
        return found, None

    def on_barcode_scanned(self, barcode):
        # 🔴 Без super() — див. докстрінг модуля: інакше один скан = два рядки.
        self.ensure_one()
        code = (barcode or '').strip()
        if not code:
            return None
        if not self._adealer_scan_editable():
            state = dict(self._fields['state']._description_selection(self.env)).get(self.state)
            return self._adealer_scan_warning(
                _("The document can no longer be changed"),
                _("Status \"%(state)s\": scanned products are not added. "
                  "What to do: scan into a new document, or reset this one to draft first.",
                  state=state or self.state))
        product, warning = self._adealer_scan_find_product(code)
        if warning:
            return warning
        problem = self._adealer_scan_product_problem(product)
        if problem:
            return self._adealer_scan_warning(_("This product cannot be added here"), problem)
        lines_field, qty_field = self._adealer_scan_target(product)
        # Товарний рядок рахунку має display_type «product», замовлення — порожній.
        same = self[lines_field].filtered(
            lambda line: line.product_id == product
            and getattr(line, 'display_type', False) in (False, 'product'))[:1]
        if same:
            same[qty_field] += 1
            return None
        before = self[lines_field]
        self[lines_field] = [Command.create({'product_id': product.id, qty_field: 1})]
        self._adealer_scan_after_new_line(self[lines_field] - before)
        return None


class SaleOrder(models.Model):
    _name = 'sale.order'
    _inherit = ['sale.order', 'adealer.barcode.scan']

    def _adealer_scan_target(self, product):
        return 'order_line', 'product_uom_qty'

    def _adealer_scan_editable(self):
        return self.state in ('draft', 'sent') and not self.locked

    def _adealer_scan_product_problem(self, product):
        if not product.sale_ok:
            return _("\"%(product)s\" is not marked as sellable. "
                     "What to do: open the product and tick \"Sales\".",
                     product=product.display_name)
        return None


class PurchaseOrder(models.Model):
    _name = 'purchase.order'
    _inherit = ['purchase.order', 'adealer.barcode.scan']

    def _adealer_scan_target(self, product):
        return 'order_line', 'product_qty'

    def _adealer_scan_editable(self):
        return self.state in ('draft', 'sent')

    def _adealer_scan_product_problem(self, product):
        if not product.purchase_ok:
            return _("\"%(product)s\" is not marked as purchasable. "
                     "What to do: open the product and tick \"Purchase\".",
                     product=product.display_name)
        return None


class RepairOrder(models.Model):
    _name = 'repair.order'
    _inherit = ['repair.order', 'adealer.barcode.scan']

    def _adealer_scan_target(self, product):
        # Форма наряду показує рядки двома вкладками — роботи й запчастини
        # (`service.py`); писати в ту, де рядок буде видно.
        if product.type == 'service':
            return 'service_line_ids', 'product_uom_qty'
        return 'part_line_ids', 'product_uom_qty'

    def _adealer_scan_editable(self):
        return self.state not in ('done', 'cancel')

    def _adealer_scan_after_new_line(self, line):
        # Ціна, одиниця й податки рядка наряду ставляться в onchange рядка.
        line._onchange_product_id()
