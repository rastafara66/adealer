# -*- coding: utf-8 -*-
"""«Ввести на підставі» — як в 1С, але з явним переліком дозволеного.

Власник, 10.09.2026: «роби Ввести на підставі», «але враховуй ЩО З ЧОГО можна
зробити, а що не можна», «це б дало однозначний зв'язок у нас в програмі».

🔴 ЧОМУ ТАБЛИЦЕЮ, А НЕ КНОПКАМИ НА ФОРМАХ.

Кнопки вже були: на наряді чотири штуки (`document_chain.py`). Але кнопка
відповідає лише на питання «що я вмію створити звідси», і відповідь на нього
розсипана по формах — щоб дізнатись, що з чого можна, треба обійти всі форми
й прочитати XML. Через це «не можна» ніде не записане взагалі: воно існує як
відсутність кнопки, тобто його не видно й не перевірити.

Тут навпаки: дозволене оголошене одним списком, і саме цей список показує
користувачеві шестерня. Заборонене — це те, чого в списку немає, і його можна
перелічити тестом.

⚠️ Напрямок має значення. З замовлення роблять наряд, з наряда — видаткову,
з видаткової — оплату. Назад не буває: з оплати не заводять наряд, з
видаткової не заводять замовлення. Тому таблиця однобічна.
"""
from odoo import _, api, fields, models
from odoo.exceptions import UserError


#: З ЧОГО -> ЩО МОЖНА. Ключ — модель-джерело, значення — перелік
#: `(код, назва для людини, метод-обробник)`.
#:
#: Обробник живе на моделі-джерелі й повертає створений запис. Зв'язок пише
#: не він, а `action_create`: інакше кожен новий обробник міг би його забути,
#: і документ тихо випав би зі структури підпорядкованості.
ON_BASIS = {
    "sale.order": [
        ("repair_order", "Repair order", "_basis_repair_order"),
        ("invoice", "Invoice", "_basis_invoice"),
    ],
    "repair.order": [
        # Ці три вже вміє `document_chain.py` — не дублюємо логіку, кличемо її.
        ("rakhunok", "Invoice (proforma)", "_basis_rakhunok"),
        ("vydatkova", "Delivery note", "_basis_vydatkova"),
        ("akt", "Act of completed works", "_basis_akt"),
        ("issue_parts", "Issue parts to the workshop", "_basis_issue_parts"),
    ],
    "account.move": [
        ("payment", "Payment", "_basis_payment"),
        ("refund", "Credit note", "_basis_refund"),
    ],
    # 🔴 З платежу в межах цього модуля не роблять НІЧОГО.
    #
    # У 1С на підставі оплати заводять податкову накладну — але вона живе в
    # «Активі», окремому модулі. Дописати її сюди означало б залежність
    # `adealer` від «Актива», а модулі лінійки продаються нарізно і одне від
    # одного не залежать. «Актив» додасть свій рядок у цю таблицю сам.
    "account.payment": [],
    "stock.picking": [],
}


