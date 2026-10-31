# -*- coding: utf-8 -*-
"""Код ЄДРПОУ / РНОКПП і ІПН платника ПДВ контрагента — одне правило для Odoo 18, 19 і 20.

🔴 ЦЕЙ ФАЙЛ ЛЕЖИТЬ БАЙТ У БАЙТ У ЯДРІ КОЖНОГО ПРОДУКТУ («Актив» — `l10n_ua_aktiv_base`, 3A-dealer — `adealer`,
Data Exchange — `atm`) і в кожній серії: модулі продаються окремо й один від одного не залежать, а правило в них
мусить бути одне. Змінюєте тут — змінюйте всюди; копії звіряє гейт 3A `tools/store/check_ua_tax_ids.py`.

У контрагента два різні номери — так у Податковому кодексі (п. 63.6: податковий номер — код ЄДРПОУ юрособи або
РНОКПП фізособи; п. 201.1 «й»: окремо індивідуальний податковий номер платника ПДВ) і так у 1С («Код по ЄДРПОУ»
і «ИНН»). Поле, де лежить кожен, залежить від серії Odoo, і вирішує НАЯВНІСТЬ поля, а не номер серії:

    номер                  Odoo 18/19           Odoo 20
    код ЄДРПОУ / РНОКПП    company_registry     vat
    ІПН платника ПДВ       vat                  additional_identifiers["UA_VAT"]

Odoo 20 прибрала `company_registry`, рахує «компанію» з `vat` і для України називає `vat` податковим номером
(`UA_TIN`, категорія TIN), а другорядні номери тримає «додатковими ідентифікаторами» — так зроблено й для
Угорщини (`HU_TIN` у `vat`, ПДВ-номер `HU_VAT` — додатковим). Рішення власника 31.10.2026, обґрунтування й цифри —
3A `docs/partner-tax-ids.md`.

Читати номери — `_l10n_ua_tax_codes()`, писати — значеннями `_l10n_ua_tax_vals()`; полів напряму не чіпати.
"""
import re

from odoo import api, models
from odoo.tools.translate import LazyTranslate

_lt = LazyTranslate(__name__)

#: Ключ ІПН серед додаткових ідентифікаторів Odoo 20 (назва — за звичаєм Odoo: країна_категорія).
UA_VAT = "UA_VAT"


def ua_digits(value):
    """Лише цифри: «UA 1234-5678» → «12345678». `[0-9]`, а не `\\d`: Python рахує цифрами й інші письмена."""
    return re.sub(r"[^0-9]", "", value or "")


def ua_check_ipn(value):
    """Перевірка ІПН для Odoo 20 (`validation_function`): 12 цифр у юрособи, 10 у ФОП (це його РНОКПП)."""
    number = ua_digits(value)
    if len(number) not in (10, 12) or re.sub(r"[\s-]", "", value or "").upper().removeprefix("UA") != number:
        raise ValueError(value)
    return number


