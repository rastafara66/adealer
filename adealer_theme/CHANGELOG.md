# Changelog — 3A-dealer Theme (`adealer_theme`)

Navy & gold backend theme for Odoo. Newest on top.
Тема оформлення бекенду. Найновіше — зверху.

## 18.0.1.2.0 — 2026-09-06 — перший випуск для Odoo 18

Порт із серії 19.0. Правити не довелось нічого: тема — це CSS і два JS-файли,
а версійно-залежного API вона не вживає. Змінено лише номер серії у версії.

### Перевірено

- Встановлення в чисту базу на живому Odoo 18.0-20250626: `installed`.
- Прогін тестів разом із `adealer`: 49 тестів, 0 падінь.

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

## 19.0.1.1.4 — 2026-09-05

### Fixed

- 🔴 **The card had no picture, and the description page opened with a broken
  one.** `index.html` referenced `banner.png`, which was never in the folder,
  and the manifest had no `images` key at all — so the listing would have shown
  a grey rectangle beside the rest of the line, and the page a broken image at
  the very top. Nothing failed along the way: the module installs, the tests
  are green, and only a pair of eyes on the finished page would have caught it.

  Found while preparing the module for publication — which is itself the point:
  the theme has been ready in the repository for a while, but a module in a
  repository is not published by itself. Each app is registered separately in
  the author dashboard, and that step had never been done.

  The banner is generated from the theme's own colours
  (`3A/tools/store/make_banner_theme.py`), so it can be rebuilt and compared,
  and it shows what the theme actually does to the backend rather than an
  abstract gradient.

## 19.0.1.1.3 — 2026-09-04

### Fixed

- 🔴 **The support address is back on the store page.** Moving the
  descriptions onto the shared generator dropped it from EVERY page in one
  command: pages still built, nothing failed, and a buyer simply had nowhere
  to write. The support block is now emitted by the generator itself, from
  the manifest's `support` key, and the build fails if it is missing.

## 19.0.1.1.2 — 2026-09-04

### Changed

- **Store description rebuilt on the shared layout** used across the whole line
  (Odoo's own `oe_container` / `oe_row` / `oe_span6` classes) instead of hand-rolled
  inline styles — in the catalogue the modules looked like products by different
  authors. Generated from `3A/tools/store/specs/adealer_theme.py`, so the layout cannot drift.
- Changelog on the page grouped into meaningful entries; the version comes straight
  from `__manifest__.py`, so page and manifest cannot disagree (invariant 93).

### Added

- **This CHANGELOG.md.** The module never had one, although the line requires a
  per-module changelog — the store page carried the history, the repository did not.


## 19.0.1.1.0 — 2026-08

- Initial release: navy & gold palette across the backend (top bar, buttons, lists, tabs, breadcrumbs, pager). Pure CSS, no SCSS rebuild, no JS.
  Перший випуск: палітра navy & gold по всьому бекенду, чистим CSS.
