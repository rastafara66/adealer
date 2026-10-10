/** @odoo-module **/
/*
 * The `barcode_handler` widget for Odoo 20, which no longer ships one.
 *
 * A scanner types like a keyboard; the standard `barcodes` module catches that and
 * fires `barcode_scanned`. The widget puts the code into the form field
 * `_barcode_scanned`, and the server onchange adds the product as a line
 * (`models/barcode_scan.py`). Odoo 18 and 19 have the same widget in `barcodes` —
 * then the standard one is registered and this one is not added at all (its module
 * loads later).
 *
 * The `barcode` service (not an OWL 3 plugin) — it exists in all three series.
 */
import { Component, xml } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useBus, useService } from "@web/core/utils/hooks";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { componentProps, declareProps } from "./owl_compat";

export class AdealerBarcodeHandlerField extends Component {
    static template = xml``;
    props = componentProps(this);

    setup() {
        const barcode = useService("barcode");
        useBus(barcode.bus, "barcode_scanned", (ev) => {
            this.props.record.update({ [this.props.name]: ev.detail.barcode });
        });
    }
}

declareProps(AdealerBarcodeHandlerField, { ...standardFieldProps });

const fields = registry.category("fields");
if (!fields.contains("barcode_handler")) {
    fields.add("barcode_handler", { component: AdealerBarcodeHandlerField });
}
