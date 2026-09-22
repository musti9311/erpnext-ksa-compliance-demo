# seed_demo.py — one-command demo rebuild on a BLANK site (frappe + erpnext + hrms).
# Proves every claim in the README without ERPNext expertise:
# fixtures -> company -> 3 installers -> VAT invoice -> workflow + quote-guard proof.
# Clearance itself is one extra line (needs the mock on the host):
#   bench --site <site> request --args '/api/method/zatca_submit?invoice=<name>'
# Run: copy erpnext_scripts/* to /tmp in the backend container, then:
#   bench --site <site> console, paste:  exec(open("/tmp/seed_demo.py").read())
# Re-runnable; each run adds one invoice + one PO (names increment, nothing breaks).
import frappe
from frappe.model.workflow import apply_workflow
from frappe.utils import add_days, today

if not getattr(frappe.local, "lang", None):
    frappe.local.lang = "en"  # bench console has no request language
frappe.set_user("Administrator")

HERE = "/tmp"  # erpnext_scripts/* copied in alongside this file
CO = "Al-Rehab Trading Est."
# console exec() runs in a cell namespace: nested functions CANNOT see
# exec-locals (NameError), only true globals. Anchor shared state on frappe.
frappe._seed = {"checks": []}
def check(label, ok, detail=""):
    frappe._seed["checks"].append(ok)
    print(("PASS" if ok else "FAIL"), label, "|", str(detail)[:120])

# ---- fixtures a blank site lacks (the demo instance grew these by hand) ----
for wt in ["Transit", "Stores"]:
    if not frappe.db.exists("Warehouse Type", wt):
        frappe.get_doc({"doctype": "Warehouse Type", "name": wt}).insert(ignore_permissions=True)
if not frappe.db.exists("Company", CO):
    frappe.get_doc({"doctype": "Company", "company_name": CO, "abbr": "ATE",
                    "default_currency": "SAR", "country": "Saudi Arabia",
                    "tax_id": "300000000000003",
                    "create_chart_based_on": "Standard Template"}).insert(ignore_permissions=True)
check("company", True, CO)
frappe.db.set_default("currency", "SAR")
frappe.db.set_value("Company", CO, "default_currency", "SAR")

def group_for(co, root):
    g = frappe.db.get_value("Account", {"company": co, "root_type": root, "is_group": 1,
                                        "account_name": ("like", "%Tax%")}, "name")
    return g or frappe.db.get_value("Account", {"company": co, "root_type": root,
                                                "is_group": 1}, "name")

for short, root, atype in [("VAT Input", "Asset", "Tax"), ("VAT Output", "Liability", "Tax")]:
    if not frappe.db.exists("Account", {"account_name": short, "company": CO}):
        frappe.get_doc({"doctype": "Account", "account_name": short, "company": CO,
                        "parent_account": group_for(CO, root),
                        "account_type": atype}).insert(ignore_permissions=True)
check("VAT accounts", True, "Input + Output")

def ensure_tree(dt, key, group, leaf, parent_field):
    if not frappe.db.exists(dt, group):
        frappe.get_doc({"doctype": dt, key: group, "is_group": 1}).insert(ignore_permissions=True)
    if not frappe.db.exists(dt, leaf):
        frappe.get_doc({"doctype": dt, key: leaf, "is_group": 0,
                        parent_field: group}).insert(ignore_permissions=True)

ensure_tree("Customer Group", "customer_group_name", "All Customer Groups",
            "Replay Customers", "parent_customer_group")
ensure_tree("Territory", "territory_name", "All Territories",
            "Replay Territory", "parent_territory")
ensure_tree("Supplier Group", "supplier_group_name", "All Supplier Groups",
            "Replay Suppliers", "parent_supplier_group")
for dt, name, extra in [
    ("Customer", "Test Customer", {"customer_group": "Replay Customers",
                                  "territory": "Replay Territory", "customer_name": "Test Customer"}),
    ("Supplier", "Test Supplier", {"supplier_group": "Replay Suppliers",
                                  "supplier_name": "Test Supplier"}),
]:
    if not frappe.db.exists(dt, name):
        frappe.get_doc(dict({"doctype": dt}, **extra)).insert(ignore_permissions=True)
if not frappe.db.exists("UOM", "Nos"):
    frappe.get_doc({"doctype": "UOM", "uom_name": "Nos"}).insert(ignore_permissions=True)
if not frappe.db.exists("Item Group", "Replay Items"):
    frappe.get_doc({"doctype": "Item Group", "item_group_name": "Replay Items", "is_group": 0,
                    "parent_item_group": frappe.db.get_value("Item Group", {"is_group": 1},
                                                             "name")}).insert(ignore_permissions=True)
if not frappe.db.exists("Item", "Test Service"):
    frappe.get_doc({"doctype": "Item", "item_code": "Test Service", "item_group": "Replay Items",
                    "stock_uom": "Nos", "is_stock_item": 0,
                    "is_sales_item": 1, "is_purchase_item": 1}).insert(ignore_permissions=True)
