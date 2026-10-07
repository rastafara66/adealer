# Changelog — 3A-dealer (`adealer`)

Усі помітні зміни модуля. Версії у форматі `19.0.<x.y.z>`.
All notable changes. Newest on top.

## 19.0.1.18.0 — 2026-10-07

### Added

- Barcode scanning in repair, sales and purchase orders: a scan adds the product, a repeat scan adds quantity.
- Сканування штрихкодів у нарядах, продажах і закупівлях: скан додає товар, повторний — кількість.

## 19.0.1.17.0 — 2026-10-04

### Added

- Interface in Polish.
- Інтерфейс польською.

## 19.0.1.16.0 — 2026-10-03

### Added

- Products open as a list. Products by group: a collapsible tree of nested groups, each group with its own icon.
- Товари відкриваються списком. Товари за групами: згорнуте дерево вкладених груп, у кожної групи своя іконка.

## 19.0.1.15.5 — 2026-10-03

### Changed

- Hints on fields and buttons. Error messages say what to do. Bug fixes.
- Підказки на полях і кнопках. Повідомлення про помилки кажуть, що робити. Виправлено помилки.

## 19.0.1.15.0 – 19.0.1.15.4 — 2026-09-29

### Added

- Попередній запис: клієнт без контакту, колір виду ремонту, повні дані й запис кліком на дошці по постах. Service bookings: customer name without a contact, repair type color, full details and click-to-book on the bay board.

### Fixed

- Виправлено помилки. Bug fixes.

## 19.0.1.14.3 – 19.0.1.14.4 — 2026-09-29

### Fixed

- Виправлено помилки (також 19.0.1.14.1, 19.0.1.14.2). Bug fixes (also 19.0.1.14.1, 19.0.1.14.2).

## 19.0.1.14.0 — 2026-09-28

### Added

- Інтерфейс французькою, німецькою, іспанською й нідерландською; український переклад повний. Interface in French, German, Spanish and Dutch; Ukrainian translation completed.

## 19.0.1.13.2 — 2026-09-28

### Changed

- Опис оновлено. Description updated.

## [19.0.1.13.1] — 2026-09-28

### Changed / Змінено

- The description opens with links to its English and Ukrainian versions, each complete on its own.

## [19.0.1.13.0] — 2026-09-15

### Added / Додано

- Менеджер після входу потрапляє на «Головну» 3A-dealer.
- After login a manager lands on the 3A-dealer Home dashboard; an accountant lands on the accounting app's home page if one is installed.

## [19.0.1.12.3] — 2026-09-12

### Fixed / Виправлено

- Bug fixes. Виправлено помилки.

- Дрібні покращення. Minor improvements.

## [19.0.1.12.2] — 2026-09-10

### Fixed / Виправлено

- Bug fixes. Виправлено помилки.

### Added / Додано

- Структура підпорядкованості документа.
- «Ввести на підставі»

## 19.0.1.12.0 - 2026-09-09

### Fixed

- Bug fixes. Виправлено помилки.

- Дрібні покращення. Minor improvements.

## 19.0.1.11.3 - 2026-09-07

### Changed

- Адреса підтримки — adealer@aktiv.in.ua.

## 19.0.1.11.2 — 2026-09-06

### Changed

- `vehicle dealer` у назві й summary.

## 19.0.1.11.1 — 2026-09-05

### Changed

- Author website now points at the line's own apps page, `https://aktiv.in.ua/dodatky/`.

## 19.0.1.11.0 — 2026-09-05

### Added

- The version check now covers the paid add-ons, not just the core module.
- Their repository is private, so the manifest cannot be read from GitHub the way the core module's is.
- A newer version is announced on the vehicle card and on the repair order — the two screens a dealership has open all day.

### Changed

- The update check runs daily instead of weekly.
- One button checks both.

### Fixed

- Bug fixes. Виправлено помилки.

## 19.0.1.10.2 — 2026-09-04

### Fixed

- Bug fixes. Виправлено помилки.

- Дрібні покращення. Minor improvements.

## 19.0.1.10.1 — 2026-09-04

### Changed

- Store description rebuilt on the shared layout of the line.
- Опис оновлено. Description updated.

## [19.0.1.10.0] — 2026-09-03

### Added / Додано

- Підказки про платні надбудови.
- Paid add-on hints.

### Fixed / Виправлено

- Bug fixes. Виправлено помилки.

## [19.0.1.8.3] — 2026-08-16

### Fixed / Виправлено

- Bug fixes. Виправлено помилки.

- Дрібні покращення. Minor improvements.

## [19.0.1.8.2] — 2026-08-15

### Changed / Змінено

- Сторінка опису в App Store.
- Store description page.

## [19.0.1.8.1] — 2026-08-15

