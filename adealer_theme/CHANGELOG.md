# Changelog — 3A-dealer Theme (`adealer_theme`)

Navy & gold backend theme for Odoo. Newest on top.
Тема оформлення бекенду. Найновіше — зверху.

## 19.0.1.2.1 - 2026-09-07

### Changed

- Адреса підтримки — **adealer@aktiv.in.ua**. Стара, `adealer@yellow.in.ua`, вела на поштову
  скриньку проєкту yellow; лінійка живе на власному домені, і писати треба
  туди. Адреса стоїть у маніфесті (її показує магазин) і на сторінці опису.

## 19.0.1.2.0 — 2026-09-05

### Added

- **Menu sidebar.** The current app's menu tree on the left, collapsible with
  one click, in **any** Odoo app — the theme is bought separately from the
  3A-dealer module, so a buyer who installed only the theme should get the menu
  everywhere, not just inside an app they may not own.

  It came from the card, not from a plan: the store picture showed a sidebar
  and the theme had none. Drawing one anyway would have promised something the
  buyer does not get, so the theme grew the feature instead.

  🔴 **It stands down where the 3A-dealer module already draws its own.** That
  module has an app-scoped sidebar behind a setting; without the guard, anyone
  with both installed would see two identical menus stacked on each other. The
  theme checks the same session flag and yields — cheaper and more reliable
  than two modules negotiating, and it works whichever was installed first.

## 19.0.1.1.5 — 2026-09-05

### Fixed

- 🔴 **The card picture was the wrong shape.** The first replacement was
  landscape, 560×315, the format the line uses for ordinary apps. A theme card
  in the store is a browser-window mock and is **portrait**: measured across
  ten published themes, the ratio runs 0.78–0.83. At 1.78 ours was shown as a
  narrow strip between white bands — it read as abandoned rather than as a
  theme. Now 800×1000, drawn from the theme's own colours, showing what the
  theme does to a real backend screen.

### Changed

- The summary says **backend** in its first words. Most cards in the Themes
  catalogue are website themes, and a buyer reads ours the same way by habit.
  Learning it after installing costs a refund and a one-star review, for a
  module that works exactly as intended.
- Author website points at the dedicated apps page,
  `https://aktiv.in.ua/dodatky/`.

## 19.0.1.1.2 – 19.0.1.1.4 — 2026-09-04 … 2026-09-05

### Fixed

- **The store listing now shows the banner**, and the description page no
  longer opens with a broken image.
- **The support address is back on the store page.**

### Changed

- The store description uses the same layout as the rest of the line.
- This module now ships its own CHANGELOG.md.


## 19.0.1.1.0 — 2026-08

- Initial release: navy & gold palette across the backend (top bar, buttons, lists, tabs, breadcrumbs, pager). Pure CSS, no SCSS rebuild, no JS.
  Перший випуск: палітра navy & gold по всьому бекенду, чистим CSS.