for email, roles in [("r1@replay.test", ["Purchase User"]),
                     ("r2@replay.test", ["Purchase User", "Purchase Manager", "Accounts Manager"])]:
    if not frappe.db.exists("User", email):
        frappe.get_doc({"doctype": "User", "email": email, "first_name": email.split("@")[0],
                        "enabled": 1}).insert(ignore_permissions=True)
    frappe.get_doc("User", email).add_roles(*roles)
check("fixtures", True, "customer/supplier/item/users")
# passwords: bench set-password (update_password kills v16 hashes — see DECISIONS.md)

if not frappe.db.exists("Fiscal Year", "2026"):
    frappe.get_doc({"doctype": "Fiscal Year", "year": "2026",
                    "year_start_date": "2026-01-01",
                    "year_end_date": "2026-12-31"}).insert(ignore_permissions=True)
fy = frappe.get_doc("Fiscal Year", "2026")
if CO not in [d.company for d in fy.companies]:
    fy.append("companies", {"company": CO})
    fy.save(ignore_permissions=True)
if not frappe.db.exists("Price List", "Standard Selling"):
    frappe.get_doc({"doctype": "Price List", "price_list_name": "Standard Selling",
                    "currency": "SAR", "selling": 1}).insert(ignore_permissions=True)
inc = frappe.db.get_value("Account", {"company": CO, "root_type": "Income", "is_group": 0}, "name")
it = frappe.get_doc("Item", "Test Service")
if CO not in [d.company for d in it.item_defaults]:
    it.append("item_defaults", {"company": CO, "income_account": inc})
    it.save(ignore_permissions=True)

# ---- the three installers (module-level only: safe under console exec) ----
exec(open(HERE + "/zatca_install.py").read())
exec(open(HERE + "/m3_install.py").read())
exec(open(HERE + "/m4_install.py").read())
# fresh scripts are invisible to this long-running console process until the
# script map cache is dropped — without this, guards silently never fire here
frappe.clear_cache()
frappe.set_user("Administrator")
check("installers", all([
    frappe.db.exists("Custom Field", {"dt": "Sales Invoice", "fieldname": "custom_zatca_status"}),
    frappe.db.exists("Server Script", "zatca_submit"),
    frappe.db.exists("Server Script", "quote_guard"),
    frappe.db.exists("Workflow", "KSA PO Approval"),
    frappe.db.exists("Notification", "KSA Iqama Expiry Alert"),
    frappe.db.exists("Report", "GOSI Monthly Contribution Register"),
    frappe.db.exists("Leave Type", "Hajj Leave"),
]), "fields/scripts/workflow/notification/reports/leave")

# ---- VAT invoice (template rows copied explicitly: server insert skips them) ----
tpl = frappe.db.get_value("Sales Taxes and Charges Template",
                          {"title": "VAT 15%", "company": CO}, "name")
trows = [{"charge_type": r.charge_type, "account_head": r.account_head,
          "description": r.description, "rate": r.rate}
         for r in frappe.get_doc("Sales Taxes and Charges Template", tpl).taxes]
inv = frappe.get_doc({"doctype": "Sales Invoice", "customer": "Test Customer", "company": CO,
                      "posting_date": today(),
                      "items": [{"item_code": "Test Service", "qty": 1, "rate": 1000}],
                      "taxes_and_charges": tpl, "taxes": trows})
inv.insert(ignore_permissions=True)
inv.submit()
check("VAT invoice", inv.total_taxes_and_charges == 150.0,
      inv.name + " total=" + str(inv.grand_total) + " vat=" + str(inv.total_taxes_and_charges))

# ---- M4 proof: 36k quoteless PO walks the real chain, dies at Final Approve ----
frappe.set_user("r1@replay.test")
po = frappe.get_doc({"doctype": "Purchase Order", "supplier": "Test Supplier", "company": CO,
                     "schedule_date": add_days(today(), 60),
                     "items": [{"item_code": "Test Service", "qty": 36, "rate": 1000,
                                "schedule_date": add_days(today(), 60)}]})
po.insert(ignore_permissions=True)
apply_workflow(po, "Request Approval")
frappe.set_user("r2@replay.test")
apply_workflow(po, "Manager Approve")
po.reload()
try:
    apply_workflow(po, "Final Approve")
    check("quote guard", False, "PO slipped through")
except Exception as e:
    check("quote guard", "competitive-quote" in str(e), po.name + " stopped: " + str(e)[:100])

frappe.db.commit()
print("==== SUMMARY ====")
n = len(frappe._seed["checks"])
print(str(sum(frappe._seed["checks"])) + "/" + str(n) + " checks passed")
print("NEXT: clear the invoice against the mock (mock must run on the host first):")
print("  bench --site <site> request --args '/api/method/zatca_submit?invoice=" + inv.name + "'")