class DocBasisWizard(models.TransientModel):
    """Маленьке вікно вибору: що саме створити на підставі документа."""

    _name = "adealer.doc.basis"
    _description = "Create on the basis of"

    source_model = fields.Char(required=True, readonly=True)
    source_res_id = fields.Integer(required=True, readonly=True)
    source_ref = fields.Char(string="Basis document", readonly=True)
    #: ⚠️ НЕ `required=True` на полі: запис створюється ДО того, як людина
    #: щось обрала, і обов'язковість на рівні бази валила створення вікна
    #: («null value in column "target" violates not-null constraint»).
    #: Обов'язковість — у формі, там вона й потрібна: не дати натиснути
    #: «Створити», нічого не обравши.
    target = fields.Selection(selection="_selection_target", string="Create")

    @api.model
    def _selection_target(self):
        """Лише те, що дозволено ДЛЯ ЦЬОГО документа.

        ⚠️ Перелік береться з контексту, а не з моделі візарда: селекція
        обчислюється до створення запису, і `self.source_model` тут ще порожній.
        """
        model = self.env.context.get("basis_model")
        return [(code, label) for code, label, _m in ON_BASIS.get(model, [])]

    @api.model
    def open_for(self, record):
        allowed = ON_BASIS.get(record._name, [])
        if not allowed:
            # 🔴 Кажемо, ЧОМУ нічого не пропонуємо. Порожнє вікно виглядало б
            # як поломка, а це свідоме «з цього документа не заводять нічого».
            raise UserError(_(
                "Nothing is created on the basis of %(name)s.\n\n"
                "This is deliberate: the chain runs one way — order, then "
                "repair order, then delivery note, then payment.",
                name=self.env["ir.model"]._get(record._name).name or record._name))
        wizard = self.with_context(basis_model=record._name).create({
            "source_model": record._name,
            "source_res_id": record.id,
            "source_ref": record.display_name,
        })
        return {
            "type": "ir.actions.act_window",
            "name": _("Create on the basis of"),
            "res_model": self._name,
            "res_id": wizard.id,
            "view_mode": "form",
            "target": "new",
            "context": dict(self.env.context, basis_model=record._name),
        }

    def action_create(self):
        self.ensure_one()
        source = self.env[self.source_model].browse(self.source_res_id)
        handler = None
        for code, _label, method in ON_BASIS.get(self.source_model, []):
            if code == self.target:
                handler = method
                break
        if not handler or not hasattr(source, handler):
            raise UserError(_("This document cannot be created from that one."))

        created = getattr(source, handler)()
        if not created:
            raise UserError(_("Nothing was created — the basis document is empty."))

        # 🔴 Зв'язок пише ОДНЕ місце, а не кожен обробник. Забутий виклик у
        # новому обробнику означав би документ, якого немає в структурі, —
        # і помітити це можна було б лише очима.
        self.env["adealer.doc.link"].link(source, created, "basis")
        return {
            "type": "ir.actions.act_window",
            "res_model": created._name,
            "res_id": created.id,
            "view_mode": "form",
        }


class SaleOrderBasis(models.Model):
    _inherit = "sale.order"

    def _basis_repair_order(self):
        self.ensure_one()
        return self.env["repair.order"].create({
            "partner_id": self.partner_id.id,
            "source_sale_order_id": self.id,
        })

    def _basis_invoice(self):
        self.ensure_one()
        if not self.invoice_ids:
            self._create_invoices()
        return self.invoice_ids[-1:]


class AccountMoveBasis(models.Model):
    _inherit = "account.move"

    def _basis_payment(self):
        """Оплата на підставі рахунка — на суму, що лишилась несплаченою."""
        self.ensure_one()
        if self.move_type not in ("out_invoice", "out_refund",
                                  "in_invoice", "in_refund"):
            raise UserError(_("A payment is created from an invoice or a bill."))
        journal = self.env["account.journal"].search(
            [("type", "in", ("bank", "cash")),
             ("company_id", "=", self.company_id.id)], limit=1)
        if not journal:
            raise UserError(_("No bank or cash journal is configured."))
        inbound = self.move_type in ("out_invoice", "in_refund")
        return self.env["account.payment"].create({
            "payment_type": "inbound" if inbound else "outbound",
            "partner_type": "customer" if self.move_type.startswith("out") else "supplier",
            "partner_id": self.partner_id.id,
            "amount": abs(self.amount_residual) or abs(self.amount_total),
            "date": fields.Date.context_today(self),
            "journal_id": journal.id,
        })

    def _basis_refund(self):
        self.ensure_one()
        if self.move_type not in ("out_invoice", "in_invoice"):
            raise UserError(_("A credit note is created from an invoice or a bill."))
        return self.env["account.move.reversal"].create({
            "move_ids": [(6, 0, self.ids)],
            "journal_id": self.journal_id.id,
        }).refund_moves() and self.reversal_move_ids[-1:]


class RepairOrderBasis(models.Model):
    _inherit = "repair.order"

    def _basis_rakhunok(self):
        return self._build_chain_move("all", _("Invoice"))

    def _basis_vydatkova(self):
        return self._build_chain_move("goods", _("Delivery note"))

    def _basis_akt(self):
        return self._build_chain_move("services", _("Act"))

    def _basis_issue_parts(self):
        picking = self._issue_parts_picking()
        if not picking:
            raise UserError(_("Order %s has no stock parts to issue.") % self.name)
        return picking
