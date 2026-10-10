# -*- coding: utf-8 -*-
"""Структура підпорядкованості мусить працювати БЕЗ 1С.

Власник, 10.09.2026: «той зв'язок, що ми взяли з 1С, повинен повністю
вкладатися в нашу логіку програми і працювати незалежно від імпорту з 1С».

Тому всі тести тут будують ланцюг **самими засобами Odoo** — жодного рядка,
привезеного імпортом. Якщо колись структура почне залежати від імпорту, ці
тести стануть червоними, а не «просто порожніми».
"""
from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestDocChainWithoutImport(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Link = cls.env["adealer.doc.link"]
        cls.Chain = cls.env["adealer.doc.chain"]
        cls.Move = cls.env["account.move"]

    def _move(self, ref):
        return self.Move.create({"move_type": "entry", "ref": ref})

    # ------------------------------------------------------------------
    def test_link_fills_the_moment_without_any_import(self):
        """Момент проставляється сам, інакше рядок не має чим упорядкуватись.

        Імпорт з 1С передає момент явно. Коли документ заводять у нас, його
        не передає ніхто — і порожнє поле поставило б рядок першим незалежно
        від того, коли документ насправді з'явився.
        """
        parent, child = self._move("A"), self._move("B")
        link = self.Link.link(parent, child, "basis")
        self.assertTrue(
            link.child_time,
            "зв'язок без моменту: структура не знатиме, що йшло першим")

    def test_the_chain_is_built_from_odoo_data_alone(self):
        first, second, third = self._move("1"), self._move("2"), self._move("3")
        self.Link.link(first, second, "basis")
        self.Link.link(second, third, "settlement")

        chain = self.Chain.browse(self.Chain.open_for(second)["res_id"])
        docs = [line.doc_ref for line in chain.line_ids]
        self.assertEqual(
            docs, [first, second, third],
            "ланцюг має йти від кореня вниз, а не від документа, з якого відкрили")
        self.assertEqual([line.level for line in chain.line_ids], [0, 1, 2])

    def test_rows_are_ordered_by_the_moment(self):
        """«Зазвичай спочатку наряд іде, а потім оплата» — порядок за часом."""
        root = self._move("root")
        later, earlier = self._move("later"), self._move("earlier")
        self.Link.link(root, later, "basis").child_time = "2026-08-20 23:50:00"
        self.Link.link(root, earlier, "basis").child_time = "2026-08-20 13:03:00"

        chain = self.Chain.browse(self.Chain.open_for(root)["res_id"])
        refs = [line.doc_ref.ref for line in chain.line_ids]
        self.assertEqual(
            refs, ["root", "earlier", "later"],
            "документи одного дня впорядковуються ГОДИНОЮ, не порядком запису")

    def test_a_cycle_does_not_hang_the_walk(self):
        """У даних замовника платіжка посилається сама на себе.

        Наївний обхід на цьому не падає — він зависає, а це гірше за помилку.
        """
        a, b, c = self._move("a"), self._move("b"), self._move("c")
        self.Link.link(a, b, "basis")
        self.Link.link(b, c, "basis")
        self.Link.link(c, a, "basis")

        chain = self.Chain.browse(self.Chain.open_for(b)["res_id"])
        self.assertEqual(len(chain.line_ids), 3,
                         "у циклі кожен документ показується рівно один раз")

    def test_a_deleted_document_is_named_out_loud(self):
        """Порожній рядок читався б як «зв'язку немає» — а зв'язок є."""
        parent, child = self._move("keep"), self._move("gone")
        link = self.Link.link(parent, child, "basis")
        child.unlink()
        self.assertTrue(link.child_ref, "зниклий документ мусить бути названий словом")


@tagged("post_install", "-at_install")
class TestNativeSourcesStillExist(TransactionCase):
    """Поля, з яких структура читає РІДНІ зв'язки Odoo, мають існувати.

    🔴 Це та сама «мовчазна порожнеча»: якщо поле перейменують у наступній
    серії Odoo, наш код просто пропустить джерело, дерево здрібніє, і жоден
    інший тест цього не помітить.
    """

    def test_declared_native_fields_are_real(self):
        from ..models.doc_link import NATIVE_CHILDREN

        missing = []
        for model, field, _kind in NATIVE_CHILDREN:
            if model not in self.env:
                missing.append("немає моделі %s" % model)
            elif field not in self.env[model]._fields:
                missing.append("%s.%s" % (model, field))
        self.assertFalse(
            missing,
            "структура читає неіснуючі поля — рідні зв'язки Odoo мовчки "
            "випадуть з дерева: %s" % ", ".join(missing))


@tagged("post_install", "-at_install")
class TestTheEntryPointExists(TransactionCase):
    """Дію відкриття структури має бути ВИДНО в шестерні «Дії».

    Модель і вигляд можуть бути бездоганні, а пункт меню — не прив'язаний;
    тоді користувач просто не має чим відкрити структуру (конвенції §7).
    """

    def test_the_cog_offers_the_structure_on_every_document(self):
        expected = {"account.move", "account.payment", "repair.order",
                    "sale.order", "stock.picking"}
        actions = self.env["ir.actions.server"].search(
            [("code", "like", "adealer.doc.chain")])
        bound = {action.binding_model_id.model for action in actions}
        self.assertFalse(
            expected - bound,
            "у шестерні немає структури для: %s" % ", ".join(sorted(expected - bound)))


@tagged("post_install", "-at_install")
class TestWhatCanBeCreatedFromWhat(TransactionCase):
    """«Враховуй ЩО З ЧОГО можна зробити, а що не можна» (власник, 10.09.2026).

    Дозволене оголошене таблицею `ON_BASIS`, і саме тому його можна
    перевірити. Доки воно було розсипом кнопок по формах, «не можна» ніде не
    існувало як твердження — лише як відсутність кнопки.
    """

    def test_every_declared_handler_really_exists(self):
        """Оголошений обробник, якого немає, впаде лише під пальцем користувача."""
        from ..models.doc_basis import ON_BASIS

        broken = []
        for model, targets in ON_BASIS.items():
            if model not in self.env:
                broken.append("немає моделі %s" % model)
                continue
            for code, _label, method in targets:
                if not hasattr(self.env[model], method):
                    broken.append("%s -> %s: немає %s()" % (model, code, method))
        self.assertFalse(broken, "; ".join(broken))

    def test_the_chain_runs_one_way_only(self):
        """Назад не заводять: з оплати не роблять наряд, з наряду — замовлення."""
        from ..models.doc_basis import ON_BASIS

        forbidden = [
            ("account.payment", "repair_order"),
            ("account.payment", "invoice"),
            ("repair.order", "sale_order"),
            ("account.move", "repair_order"),
        ]
        for model, code in forbidden:
            codes = [row[0] for row in ON_BASIS.get(model, [])]
            self.assertNotIn(
                code, codes,
                "з %s не можна заводити %s — ланцюг іде в один бік" % (model, code))

    def test_a_document_with_no_targets_says_why(self):
        """Порожнє вікно читалося б як поломка. Має бути сказано словом."""
        from odoo.exceptions import UserError

        payment = self.env["account.payment"].create({
            "payment_type": "inbound", "partner_type": "customer",
            "amount": 1.0,
        })
        with self.assertRaises(UserError):
            self.env["adealer.doc.basis"].open_for(payment)

    def test_creating_on_the_basis_writes_the_link(self):
        """Головна вимога: звʼязок зʼявляється БЕЗ жодного імпорту з 1С."""
        partner = self.env["res.partner"].create({"name": "Chain test"})
        order = self.env["sale.order"].create({"partner_id": partner.id})

        wizard = self.env["adealer.doc.basis"].with_context(
            basis_model="sale.order").create({
                "source_model": "sale.order", "source_res_id": order.id,
                "target": "repair_order"})
        action = wizard.action_create()

        created = self.env[action["res_model"]].browse(action["res_id"])
        link = self.env["adealer.doc.link"].search([
            ("parent_model", "=", "sale.order"), ("parent_res_id", "=", order.id),
            ("child_model", "=", created._name), ("child_res_id", "=", created.id)])
        self.assertTrue(link, "документ, заведений на підставі, не потрапив у структуру")


@tagged("post_install", "-at_install")
class TestGitPanelTellsTheTruthUpfront(TransactionCase):
    """Кнопка «Update from GitHub» не має існувати там, де git немає.

    10.09.2026 на ford.aktiv.in.ua натискання давало «git недоступний на
    сервері: No such file or directory». Це не поломка модуля — офіційний
    образ Odoo просто не містить git. Але для користувача воно виглядає
    поломкою, бо кнопка стоїть і обіцяє дію.
    """

    def test_missing_git_is_explained_before_the_click(self):
        from unittest.mock import patch as mock_patch

        with mock_patch("subprocess.run", side_effect=OSError("No such file: 'git'")):
            ready, reason = self.env["adealer.app.update"].git_status()

        self.assertFalse(ready)
        self.assertTrue(reason, "мовчазне «не можна» читається як поломка")
        self.assertIn(
            "App Store", reason,
            "сказати «не можна» мало — треба сказати, ЯК тоді оновитись")

    def test_a_working_checkout_offers_the_button(self):
        ready, reason = self.env["adealer.app.update"].git_status()
        if not ready:
            self.skipTest("на цій машині немає git або тека не є git-клоном: %s" % reason)
        self.assertFalse(reason, "коли можна — пояснювати нічого не треба")


@tagged("post_install", "-at_install")
class TestInstalledMeansWorking(TransactionCase):
    """«Встановив — і ВСЕ працює» (власник, 10.09.2026).

    🔴 Найдорожча помилка цього класу: `base.group_user` має в `ir_model_data`
    прапорець `noupdate=True`. Odoo застосовує такі записи при ПЕРШОМУ
    встановленні й мовчки пропускає при ОНОВЛЕННІ. Тому інсталл у чисту базу
    (§4) був зелений, а кожна вже наявна база лишалась без доступу — і
    користувач бачив «Помилка доступу» на кожному документі.

    Цей тест іде саме тією базою, у якій його запустили, тож ловить обидва
    випадки: і install, і upgrade.
    """

    def test_every_employee_gets_the_daily_level(self):
        ours = self.env.ref("adealer.group_adealer_user")
        employee = self.env.ref("base.group_user")
        self.assertIn(
            ours, employee.implied_ids,
            "внутрішній користувач не отримує рівень «Користувач»: меню є, "
            "а жоден документ не відкривається")

    def test_an_administrator_gets_the_manager_level(self):
        """Ставить додаток адміністратор, а не бухгалтер."""
        ours = self.env.ref("adealer.group_adealer_manager")
        admins = self.env.ref("base.group_system")
        self.assertIn(
            ours, admins.implied_ids,
            "адміністратор не отримує рівень «Керівник» — нікому налаштувати "
            "додаток одразу після встановлення")

    def test_a_plain_employee_can_actually_read_a_document(self):
        """Груп мало — перевіряємо саме читання, під НЕ-адміністратором."""
        user = self.env["res.users"].create({
            "name": "Access probe", "login": "adealer_access_probe",
            "group_ids": [(6, 0, [self.env.ref("base.group_user").id])],
        })
        try:
            self.env["repair.order"].with_user(user).search([], limit=1)
            self.env["dealer.car"].with_user(user).search([], limit=1)
        except Exception as exc:                            # noqa: BLE001
            self.fail("звичайний співробітник не може читати документи "
                      "одразу після встановлення: %s" % exc)
