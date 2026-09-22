# ZATCA installer (idempotent, safe to re-run). Creates if missing:
#  1. 6 custom_zatca_* fields on Sales Invoice
#  2. Server Scripts: zatca_submit (API), vat_guard (Sales Invoice, Before Validate)
#  3. Client Script: zatca_button on Sales Invoice
#  4. Print Formats: ZATCA Phase 1 Invoice (EN evidence) + ZATCA Bilingual Invoice
#     (AR/EN, per-invoice QR from custom_zatca_qr_image; no slash in the name —
#     slashes break the print-view format selector)
#  5. Sales VAT 15% template (needs a VAT Output account in the CoA first)
# Run: copy this file + zatca_submit.server.py + vat_guard.server.py +
# zatca_button.client.js + zatca_print_format.html + zatca_print_format_ar.html
# to /tmp inside the backend container, then:  bench --site frontend console
# and paste:  exec(open("/tmp/zatca_install.py").read())
import frappe

if not getattr(frappe.local, "lang", None):
    frappe.local.lang = "en"  # bench console has no request language; avoids a locale crash

HERE = "/tmp"  # scripts copied in alongside this file

# 1. custom fields on Sales Invoice (no insert_after: anchors differ per site;
# Frappe appends at the end, which is fine for a demo)
FIELDS = [
    ("custom_zatca_status", "ZATCA Status", "Select",
     "Not Submitted\nPending\nCleared\nReported\nFailed", None),
    ("custom_zatca_uuid", "ZATCA UUID", "Data", None, None),
    ("custom_zatca_invoice_hash", "ZATCA Invoice Hash", "Data", None, None),
    ("custom_zatca_previous_hash", "ZATCA Previous Hash", "Data", None, None),
    ("custom_zatca_submitted_at", "ZATCA Submitted At", "Data", None, None),
    ("custom_zatca_qr_image", "ZATCA QR Image", "Long Text", None, None),
]
for fieldname, label, fieldtype, options, after in FIELDS:
    if frappe.db.exists("Custom Field", {"dt": "Sales Invoice", "fieldname": fieldname}):
        print(fieldname, "exists")
        continue
    doc = {"doctype": "Custom Field", "dt": "Sales Invoice", "fieldname": fieldname,
           "label": label, "fieldtype": fieldtype}
    if options:
        doc["options"] = options
    if after:
        doc["insert_after"] = after
    frappe.get_doc(doc).insert(ignore_permissions=True)
    print(fieldname, "created")

# 2. server scripts (body refreshed from repo files; events left alone if edited)
SCRIPTS = {
    "zatca_submit": ("zatca_submit.server.py", "API", None, None),
    "vat_guard": ("vat_guard.server.py", "DocType Event", "Sales Invoice", "Before Validate"),
}
for name, (fname, stype, doctype, event) in SCRIPTS.items():
    script = open("%s/%s" % (HERE, fname)).read()
    if script.startswith("# "):
        script = script.split("\n", 1)[1]
    if frappe.db.exists("Server Script", name):
        d = frappe.get_doc("Server Script", name)
        d.script = script
        d.save(ignore_permissions=True)
        print(name, "updated")
    else:
        doc = {"doctype": "Server Script", "name": name, "script_name": name,
               "script_type": stype, "script": script}
        if stype == "API":
            doc["api_method"] = name
        else:
            doc["reference_doctype"] = doctype
            doc["doctype_event"] = event
        frappe.get_doc(doc).insert(ignore_permissions=True)
        print(name, "created")

# 3. client script
button = open("%s/zatca_button.client.js" % HERE).read()
if button.startswith("# "):
    button = button.split("\n", 1)[1]
if frappe.db.exists("Client Script", "zatca_button"):
    d = frappe.get_doc("Client Script", "zatca_button")
    d.script = button
    d.save(ignore_permissions=True)
    print("zatca_button updated")
else:
    frappe.get_doc({"doctype": "Client Script", "name": "zatca_button",
                    "dt": "Sales Invoice", "enabled": 1,
                    "script": button}).insert(ignore_permissions=True)
    print("zatca_button created")

# 4. print formats (QR embedded as data-URI; container wkhtmltopdf can't fetch
# internal URLs — see DECISIONS.md)
for pf_name, pf_file in [("ZATCA Phase 1 Invoice", "zatca_print_format.html"),
                         ("ZATCA Bilingual Invoice", "zatca_print_format_ar.html")]:
    if frappe.db.exists("Print Format", pf_name):
        print(pf_name, "exists")
        continue
    html = open("%s/%s" % (HERE, pf_file)).read()
    frappe.get_doc({"doctype": "Print Format", "name": pf_name,
                    "doc_type": "Sales Invoice", "module": "Accounts",
                    "print_format_type": "Jinja", "standard": "No",
                    "html": html}).insert(ignore_permissions=True)
    print(pf_name, "created")

# 5. sales VAT template
if frappe.db.exists("Sales Taxes and Charges Template", {"title": "VAT 15%"}):
    print("VAT template exists")
else:
    acct = frappe.db.get_value("Account", {"account_name": "VAT Output",
                                           "company": "Al-Rehab Trading Est."}, "name")
    if not acct:
        acct = frappe.db.get_value("Account", {"company": "Al-Rehab Trading Est.",
                                               "account_name": ("like", "%VAT%")}, "name")
    frappe.get_doc({"doctype": "Sales Taxes and Charges Template", "title": "VAT 15%",
                    "company": "Al-Rehab Trading Est.",
                    "taxes": [{"account_head": acct, "description": "VAT Output",
                               "rate": 15, "charge_type": "On Net Total",
                               "included_in_print_rate": 0}]}).insert(ignore_permissions=True)
    print("VAT template created with account:", acct)

frappe.db.commit()
print("INSTALL DONE")
