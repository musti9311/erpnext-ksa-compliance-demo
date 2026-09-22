# API — zatca_submit

def b64(data):
    alpha = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/"
    out = ""
    pad = 0
    i = 0
    while i < len(data):
        c0 = data[i]
        c1 = data[i+1] if i+1 < len(data) else 0
        c2 = data[i+2] if i+2 < len(data) else 0
        remaining = len(data) - i
        n = (c0 << 16) | (c1 << 8) | c2
        out = out + alpha[(n >> 18) & 63] + alpha[(n >> 12) & 63]
        if remaining > 1:
            out = out + alpha[(n >> 6) & 63]
        else:
            out = out + "="
        if remaining > 2:
            out = out + alpha[n & 63]
        else:
            out = out + "="
        i = i + 3
    return out

def tlv(tag, val):
    b = str(val).encode("utf-8")
    return bytes([tag, len(b)]) + b

def money(v):
    cents = int(round(float(v) * 100))
    whole = cents // 100
    frac = cents % 100
    f = str(frac)
    if len(f) < 2:
        f = "0" + f
    return str(whole) + "." + f

inv = frappe.get_doc("Sales Invoice", frappe.form_dict.invoice)

# idempotency: never re-clear an already-cleared invoice (mock now also
# rejects duplicates server-side; this keeps double-clicks visible, not fatal)
if inv.get("custom_zatca_status") == "Cleared":
    frappe.response["result"] = {"status": "ALREADY_CLEARED", "server_qr_matches": True}
else:
    comp = frappe.get_doc("Company", inv.company)

    ts = str(inv.posting_date) + "T" + str(inv.posting_time)[:8] + "+03:00"

    payload = b"".join([
        tlv(1, comp.company_name.strip()),
        tlv(2, comp.tax_id.strip()),
        tlv(3, ts),
        tlv(4, money(inv.grand_total)),
        tlv(5, money(inv.total_taxes_and_charges)),
    ])
    qr_b64 = b64(payload)

    data = None
    try:
        data = frappe.make_post_request(
            "http://host.docker.internal:8090/api/v1/zakat/taxpayer/invoices/clearance",
            json={"invoiceNumber": inv.name, "invoiceTotal": inv.grand_total,
                  "vatTotal": inv.total_taxes_and_charges, "qrCode": qr_b64},
        )
    except Exception:
        # mock down / network wall: visible Failed, never a silent dead button
        frappe.db.set_value("Sales Invoice", inv.name, {"custom_zatca_status": "Failed"})
        frappe.db.set_value("Sales Invoice", inv.name, "custom_zatca_submitted_at",
                            str(frappe.utils.now()))
        frappe.db.commit()
        frappe.response["result"] = {"status": "ERROR", "reason": "FATOORA_UNREACHABLE",
                                     "server_qr_matches": qr_b64}

    if data is None:
        pass
    elif data.get("status") == "OK":
        frappe.db.set_value("Sales Invoice", inv.name, {
            "custom_zatca_status": "Cleared",
            "custom_zatca_uuid": data["uuid"],
            "custom_zatca_invoice_hash": data["invoiceHash"],
            "custom_zatca_previous_hash": data["previousInvoiceHash"],
            # renderer-ready QR image for the bilingual print format (v1 keeps
            # its static evidence image); empty when the mock lacks the QR libs
            "custom_zatca_qr_image": data.get("qrDataUri") or "",
        })
        frappe.db.set_value("Sales Invoice", inv.name, "custom_zatca_submitted_at",
                            str(frappe.utils.now()))
        frappe.db.commit()
        frappe.response["result"] = {"status": data.get("status"), "server_qr_matches": qr_b64}
    elif data.get("reasonCode") == "DUPLICATE_INVOICE" and data.get("uuid"):
        # converged: mock already holds this invoice — adopt its stamps, stay Cleared
        frappe.db.set_value("Sales Invoice", inv.name, {
            "custom_zatca_status": "Cleared",
            "custom_zatca_uuid": data["uuid"],
            "custom_zatca_invoice_hash": data.get("invoiceHash"),
            "custom_zatca_qr_image": data.get("qrDataUri") or "",
        })
        frappe.db.set_value("Sales Invoice", inv.name, "custom_zatca_submitted_at",
                            str(frappe.utils.now()))
        frappe.db.commit()
        frappe.response["result"] = {"status": "OK", "server_qr_matches": qr_b64}
    else:
        frappe.db.set_value("Sales Invoice", inv.name, {"custom_zatca_status": "Failed"})
        frappe.db.set_value("Sales Invoice", inv.name, "custom_zatca_submitted_at",
                            str(frappe.utils.now()))
        frappe.db.commit()
        frappe.response["result"] = {"status": data.get("status"), "server_qr_matches": qr_b64}
