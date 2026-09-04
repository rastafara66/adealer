# Changelog — 3A-dealer Theme (`adealer_theme`)

Navy & gold backend theme for Odoo. Newest on top.
Тема оформлення бекенду. Найновіше — зверху.

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
