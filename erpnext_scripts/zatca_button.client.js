#  — zatca_button
frappe.ui.form.on("Sales Invoice", {
    refresh(frm) {
        if (frm.doc.docstatus === 1 &&
            !["Cleared", "Reported"].includes(frm.doc.custom_zatca_status)) {
            frm.add_custom_button("Submit to ZATCA", () => {
                frappe.call({
                    method: "zatca_submit",
                    args: { invoice: frm.doc.name },
                    freeze: true,
                    callback(r) {
                        const st = r.message.result.status;
                        frm.reload_doc();
                        frappe.show_alert({
                            message: st === "OK" || st === "ALREADY_CLEARED"
                                ? "ZATCA clearance: CLEARED"
                                : "ZATCA clearance: REJECTED — see status",
                            indicator: st === "OK" || st === "ALREADY_CLEARED" ? "green" : "red"
                        });
                    }
                });
            });
        }
    }
});