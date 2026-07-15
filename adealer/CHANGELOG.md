# Changelog — 3A-dealer (`adealer`)

Усі помітні зміни модуля. Версії у форматі `19.0.<x.y.z>`.
All notable changes. Newest on top.

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
