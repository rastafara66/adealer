# Changelog — 3A-dealer (`adealer`)

Усі помітні зміни модуля. Версії у форматі `19.0.<x.y.z>`.
All notable changes. Newest on top.

## [19.0.1.1.2] — 2026-07-16
### Fixed / Виправлено
- **Виправлено збій оновлення з версій ≤1.1.0** через фічу «Організація». Дефолт поля
  `organization_id` міг виконуватись під час додавання колонки, коли таблиця `dealer_organization`
  ще не створена → `relation "dealer_organization" does not exist` і відкат апгрейду. Тепер
  `_default_org` перевіряє наявність таблиці (`to_regclass`) і безпечно повертає порожньо під час install/upgrade.
- Fixed an upgrade crash from versions ≤1.1.0 introduced by the Organization feature: the
  `organization_id` default could run while the `dealer_organization` table did not yet exist,
  aborting the upgrade. `_default_org` now guards on table existence.

## [19.0.1.1.1] — 2026-07-15
### Fixed / Виправлено
- **Прибрано зовнішню залежність `pandas`.** Імпорт Excel (.xlsx) тепер через **openpyxl**
  (входить у стандартний Odoo). Модуль встановлюється чисто **скрізь, включно з Odoo Online/SaaS**,
  без ручного `pip install`. Торкнулось майстрів імпорту: партнери, адреси, авто, моделі авто.
- Removed the `pandas` external dependency — Excel import now uses **openpyxl** (bundled with Odoo);
  the module installs cleanly everywhere, including **Odoo Online**, with no manual `pip install`.

## [19.0.1.1.0] — 2026-07-12
### Added / Додано
- Перший публічний реліз. Initial public release:
  - Ланцюг документів: Замовлення → Наряд-замовлення → Видаткова / Акт / Рахунок
    (кожен «на підставі» попереднього). Document chain with "on the basis of" links.
  - Наряд-замовлення СТО, автомобілі клієнтів (VIN), склад автосалону, запчастини й аналоги,
    нормо-години. Repair orders, customer vehicles, showroom stock, parts & analogs, standard hours.
  - Звіти у двох стилях (готові + pivot), друковані форми UA, журнали документів.
    Reports (ready + pivot), UA printable forms, document journals.
  - Фірмова тема + бічне меню (navy/gold). Імпорт з Excel. ~60 логотипів брендів.
    Branded theme + sidebar. Excel import. ~60 brand logos.
  - Інтерфейс EN + UA. English + Ukrainian interface.
