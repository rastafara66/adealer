# -*- coding: utf-8 -*-

import re

from odoo import api, fields, models

# Іконка групи товарів за її назвою. Групи приходять з довідника номенклатури
# облікової системи (теки «Запчастини», «Масла», «Шини»…), тож правила — це
# корені слів трьома мовами, якими такі теки називають: українською,
# російською й англійською.
#
# 🔴 Перше правило, що збіглося, перемагає, тому вужчі стоять ВИЩЕ ширших:
# «Фільтр масляний» — фільтр, а не масло; «Масло КПП» — масло, а не
# трансмісія; «Мийка автомобіля» — мийка, а не автомобіль. Перестановка двох
# рядків мовчки міняє іконки десяткам груп — тест test_product_category_icon
# тримає приклади кожного такого спору.
#
# Назви марок і моделей сюди НЕ пишемо: марку впізнаємо за довідником марок
# автопарку самої бази (`fleet.vehicle.model.brand`), модель — за об'ємом
# двигуна чи паливом у назві («… 1.6 бензин»).
ICON_RULES = [
    (r"фільтр|фильтр|filter", "fa-filter"),
    (r"неліквід|неликвид|невикорист|неиспольз|obsolete|unused", "fa-ban"),
    (r"розіграш|розыгрыш|lottery|prize", "fa-trophy"),
    (r"\bакці|\bакци|\bpromo", "fa-gift"),
    (r"діагност|диагност|огляд|осмотр|дефектов|diagnos|inspection", "fa-stethoscope"),
    (r"мийк|мойк|\bwash", "fa-shower"),
    (r"\bшин|\btyre|\btire", "fa-life-ring"),
    (r"розвал|развал|alignment", "fa-crosshairs"),
    (r"\bmix\b|фарб|краск|красок|лакофарб|покрас|малярк|молярк|грунт|шпакл|paint",
     "fa-paint-brush"),
    (r"поліров|полиров|polish", "fa-magic"),
    (r"масл|мастил|смазк|\boil|grease|lubric", "fa-tint"),
    (r"рідин|жидкост|автохім|автохим|хімі|химия|fluid|chemic", "fa-flask"),
    (r"аксесуар|аксессуар|бутік|бутик|вітрин|витрин|accessor", "fa-shopping-bag"),
    (r"гарант|warrant|захист|защит|protect", "fa-shield"),
    (r"гальм|тормоз|brake", "fa-stop-circle-o"),
    (r"охолод|охлажд|радіатор|радиатор|cooling", "fa-thermometer-half"),
    (r"кондиц|клімат|климат|опален|отоплен|air.?con|heating", "fa-snowflake-o"),
    (r"вихлоп|выхлоп|глушник|глушит|exhaust", "fa-cloud"),
    (r"палив|топлив|\bfuel", "fa-fire"),
    (r"ламп|світильн|светильн|освітл|освещ|\blight", "fa-lightbulb-o"),
    (r"електр|электр|енерго|энерго|акумулят|аккумулят|запобіжн|предохран|\bреле\b|"
     r"статор|стартер|генератор|electr|batter", "fa-bolt"),
    (r"двигун|двигат|\bдвс\b|\bгрм\b|\bгбц\b|engine|\bmotors?\b", "fa-cogs"),
    (r"трансміс|трансмис|\bкпп\b|\bакпп\b|\bмкпп\b|\b[aа4]wd\b|роздат|раздат|редуктор|"
     r"зчеплен|сцеплен|gearbox|transmission|clutch", "fa-cog"),
    (r"рульов|рулев|\bгур\b|гідропідс|гидроусил|steering", "fa-circle-o-notch"),
    (r"ходов|підвіск|подвеск|suspension|chassis", "fa-road"),
    (r"\bрт[іи]\b|резин|rubber", "fa-circle-o"),
    (r"кузов|рихтов|розбир|разборк|\bbody", "fa-car"),
    (r"салон|interior", "fa-th-large"),
    (r"техобсл|техообсл|обслугов|обслужив|\bто\b|maintenance", "fa-calendar-check-o"),
    (r"підготов|подготов|передпродаж|предпродаж|preparation", "fa-check-square-o"),
    (r"метиз|кріпл|кріпіж|крепеж|крепл|fastener|hardware", "fa-thumb-tack"),
    (r"не\s*оригін|не\s*оригин|неоригін|неоригин|аналог|aftermarket|analog", "fa-puzzle-piece"),
    (r"оригін|оригин|original|genuine", "fa-certificate"),
    (r"запчаст|spare|\bparts?\b", "fa-puzzle-piece"),
    (r"\bдиск|колес|wheel|\brims?\b", "fa-dot-circle-o"),
    (r"інструмент|инструмент|інвентар|инвентар|\btools?\b", "fa-wrench"),
    (r"аптечк|медич|медиц|first.?aid", "fa-medkit"),
    (r"знаки пб|пожеж|пожар|\bпб\b|fire.?safety", "fa-fire-extinguisher"),
    (r"охорон\w* праці|охран\w* труда|safety", "fa-exclamation-triangle"),
    (r"\bзнак|\bsigns?\b", "fa-map-signs"),
    (r"бланк", "fa-file-text-o"),
    (r"канц|stationery|office", "fa-pencil"),
    (r"будів|будмат|стройм|строит|конструкц|construction|building", "fa-building"),
    (r"господар|хозтовар|госптовар|household", "fa-home"),
    (r"мебл|мебел|furniture", "fa-bed"),
    (r"одяг|одежд|уніформ|униформ|clothing|uniform|workwear", "fa-shirtsinbulk"),
    (r"каталог|catalog|літератур|литератур", "fa-book"),
    (r"реклам|маркетинг|відділ продаж|отдел продаж|advert|marketing", "fa-bullhorn"),
    (r"доставк|перевез|transport|delivery|shipping", "fa-truck"),
    (r"агентськ|агентск|винагород|вознагражд|комісі|комисси|commission", "fa-percent"),
    (r"оренд|аренд|\brent|\blease", "fa-key"),
    (r"полив|газон|irrigation|garden", "fa-tree"),
    (r"\bнма\b|нематер|intangible", "fa-copyright"),
    (r"\bос\b|основн|\bмбп\b|малоцін|малоцен|fixed asset", "fa-briefcase"),
    (r"обладнан|оборудован|устаткуван|equipment", "fa-industry"),
    (r"матеріал|материал|витратн|расходн|material|consumable", "fa-cube"),
    (r"бухгалт|рахун|\bрах\b|\bсчет|accounting", "fa-calculator"),
    (r"expens", "fa-money"),
    (r"автомоб|\bавто\b|стоянк|парков|vehicle|\bcars?\b|parking", "fa-car"),
    # модель авто: паливо або «об'єм двигуна … рік» («… 2.0 2010 -»)
    (r"бензин|дизел|diesel|petrol|gasoline|\b\d[.,]\d\b.*\b(19|20)\d\d\b", "fa-car"),
    (r"робот|работ|\bсто\b|\bworks?\b|labou?r|repair|ремонт", "fa-wrench"),
    (r"послуг|услуг|сервіс|сервис|service", "fa-handshake-o"),
    (r"товар|goods|\bproducts?\b", "fa-cubes"),
    (r"службов|служеб|внутрішн|internal", "fa-cog"),
    (r"забезпеч|обеспеч|support", "fa-building-o"),
    (r"проче|інше|иное|другое|інші|разное|різне|\bother|\bmisc", "fa-ellipsis-h"),
]
ICON_RULES = [(re.compile(pattern), icon) for pattern, icon in ICON_RULES]

