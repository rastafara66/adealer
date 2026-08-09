# Changelog — 3A-dealer (`adealer`)

Усі помітні зміни модуля. Версії у форматі `19.0.<x.y.z>`.
All notable changes. Newest on top.

## [19.0.1.6.3] — 2026-08-09
### Changed / Змінено
- **Картка додатка в App Store** — замість скріншота тепер намальований банер
  з назвою й трьома напрямками двома мовами. Скріншот у мініатюрі читався
  як сіра пляма; самі скріншоти лишились — в галереї.
- The App Store card is a drawn banner (bilingual) instead of a screenshot; the
  screenshots remain as the gallery. Drawn from code by `tools/make_banner.py`,
  taking its colours from the module icon.

## [19.0.1.6.2] — 2026-08-08
### Changed / Змінено
- **Єдиний автор для всіх додатків** — поле `author` зведено до `chukhin` (було «3A Dealer»
  у `adealer` і «ser.chukhin@gmail.com» у `adealer_theme`). Через різні значення пошук у
  App Store за автором не показував усі додатки разом.
- Single `author` value (`chukhin`) across the modules, so all published apps are found
  together in the App Store.

## [19.0.1.6.1] — 2026-07-30
### Changed / Змінено
- Причесано формулювання інтерфейсу та внутрішню документацію (нейтральні generic-назви;
  деякі мітки полів перейменовано на загальні, напр. «Ext. ref.», «WH ID (source)»).
- Interface wording and in-repo documentation tidied up (neutral, generic naming).

## [19.0.1.6.0] — 2026-07-30
### Added / Додано
- **Дошка записів по постах** — новий вигляд «По постах» (колонки-пости) з перемикачем
  **Пости / Період**: кілька записів на один час стоять у різних колонках-постах.
- **Продажі авто** — окремий пункт меню в розділі Продажі + фільтр «Продаж авто» у списку
  Реалізацій (лише документи, що продають авто) + лінк **авто ↔ Реалізація** в обидва боки.
- **Автомобіль як обʼєкт** — `dealer.car` отримав дату й документ продажу, VIN-ключ, текст моделі;
  імпорт проданих авто з довідника автомобілів (за VIN-обʼєктом).
- New **Posts board** (workplace columns, classic style) with a Posts/Period switch; **Vehicle sales**
  menu + filter + car↔invoice link; vehicles imported as real objects (`dealer.car`).
### Changed / Змінено
- **Автосалон** тепер рахує продажі авто за **реальним обʼєктом** (`dealer.car` / VIN), а не за
  назвою рядка реалізації — послуги/запчастини більше не потрапляють у «продаж авто».
- **Календар обслуговування** знову показує наряди; виручка СТО й продаж ЗЧ рахуються за
  діловою датою наряду (`schedule_date`), а не за датою імпорту.
- **Попередній запис**: майстер-приймальник (довідник співробітників), лінк на замовлення клієнта
  (`sale.order`), інформативніший календар (держномер/роботи/механік).
- The **Showroom** counts vehicle sales by the real vehicle object (not by product name); the
  **Service calendar** shows repair orders again; service/parts use the business date.
### Fixed / Виправлено
- **JS-помилка завантаження модулів** (luxon у дошці записів) — ламала бекенд-бандл; виправлено.
- Fixed a JavaScript module-loading error (luxon import in the bookings board).

## [19.0.1.5.0] — 2026-07-28
### Added / Додано
- **Попередній запис на обслуговування** — нова модель `adealer.service.booking`, що дзеркалить
  регістр попередніх записів: дата/час запису, пост (робоче місце), механік,
  майстер-приймальник, тривалість робіт, час прийому а/м, клієнт, авто, модель, рік, держномер,
  телефон, VIN, заявлені роботи, вид ремонту, GUID. Наряд-замовлення може бути прив'язаний до
  запису (реквізит «Заказ») — кнопка «Створити наряд». Календар записів (по постах), список, форма.
  Довідники **«Робочі місця / пости»** та **«Види ремонту»** у Налаштуваннях.
- New **Service booking** model (mirrors the preliminary-appointment register): post/workplace,
  mechanic, advisor, duration, customer, vehicle, requested works, repair type; a repair order can
  be linked to a booking. Calendar/list/form + Workplaces and Repair types reference lists.

## [19.0.1.4.0] — 2026-07-24
### Added / Додано
- **«Реалізації»** — новий пункт меню в розділі **Продажі**: журнал документів реалізації
  (Видаткові, `account.move` out_invoice) у класичному стилі — Дата, Номер, Клієнт, Ext. ref, Сума,
  Статус, Оплата.
- New **Sales invoices** menu under Sales — a classic journal of delivery notes.
### Changed / Змінено
- **Дашборд «Головна»** тепер стартова сторінка **за замовчуванням** (для користувачів без
  власної стартової) і показується єдиним пунктом без підменю; отримав українську назву.
- **Автосалон** рахує продажі авто з **Реалізацій** (позиції-авто за назвою «Автомобіль…/Автобус…»),
  а не лише з довідника авто — тепер показує реальні продажі авто.
- The **Home dashboard** is now the default landing page and a single top-level menu item; the
  **Showroom** tab counts vehicle sales from delivery notes (vehicle lines), not only the car register.
- **«Календар обслуговування»** знову показує наряди (repair.order за `schedule_date`) — раніше він
  був переведений на «Заявки», яких у базі ще нема, тож виглядав порожнім; заявки лишаються зі своїм
  календарем у меню «Заявки на обслуговування».
- The **Service calendar** menu shows repair orders again (was pointing at the empty Requests model).

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
