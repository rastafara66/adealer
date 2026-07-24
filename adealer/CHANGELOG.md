# Changelog — 3A-dealer (`adealer`)

Усі помітні зміни модуля. Версії у форматі `19.0.<x.y.z>`.
All notable changes. Newest on top.

## [19.0.1.4.0] — 2026-07-24
### Added / Додано
- **«Реалізації»** — новий пункт меню в розділі **Продажі**: журнал документів реалізації
  (Видаткові, `account.move` out_invoice) у стилі 1С — Дата, Номер, Клієнт, 1С-ref, Сума,
  Статус, Оплата.
- New **Sales invoices** menu under Sales — a 1C-style journal of delivery notes.
### Changed / Змінено
- **Дашборд «Головна»** тепер стартова сторінка **за замовчуванням** (для користувачів без
  власної стартової) і показується єдиним пунктом без підменю; отримав українську назву.
- **Автосалон** рахує продажі авто з **Реалізацій** (позиції-авто за назвою «Автомобіль…/Автобус…»),
  а не лише з довідника авто — тепер показує реальні продажі Ford.
- The **Home dashboard** is now the default landing page and a single top-level menu item; the
  **Showroom** tab counts vehicle sales from delivery notes (vehicle lines), not only the car register.

## [19.0.1.3.0] — 2026-07-24
### Added / Додано
- **Дашборд «Головна»** — новий перший пункт застосунку (відкривається за замовчуванням).
  Перемикач типу дашборду: **Автосалон** (авто в наявності, продано за період, продажі авто),
  **Автосервіс** (наряди за період, виручка СТО, у роботі, календар найближчих ремонтів),
  **Автозапчастини** (позиції на складі, видача запчастин, продаж, вартість складу).
  Період вибирається (з/по); KPI-плитки + стовпчиковий графік по місяцях + список.
  Можна зробити стартовою сторінкою (Налаштування → Home page → «Дашборд»).
- New **Home dashboard** — the first app menu, opened by default. A dashboard-type switch:
  **Showroom** (vehicles in stock, sold in period, sales), **Service** (repair orders,
  revenue, in-progress, upcoming-repairs calendar), **Parts** (stock positions, parts issued,
  sales, stock value). Selectable period; KPI tiles + monthly bar chart + a details list.

## [19.0.1.2.0] — 2026-07-22
### Added / Додано
- **Заявка на обслуговування** — нова модель `adealer.service.request`: дата/час візиту,
  клієнт, авто, пробіг, причина звернення, менеджер, статус. Кнопка **«Створити Замовлення»**
  породжує Замовлення клієнта (перенося клієнта й авто) — це вхідна точка ланцюга
  Заявка → Замовлення → Наряд → Видаткова. Календар СТО тепер будується на заявках, а не
  на нарядах (наряд у ланцюзі зʼявляється на два документи пізніше).
- New **Service request** model (`adealer.service.request`): scheduled date/time, customer,
  vehicle, mileage, reason, manager, status; a **Create Sale Order** button turns the request
  into a customer order. The workshop calendar is now built on requests, not repair orders.
### Changed / Змінено
- Меню **«Заявки на обслуговування»** відкриває заявки, а не список замовлень (раніше воно
  дублювало меню «Замовлення клієнтів» — обидва вели на ту саму дію).
- The **Maintenance requests** menu now opens requests instead of duplicating the Sale orders list.

## [19.0.1.1.3] — 2026-07-17
### Changed / Змінено
- **Вужчий боковий чатер** у формах документів — 380px замість стандартних 530px (більше місця під форму).
- **Детальніші записи в чатері:** при проведенні наряду вказуються назви й **суми** створених
  документів; при переході в закриваючу стадію — окреме повідомлення «Order closed».
- Narrower side chatter (380px). Richer chatter logs: posted repair orders show created document
  names and amounts; a dedicated message when the order moves to a closing stage.

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