### Changed / Змінено

- Автозвіт про помилки тепер знає модуль-джерело.
- Error reports now carry the source module.

## [19.0.1.8.0] — 2026-08-13

### Added / Додано

- Фотогалерея авто.
- Vehicle photo gallery.

## [19.0.1.7.5] — 2026-08-11

### Changed / Змінено

- Розділ «Звіти про помилки» на сторінці опису.
- Added an Error reports section to the App Store description page: what is sent, what is never sent.

## [19.0.1.7.4] — 2026-08-11

### Changed / Змінено

- Повна англійська галерея скріншотів.
- Опис оновлено. Description updated.

## [19.0.1.7.3] — 2026-08-11

### Changed / Змінено

- Демо-дані інтернаціоналізовано (English).
- Нові англійські скріншоти галереї.
- Demo data in English.

## [19.0.1.7.2] — 2026-08-09

### Changed / Змінено

- Англійський UI звірено для міжнародного вжитку.
- English UI reviewed for international use: removed the last non-English hints from field tooltips; all visible labels.

## [19.0.1.7.1] — 2026-08-09

### Changed / Змінено

- Ендпоінт звітів про помилки.
- Default reporting endpoint switched to the neutral `/odoo-report` path (still configurable; the old path keeps working.

## [19.0.1.7.0] — 2026-08-09

### Added / Додано

- Автоматичні звіти про помилки (за згодою, типово вимкнено)
- Розмова з користувачем — не звітується.
- Згода: Налаштування → 3A-dealer → Error reports (типово Off) + окремий пункт меню Settings → Error reports зі списком черги.
- New automatic error reports (opt-in, off by default): model `adealer.error.report`.

## [19.0.1.6.3] — 2026-08-09

### Changed / Змінено

- Картка додатка в App Store.
- Опис оновлено. Description updated.

## [19.0.1.6.2] — 2026-08-08

### Changed / Змінено

- Єдиний автор для всіх додатків.
- Single `author` value (`chukhin`) across the modules, so all published apps are found together in the App Store.

## [19.0.1.6.1] — 2026-07-30

### Changed / Змінено

- Уточнено написи інтерфейсу.
- Interface wording tidied up.

## [19.0.1.6.0] — 2026-07-30

### Added / Додано

- Дошка записів по постах.
- Продажі авто.
- Автомобіль як обʼєкт.
- New Posts board (workplace columns, classic style) with a Posts/Period switch; Vehicle sales menu + filter + car↔invoice link.

### Changed / Змінено

- Автосалон.
- Календар обслуговування.
- Попередній запис.
- The Showroom counts vehicle sales by the real vehicle object (not by product name); the Service calendar shows repair orders again.

### Fixed / Виправлено

- Bug fixes. Виправлено помилки.

## [19.0.1.5.0] — 2026-07-28

### Added / Додано

- Попередній запис на обслуговування.
- New Service booking model (mirrors the preliminary-appointment register): post/workplace, mechanic, advisor, duration, customer, vehicle.

## [19.0.1.4.0] — 2026-07-24

### Added / Додано

- «Реалізації»
- New Sales invoices menu under Sales — a classic journal of delivery notes.

### Changed / Змінено

- Дашборд «Головна»
- Автосалон.
- The Home dashboard is now the default landing page and a single top-level menu item.
- «Календар обслуговування»
- The Service calendar menu shows repair orders again (was pointing at the empty Requests model).

## [19.0.1.3.0] — 2026-07-24

### Added / Додано

- Дашборд «Головна»
- New Home dashboard — the first app menu, opened by default.

## [19.0.1.2.0] — 2026-07-22

### Added / Додано

- Заявка на обслуговування.
- New Service request model (`adealer.service.request`): scheduled date/time, customer, vehicle, mileage, reason, manager, status.

### Changed / Змінено

- Меню «Заявки на обслуговування» відкриває заявки, а не список замовлень (раніше воно дублювало меню «Замовлення клієнтів»
- The Maintenance requests menu now opens requests instead of duplicating the Sale orders list.

## [19.0.1.1.3] — 2026-07-17

### Changed / Змінено

- Вужчий боковий чатер.
- Детальніші записи в чатері: при проведенні наряду вказуються назви й суми створених документів.
- Narrower side chatter (380px).

## [19.0.1.1.2] — 2026-07-16

### Fixed / Виправлено

- Bug fixes. Виправлено помилки.

- Дрібні покращення. Minor improvements.

## [19.0.1.1.1] — 2026-07-15

### Fixed / Виправлено

- Bug fixes. Виправлено помилки.

- Дрібні покращення. Minor improvements.

## [19.0.1.1.0] — 2026-07-12

### Added / Додано

- Перший публічний реліз.
