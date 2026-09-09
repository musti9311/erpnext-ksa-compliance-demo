# DocType Event — vat_guard
if doc.company == "Al-Rehab Trading Est." and not doc.taxes_and_charges:
    if doc.docstatus == 1:
        frappe.throw(
            "Cannot submit: no VAT applied. "
            "Pick 'VAT 15% - ATE' in Sales Taxes and Charges Template."
        )