# Латинські літери, що в кириличній назві вдають кириличні: «оригiнал» з
# латинською «i» чи «ОС c 2016» з латинською «c». Правило «оригін» таке слово
# не бачить, а на око різниці нема.
LOOKALIKES = str.maketrans("aceiopxykmthb", "асеіорхукмтнв")


def _texts(name):
    """Назва в нижньому регістрі — як є і з латинськими двійниками → кирилиця.

    Перетворену берем лише для назви, де кирилиці більше, ніж латиниці, і
    звіряємо ОБИДВІ: у «Подготовка MIX» справжнє латинське слово, і в
    перетвореній воно стало б «міх».
    """
    text = " ".join((name or "").lower().split())
    cyrillic = sum(1 for ch in text if "а" <= ch <= "я" or ch in "іїєґё")
    latin = sum(1 for ch in text if "a" <= ch <= "z")
    if cyrillic > latin:
        return text, text.translate(LOOKALIKES)
    return (text,)


def icon_for_name(name, brands=()):
    """Іконка Font Awesome за назвою групи, або порожньо, якщо назва нічого не каже.

    `brands` — назви марок авто в нижньому регістрі: група «Opel» — це авто.
    """
    texts = _texts(name)
    for text in texts:
        if any(text == brand or text.startswith(brand + " ") for brand in brands):
            return "fa-car"
    for rule, icon in ICON_RULES:
        if any(rule.search(text) for text in texts):
            return icon
    return ""


class ProductCategory(models.Model):
    _inherit = 'product.category'

    adealer_icon = fields.Char(
        string="Icon",
        help="Font Awesome icon shown next to the group in the product list grouped by "
             "group, e.g. fa-tint. It is picked from the name when the group is created; "
             "clear it and save to pick it again.")

    @api.model_create_multi
    def create(self, vals_list):
        categories = super().create(vals_list)
        categories.filtered(lambda c: not c.adealer_icon)._adealer_pick_icon()
        return categories

    def write(self, vals):
        res = super().write(vals)
        # Прапорець контексту — бо підбір сам пише сюди й порожнє значення теж:
        # без нього група, якій нічого не підійшло, підбирала б собі іконку
        # нескінченно.
        if ('adealer_icon' in vals and not vals['adealer_icon']
                and not self.env.context.get('adealer_icon_picking')):
            self._adealer_pick_icon()
        return res

    def _adealer_pick_icon(self):
        """Підібрати іконку за назвою; назва нічого не каже — взяти батьківську.

        Батьків обробляємо раніше за дітей (за `parent_path`), щоб «Задня
        частина» в «Ходовій частині» успадкувала вже підібрану іконку ходової.
        Порожньо лишається лише там, де нічого не підійшло й батька немає, —
        список тоді показує теку.
        """
        brands = {
            name.lower().strip()
            for name in self.env['fleet.vehicle.model.brand'].sudo().search([]).mapped('name')
            if name and name.strip()
        }
        for category in self.with_context(adealer_icon_picking=True).sorted(
                lambda c: c.parent_path or ''):
            category.adealer_icon = (icon_for_name(category.name, brands)
                                     or category.parent_id.adealer_icon or False)

    def action_adealer_pick_icons(self):
        """Дія зі списку груп: підібрати іконки заново за поточними назвами."""
        self._adealer_pick_icon()
