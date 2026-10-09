/** @odoo-module **/
/*
 * The same 3A-dealer JS on Odoo 18, 19 and 20 — checks what OWL can do, not the series.
 *
 * Odoo 18 and 19 run OWL 2, Odoo 20 runs OWL 3. For our components the difference is in
 * three places:
 *
 * - reactive state: OWL 2 has `useState`, OWL 3 has `proxy` (`useState` is gone);
 * - props: OWL 2 puts them into `this.props` itself, OWL 3 hands them out only through
 *   `useProps()`;
 * - props declaration: OWL 2 wants `static props` (a warning in debug mode without it),
 *   while the Odoo 20 compatibility layer FAILS on `static props` — and with the sidebar,
 *   which is always mounted, the whole interface would go down.
 *
 * Same idea as in Python ("by field presence"): one code base in three branches, the
 * 19.0 → series merge has no forks. Template expressions use `this.` (OWL 3 renders a
 * template with `{this: component}`; `this.x` works in OWL 2 as well).
 */
import * as owl from "@odoo/owl";

/** Reactive component state (call in `setup`). */
export const useReactive = owl.proxy || owl.useState;

/** Component props as a class field: `props = componentProps(this);` */
export function componentProps(component) {
    return owl.useProps ? owl.useProps() : component.props;
}

/** Props declaration — OWL 2 only: `declareProps(MyComponent, {...})` after the class. */
export function declareProps(ComponentClass, props) {
    if (!owl.useProps) {
        ComponentClass.props = props;
    }
}