class ResPartner(models.Model):
    _inherit = "res.partner"

    # ------------------------------------------------------------------ читання й запис
    def _l10n_ua_home(self):
        """Чи діє українське правило: країна контрагента — Україна; без країни — країна організації (у
        перенесених з 1С карток країни найчастіше немає). Країни немає ні там, ні там — теж так: інакше в
        організації, якій забули вказати країну, ПН, Д1 і 4ДФ мовчки лишилися б без номерів."""
        self.ensure_one()
        country = self.country_id or (self.company_id or self.env.company).country_id
        return not country or country.code == "UA"

    def _l10n_ua_tax_codes(self):
        """(код ЄДРПОУ/РНОКПП, ІПН платника ПДВ) комерційного контрагента — лише цифри, «» коли номера немає.

        Іноземному контрагенту — («», «»): його `vat` — номер іншої країни. Порожній запис (документ без
        контрагента) — теж («», «»).

        Терпить і дані, записані до 31.10.2026, коли `vat` усюди вважали ІПН, а 3A-dealer тримав код у своєму
        полі `edrpou`: 12 цифр у `vat` Odoo 20 — це ІПН; у Odoo 18/19 без коду 8 чи 10 цифр з `vat` стають і кодом
        (8 — код, покладений не туди; 10 — ФОП-платник, у якого ІПН і є РНОКПП). ІПН повертається таким, як
        записаний, навіть коли це не ІПН: звіт має сказати «у полі ІПН — код ЄДРПОУ», а не «ІПН немає».
        """
        if not self:
            return "", ""
        self.ensure_one()
        partner = self.commercial_partner_id
        if not partner._l10n_ua_home():
            return "", ""
        legacy = ua_digits(partner["edrpou"]) if "edrpou" in partner._fields else ""
        legacy = legacy if len(legacy) != 12 else ""
        if "company_registry" in partner._fields:  # Odoo 18/19
            ipn = ua_digits(partner.vat)
            code = ua_digits(partner.company_registry) or legacy or (ipn if len(ipn) in (8, 10) else "")
            return code, ipn
        code = ua_digits(partner.vat)  # Odoo 20
        ipn = ua_digits((partner.additional_identifiers or {}).get(UA_VAT))
        if len(code) == 12:
            code, ipn = "", ipn or code
        return code or legacy, ipn

    @api.model
    def _l10n_ua_tax_vals(self, code=None, ipn=None, identifiers=None):
        """Значення для `create`/`write`: куди в цій серії лягають код і ІПН.

        `None` — не чіпати, «» — очистити. `identifiers` — нинішні додаткові ідентифікатори запису: Odoo 20
        пише JSON цілком, тож їх треба злити, а не затерти.
        """
        vals = {}
        if "company_registry" in self._fields:  # Odoo 18/19
            if code is not None:
                vals["company_registry"] = ua_digits(code) or False
            if ipn is not None:
                vals["vat"] = ua_digits(ipn) or False
            return vals
        if code is not None:  # Odoo 20
            vals["vat"] = ua_digits(code) or False
        if ipn is not None:
            merged = dict(identifiers or {})
            if ua_digits(ipn):
                merged[UA_VAT] = ua_digits(ipn)
            else:
                merged.pop(UA_VAT, None)
            vals["additional_identifiers"] = merged
        return vals

    # ------------------------------------------------------------------ попередження: номер не в тому полі
    @api.onchange("vat")
    def _l10n_ua_onchange_vat_slot(self):
        """Попередження на формі, не заборона (§19): у полі коду — 12 цифр ІПН (Odoo 20), у полі ІПН — 8 цифр
        ЄДРПОУ (Odoo 18/19). Записати так можна — звіти «Актива» скажуть про це ще раз, — але номер тоді не
        працює там, де його шукають: «компанія», пошук, податкова накладна."""
        if self.parent_id or not self.vat or not self._l10n_ua_home():
            return None
        number = ua_digits(self.vat)
        if "company_registry" not in self._fields and len(number) == 12:
            message = self.env._(
                "%(number)s has 12 digits, so it is a VAT payer IPN, not an EDRPOU / RNOKPP code. Put the IPN "
                "into “VAT payer IPN” (button next to this field) and the EDRPOU code (8 digits) or the RNOKPP "
                "(10 digits) here.", number=number)
        elif "company_registry" in self._fields and len(number) == 8:
            message = self.env._(
                "%(number)s has 8 digits, so it is an EDRPOU code, not a VAT payer IPN. Put the code into "
                "“EDRPOU / RNOKPP” and the IPN (12 digits for a company, 10 for an individual entrepreneur) here.",
                number=number)
        else:
            return None
        return {"warning": {"title": self.env._("The number is in the wrong field"), "message": message}}

    # ------------------------------------------------------------------ Odoo 20: ІПН — додатковий ідентифікатор
    @api.model
    def _get_all_additional_identifiers_metadata(self):
        """Odoo 20 відкидає ключ, якого немає в цьому переліку (у журналі — «Skipped … not in supported
        identifiers»), тож ІПН реєструє кожне ядро. `sequence` більше, ніж у коду (100): рахунок Odoo друкує
        «податковий номер» першим за порядком, і там має стояти код, а не ІПН."""
        return {**super()._get_all_additional_identifiers_metadata(), UA_VAT: {
            "sequence": 200,
            "label": _lt("VAT payer IPN"),
            "help": _lt("Individual tax number of a VAT payer: 12 digits for a company, 10 for an individual "
                        "entrepreneur (the same as the RNOKPP). Leave it empty if the partner does not pay VAT."),
            "placeholder": "123456789012",
            "category": "VAT",
            "countries": ["UA"],
            "validation_function": ua_check_ipn,
        }}

    def _compute_available_additional_identifiers_metadata(self):
        """Odoo 20 пропонує ідентифікатори країни контрагента; картці без країни в організації України ІПН
        теж потрібен."""
        super()._compute_available_additional_identifiers_metadata()
        meta = self._get_all_additional_identifiers_metadata()[UA_VAT]
        for partner in self.filtered(lambda p: not p.country_id):
            available = partner.available_additional_identifiers_metadata or {}
            if UA_VAT not in available and partner._l10n_ua_home():
                partner.available_additional_identifiers_metadata = {
                    **available, UA_VAT: self._lazy_translate_additional_identifiers_metadata(meta)}

    @api.depends("vat", "country_id")
    def _compute_is_company(self):
        """Odoo 20: «компанія» — свій комерційний партнер, у якого є `vat`. В Україні `vat` — код: 8 цифр
        (ЄДРПОУ) — юрособа, 10 (РНОКПП) — фізособа, зокрема ФОП; так Odoo рахує для Італії й Іспанії.
        Odoo 18/19 цього методу не викликає: там «компанію» ставить людина."""
        ua = self.filtered(lambda p: p.vat and p._l10n_ua_home())
        for partner in ua:
            partner.is_company = partner.commercial_partner_id == partner and len(ua_digits(partner.vat)) == 8
        super(ResPartner, self - ua)._compute_is_company()

    # ------------------------------------------------------------------ Odoo 18/19: підпис поля коду
    def _get_company_registry_labels(self):
        return {**super()._get_company_registry_labels(), "UA": self.env._("EDRPOU / RNOKPP")}

    # ------------------------------------------------------------------ підпис `vat` і перенос наявних даних
    @api.model
    def _l10n_ua_tax_labels(self):
        """Підпис поля `vat` в організаціях України — за серією (з `data/ua_tax_ids.xml` при встановленні й
        кожному оновленні модуля). Без нього Odoo підписує `vat` українською «ІПН» в усіх серіях — і в Odoo 20
        туди вводили б ІПН замість коду."""
        country = self.env.ref("base.ua", raise_if_not_found=False)
        if not country:
            return
        if "company_registry" in self._fields:
            label, label_uk = "VAT payer IPN", "ІПН платника ПДВ"
        else:
            label, label_uk = "EDRPOU / RNOKPP", "Код ЄДРПОУ / РНОКПП"
        if country.with_context(lang="en_US").vat_label != label:
            country.with_context(lang="en_US").vat_label = label
        if self.env["res.lang"].search_count([("code", "=", "uk_UA")]):
            country.update_field_translations("vat_label", {"uk_UA": label_uk})

    @api.model
    def _l10n_ua_normalize_tax_ids(self, legacy_vat_is_ipn=False):
        """Розкласти номери українських контрагентів за цим правилом; повертає звіт.

        Нічого не стирає: номер лише переїжджає у своє поле, повторний запуск нічого не робить. Код, який
        3A-dealer тримав у своєму полі `edrpou`, читається прямо зі стовпчика бази: після оновлення модуля поле
        стає псевдонімом і стовпчика не бачить.

        `legacy_vat_is_ipn` — для Odoo 20, де до 31.10.2026 `vat` вважали ІПН (бази «Актива» й 3A-dealer):
        тоді 10 цифр у `vat` — ІПН ФОП-платника (він же РНОКПП), і номер лягає в обидва поля. Викликати один раз —
        з міграції версії; на базі, де правило вже діє, 10 цифр у `vat` — просто РНОКПП. В Odoo 18/19 правило
        «`vat` — ІПН» не змінилося, тож там прапорець нічого не міняє.

        Звіт: {"code": заповнено кодів, "ipn": заповнено ІПН, "no_code": [ІПН є, коду немає],
        "conflict": [у двох полях різні коди — лишено як є]}.
        """
        cr = self.env.cr
        legacy = {}
        cr.execute("SELECT 1 FROM information_schema.columns WHERE table_name = 'res_partner' "
                   "AND column_name = 'edrpou'")
        if cr.fetchone():
            cr.execute("SELECT id, edrpou FROM res_partner WHERE coalesce(edrpou, '') <> ''")
            legacy = {pid: ua_digits(value) for pid, value in cr.fetchall()}
        Partner = self.with_context(active_test=False, tracking_disable=True, mail_notrack=True)
        partners = Partner.search([("parent_id", "=", False)]).filtered(lambda p: p._l10n_ua_home())
        series20 = "company_registry" not in self._fields
        report = {"code": 0, "ipn": 0, "no_code": [], "conflict": []}
        for partner in partners:
            old = legacy.get(partner.id, "")
            old = old if len(old) in (8, 9, 10) else ""
            number = ua_digits(partner.vat)
            vals = {}
            if series20:
                ids = dict(partner.additional_identifiers or {})
                if len(number) == 12 or (legacy_vat_is_ipn and len(number) == 10 and old and old != number):
                    code, ipn = old, number  # у `vat` стояв ІПН, код — у полі 3A-dealer
                elif legacy_vat_is_ipn and len(number) == 10:
                    code, ipn = number, number  # ФОП-платник: РНОКПП і ІПН — один номер
                else:
                    code, ipn = number or old, ""
                    if number and old and number != old:
                        report["conflict"].append(partner.id)
                if code != number:
                    vals["vat"] = code or False
                    report["code"] += bool(code)
                if ipn and not ids.get(UA_VAT):
                    vals["additional_identifiers"] = {**ids, UA_VAT: ipn}
                    report["ipn"] += 1
                ipn = ipn or ua_digits(ids.get(UA_VAT))
            else:
                code = ua_digits(partner.company_registry)
                if not code:
                    code = old or (number if len(number) in (8, 10) else "")
                    if code:
                        vals["company_registry"] = code
                        report["code"] += 1
                elif old and old != code:
                    report["conflict"].append(partner.id)
                if len(number) == 8:
                    if code == number:
                        vals["vat"] = False  # код стояв у полі ІПН
                    else:
                        report["conflict"].append(partner.id)
                ipn = number if len(number) in (10, 12) else ""
            if vals:
                partner.write(vals)
            if ipn and not code:
                report["no_code"].append(partner.id)
        if series20 and partners:
            # «Компанія» в Odoo 20 рахується лише при зміні залежностей: ФОП, у яких додався тільки ІПН, і
            # юрособи без змін у `vat` перераховуємо явно — за новим правилом.
            self.env.add_to_compute(self._fields["is_company"], partners)
            partners.flush_recordset(["is_company"])
        return report
