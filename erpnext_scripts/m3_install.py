# M3 installer (idempotent, safe to re-run). Creates if missing:
#  1. Employee KSA fields (iqama_number, iqama_expiry, nationality)
#  2. Server Scripts: employer_gosi + eosb_accrue (API)
#  3. Notification: KSA Iqama Expiry Alert (30 days, to HR Manager)
#  4. Query Reports: GOSI register + EOSB register (from *.sql files)
#  5. KSA Leave Types: Annual 21 / Hajj 10 / Maternity 70d / Paternity 3d
# Run: copy this file + employer_gosi.server.py + eosb_accrue.server.py +
# gosi_register.sql + eosb_register.sql to /tmp inside the backend
# container, then:  bench --site frontend console
# and paste:  exec(open("/tmp/m3_install.py").read())
import frappe

if not getattr(frappe.local, "lang", None):
    frappe.local.lang = "en"  # bench console has no request language; avoids a locale crash

HERE = "/tmp"  # scripts copied in alongside this file

# 1. employee fields
for fieldname, label, fieldtype, options in [
    ("iqama_number", "Iqama Number", "Data", None),
    ("iqama_expiry", "Iqama Expiry", "Date", None),
    ("nationality", "Country", "Link", "Country"),
]:
    if frappe.db.exists("Custom Field", {"dt": "Employee", "fieldname": fieldname}):
        print(fieldname, "exists")
        continue
    doc = {"doctype": "Custom Field", "dt": "Employee", "fieldname": fieldname,
           "label": label, "fieldtype": fieldtype}
    if options:
        doc["options"] = options
    frappe.get_doc(doc).insert(ignore_permissions=True)
    print(fieldname, "created")

# 2. server scripts (HRMS gap patches — see DECISIONS.md 2026-09-13)
for name, fname in [("employer_gosi", "employer_gosi.server.py"),
                    ("eosb_accrue", "eosb_accrue.server.py")]:
    script = open("%s/%s" % (HERE, fname)).read()
    if script.startswith("# "):
        script = script.split("\n", 1)[1]
    if frappe.db.exists("Server Script", name):
        d = frappe.get_doc("Server Script", name)
        d.script = script
        d.save(ignore_permissions=True)
        print(name, "updated")
    else:
        frappe.get_doc({"doctype": "Server Script", "name": name, "script_name": name,
                        "script_type": "API", "api_method": name,
                        "script": script}).insert(ignore_permissions=True)
        print(name, "created")

# 3. iqama expiry notification (clean ASCII message; the live instance's copy
# carries a mojibake dash from a docs paste — this is the fixed text)
if frappe.db.exists("Notification", "KSA Iqama Expiry Alert"):
    print("notification exists")
else:
    frappe.get_doc({"doctype": "Notification", "name": "KSA Iqama Expiry Alert",
                    "document_type": "Employee", "event": "Days Before",
                    "days_in_advance": 30, "date_changed": "iqama_expiry",
                    "channel": "System Notification", "enabled": 1,
                    "subject": "Iqama expiring: {{ doc.employee_name }}",
                    "message": "<p><strong>Iqama expiring soon</strong></p>"
                               "<p>{{ doc.employee_name }} ({{ doc.name }}) - Iqama "
                               "{{ doc.iqama_number or '-' }} expires "
                               "<strong>{{ doc.iqama_expiry }}</strong>. "
                               "Start renewal now.</p>",
                    "recipients": [{"receiver_by_role": "HR Manager"}]}
                   ).insert(ignore_permissions=True)
    print("notification created")

# 3b. Arabic twin (same trigger, MSA wording in standard portal vocabulary)
if frappe.db.exists("Notification", "KSA Iqama Expiry Alert AR"):
    print("AR notification exists")
else:
    frappe.get_doc({"doctype": "Notification", "name": "KSA Iqama Expiry Alert AR",
                    "document_type": "Employee", "event": "Days Before",
                    "days_in_advance": 30, "date_changed": "iqama_expiry",
                    "channel": "System Notification", "enabled": 1,
                    "subject": "اقتراب انتهاء الإقامة: {{ doc.employee_name }}",
                    "message": "<p><strong>الإقامة على وشك الانتهاء</strong></p>"
                               "<p>{{ doc.employee_name }} ({{ doc.name }}) - رقم الإقامة "
                               "{{ doc.iqama_number or '-' }} تنتهي في "
                               "<strong>{{ doc.iqama_expiry }}</strong>. "
                               "يرجى بدء التجديد الآن.</p>",
                    "recipients": [{"receiver_by_role": "HR Manager"}]}
                   ).insert(ignore_permissions=True)
    print("AR notification created")

# 4. query reports (query = .sql file minus the -- filter header lines)
REPORTS = [
    ("GOSI Monthly Contribution Register", "Salary Slip", "gosi_register.sql",
     [("from_date", "Date", None, None), ("end_date", "Date", None, None)]),
    ("KSA EOSB Liability Register", "Employee", "eosb_register.sql",
     [("as_of", "Date", None, None), ("company", "Link", "Company", "Al-Rehab Trading Est.")]),
]
for rname, ref, fname, filters in REPORTS:
    if frappe.db.exists("Report", rname):
        print(rname, "exists")
        continue
    lines = [ln for ln in open("%s/%s" % (HERE, fname)).read().splitlines()
             if not ln.strip().startswith("--")]
    frappe.get_doc({"doctype": "Report", "report_name": rname, "ref_doctype": ref,
                    "report_type": "Query Report", "is_standard": "No",
                    "query": "\n".join(lines).strip(),
                    "filters": [{"fieldname": fn, "label": fn.replace("_", " ").title(),
                                 "fieldtype": ft, "options": op or "",
                                 "default": df or ""}
                                for fn, ft, op, df in filters]}
                   ).insert(ignore_permissions=True)
    print(rname, "created")

# 5. KSA leave types (values verified live 2026-09-21)
for lt, max_leaves, after, carry in [
    ("Annual Leave", 21, 0, 1),
    ("Hajj Leave", 10, 730, 0),
    ("Maternity Leave", 70, 0, 0),
    ("Paternity Leave", 3, 0, 0),
]:
    if frappe.db.exists("Leave Type", lt):
        print(lt, "exists")
        continue
    frappe.get_doc({"doctype": "Leave Type", "leave_type_name": lt,
                    "max_leaves_allowed": max_leaves, "applicable_after": after,
                    "is_carry_forward": carry}).insert(ignore_permissions=True)
    print(lt, "created")

frappe.db.commit()
print("INSTALL DONE")
