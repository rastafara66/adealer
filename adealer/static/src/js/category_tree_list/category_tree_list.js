/** @odoo-module **/

import { onWillStart, onWillUpdateProps, useState } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { CharField, charField } from "@web/views/fields/char/char_field";
import { listView } from "@web/views/list/list_view";
import { ListRenderer } from "@web/views/list/list_renderer";

// Поле, за яким групування показується деревом, і модель груп.
const TREE_FIELD = "categ_id";
const NO_ICON_CLOSED = "fa-folder-o";
const NO_ICON_OPEN = "fa-folder-open-o";

/**
 * Список товарів, у якому групування за групою товару — ДЕРЕВО: вкладені групи
 * всередині батьківських, як теки довідника номенклатури в 1С, згорнуті.
 *
 * Штатний список Odoo групує пласко: «Запчастини / Фільтри / Масляні» — одна
 * група з повним шляхом, і групи без власних товарів не видно взагалі. Тут
 * дані беруться ті самі (Odoo групує за `categ_id` як завжди), а дерево
 * складається вже при показі — з батьків кожної групи. Тому:
 *
 * * група, де є і власні товари, і підгрупи, показує спершу підгрупи, а
 *   під ними свої товари — як тека в 1С;
 * * група без власних товарів (лише підгрупи) — вузол без даних, його
 *   розгорнутість живе тут, а не в моделі;
 * * лічильник групи — разом із підгрупами.
 */
export class CategoryTreeListRenderer extends ListRenderer {
    static rowsTemplate = "adealer.CategoryTreeRows";

    setup() {
        super.setup();
        // Розгорнуті вузли БЕЗ власних товарів: {ключ: true|false}. Вузли з
        // власними товарами розгортає сама група моделі (вона ж і пам'ятає).
        this.treeState = useState({ open: {} });
        this.categories = null;
        onWillStart(() => this.loadCategories(this.props));
        onWillUpdateProps((nextProps) => this.loadCategories(nextProps));
    }

    isTreeGrouped(list) {
        return (
            list.isGrouped &&
            list.groupBy.length === 1 &&
            list.groupBy[0].split(":")[0] === TREE_FIELD
        );
    }

    /** Чи малювати `list` деревом: лише корінь, згрупований за групою товару. */
    isTreeList(list) {
        return list === this.props.list && this.isTreeGrouped(list);
    }

    async loadCategories(props) {
        const list = props.list;
        if (!this.isTreeGrouped(list) || !list.fields[TREE_FIELD]) {
            return;
        }
        // Групу, створену після завантаження, дерево ще не знає — тоді перечитати.
        const known = this.categories;
        if (known && list.groups.every((g) => !g.value || known[g.value])) {
            return;
        }
        const rows = await this.orm.searchRead(
            list.fields[TREE_FIELD].relation,
            [],
            ["name", "parent_id", "adealer_icon"]
        );
        const categories = {};
        for (const row of rows) {
            categories[row.id] = {
                name: row.name,
                parentId: row.parent_id && row.parent_id[0],
                icon: row.adealer_icon || "",
            };
        }
        this.categories = categories;
    }

    /** Корені дерева: вузли з дітьми й групою (якщо в групі є свої товари). */
    get categoryTree() {
        const categories = this.categories || {};
        const nodes = {};
        const roots = [];
        const nodeOf = (id) => {
            if (nodes[id]) {
                return nodes[id];
            }
            const category = categories[id];
            const node = {
                key: `c${id}`,
                name: category ? category.name : "",
                icon: category ? category.icon : "",
                children: [],
                group: null,
                count: 0,
            };
            nodes[id] = node;
            const parentId = category && category.parentId;
            if (parentId && categories[parentId]) {
                nodeOf(parentId).children.push(node);
            } else {
                roots.push(node);
            }
            return node;
        };
        let withoutGroup = null;
        for (const group of this.props.list.groups) {
            if (!group.value) {
                withoutGroup = {
                    key: "none",
                    name: _t("No group"),
                    icon: "",
                    children: [],
                    group,
                    count: 0,
                };
                continue;
            }
            const node = nodeOf(group.value);
            if (!node.name) {
                node.name = group.displayName; // дерево ще не знає групу — повний шлях
            }
            node.group = group;
        }
        const total = (node) => {
            node.count =
                (node.group ? node.group.count : 0) +
                node.children.reduce((sum, child) => sum + total(child), 0);
            return node.count;
        };
        const byName = (a, b) =>
            a.name.localeCompare(b.name, undefined, { numeric: true, sensitivity: "base" });
        const sortTree = (list) => {
            list.sort(byName);
            list.forEach((node) => sortTree(node.children));
        };
        roots.forEach(total);
        sortTree(roots);
        if (withoutGroup) {
            total(withoutGroup);
            roots.push(withoutGroup);
        }
        return roots;
    }

    /**
     * Чи розгорнутий вузол. Вузол із власними товарами — як його група в
     * моделі. Вузол без них — як його розгорнули тут; а поки його не чіпали
     * (повернулись зі сторінки товару, і дерево складено заново) — розгорнутий,
     * якщо всередині є розгорнута група: інакше відкрита раніше гілка
     * сховалась би за згорнутим батьком.
     */
    isNodeOpen(node) {
        if (node.group) {
            return !node.group.isFolded;
        }
        const own = this.treeState.open[node.key];
        if (own !== undefined) {
            return own;
        }
        return node.children.some((child) => this.isNodeOpen(child));
    }

    /** Рядки для показу: вузли й товари розгорнутих груп, по порядку. */
    get treeRows() {
        const rows = [];
        const walk = (nodes, level) => {
            for (const node of nodes) {
                const open = this.isNodeOpen(node);
                rows.push({ type: "node", key: node.key, node, level, open });
                if (!open) {
                    continue;
                }
                walk(node.children, level + 1);
                if (node.group && !node.group.isFolded) {
                    rows.push({ type: "records", key: `${node.key}_records`, group: node.group });
                }
            }
        };
        walk(this.categoryTree, 0);
        return rows;
    }

    nodeIcon(row) {
        return row.node.icon || (row.open ? NO_ICON_OPEN : NO_ICON_CLOSED);
    }

    async onNodeClicked(node) {
        const left = await this.props.list.leaveEditMode();
        if (!left) {
            return;
        }
        if (node.group) {
            await node.group.toggle();
            return;
        }
        this.treeState.open[node.key] = !this.isNodeOpen(node);
    }
}

export const categoryTreeListView = {
    ...listView,
    Renderer: CategoryTreeListRenderer,
};

registry.category("views").add("adealer_category_tree_list", categoryTreeListView);

/** Поле «Іконка» групи: сама іконка поруч із назвою класу Font Awesome. */
export class FaIconField extends CharField {
    static template = "adealer.FaIconField";
}

registry.category("fields").add("adealer_fa_icon", {
    ...charField,
    component: FaIconField,
});
