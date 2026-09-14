# Server Script: po_match_guard  |  Before Validate  |  Purchase Invoice
# KSA control: three-way-match first leg — no supplier invoice without a
# Purchase Order. Closes the "pay a random invoice" fraud.
# AUDIT FIX (14-Sep e2e audit): EVERY priced line must carry a PO link.
# The old any()-style check let a SAR 35 token line launder a SAR 375,000
# unlinked line on the same invoice.
# Fires at submit only (drafting free); matches vat_guard/quote_guard style.
# RestrictedPython sandbox: no imports; str.format BANNED — + and str() only.

if doc.company == "Al-Rehab Trading Est." and doc.docstatus == 1:
    unlinked = 0
    for it in (doc.items or []):
        if (it.amount or 0) and not it.purchase_order:
            unlinked += 1
    if unlinked:
        frappe.throw(
            "Cannot submit: " + str(unlinked) + " of " + str(len(doc.items or []))
            + " invoice line(s) have no Purchase Order link. Policy: supplier"
            " bills are booked against an approved PO only — use Create >"
            " Purchase Invoice from the PO, or each line must reference its PO."
        )
