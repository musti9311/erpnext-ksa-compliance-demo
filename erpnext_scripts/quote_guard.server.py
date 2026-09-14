# Server Script: quote_guard  |  Before Validate  |  Purchase Order
# KSA control (GSA procurement rule): POs >= SAR 25,000 must be backed by a
# competitive supplier quotation. Fires at submit (docstatus==1) only, so
# drafting stays free — same semantics as vat_guard.
# AUDIT FIX (14-Sep e2e audit): threshold and coverage compare
# base_grand_total/base_net_total (company-currency SAR) — grand_total is in
# PO currency, a USD PO sailed 90k SAR under a 25k SAR threshold.
# The linked quotation must be from the SAME supplier and must cover the PO
# net value (presence-only check was launderable with an old 350-SAR quote).
# RestrictedPython sandbox: no imports; str.format BANNED — + and str() only.

if doc.company == "Al-Rehab Trading Est." and doc.docstatus == 1:
    if (doc.base_grand_total or 0) >= 25000:
        link = doc.get("custom_supplier_quotation")
        if not link:
            frappe.throw(
                "Cannot submit: PO value SAR " + str(doc.base_grand_total)
                + " is at or above the SAR 25,000 competitive-quote threshold. "
                "Link a Supplier Quotation in the 'Supplier Quotation' field "
                "before submitting."
            )
        sq = frappe.db.get_value(
            "Supplier Quotation", link,
            ["supplier", "docstatus", "base_net_total"], as_dict=True)
        if not sq:
            frappe.throw("Linked Supplier Quotation no longer exists.")
        if sq.docstatus != 1:
            frappe.throw(
                "Linked quotation " + str(link) + " is not submitted — a draft"
                " quote from the supplier can be fabricated; submit it first."
            )
        if sq.supplier != doc.supplier:
            frappe.throw(
                "Linked quotation " + str(link) + " belongs to " + str(sq.supplier)
                + ", not this PO's supplier " + str(doc.supplier)
                + ". Competitive quotes must be for the same vendor."
            )
        if (sq.base_net_total or 0) < (doc.base_net_total or 0):
            frappe.throw(
                "Linked quotation covers SAR " + str(sq.base_net_total)
                + " but this PO's net value is SAR " + str(doc.base_net_total)
                + " — the quote no longer covers the order (total changed after"
                " the quote was linked)."
            )
