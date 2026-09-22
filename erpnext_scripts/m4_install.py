# M4 installer (idempotent, safe to re-run). Creates if missing:
#  1. custom_supplier_quotation (Link -> Supplier Quotation) on Purchase Order
#  2. Server Scripts: quote_guard, po_match_guard, bank_change_audit,
#     po_submit_gate, pending_freeze
#  3. Purchase VAT 15% template (none exists yet)
#  4. Workflow: KSA PO Approval (10k two-level + 25k quote legs live in scripts)
#  5. Passwords for Kareem + Amina (demo123) so the chain can be acted out
import frappe

if not getattr(frappe.local, "lang", None):
    frappe.local.lang = "en"  # bench console has no request language; avoids a locale crash

HERE = "/tmp"  # scripts copied in alongside this file
SFILE = {
    "quote_guard": "quote_guard.server.py",
    "po_match_guard": "po_match_guard.server.py",
    "bank_change_audit": "bank_change_audit.server.py",
    "po_submit_gate": "po_submit_gate.server.py",
    "pending_freeze": "pending_freeze.server.py",
}
DOCTY = {"quote_guard": "Purchase Order", "po_match_guard": "Purchase Invoice",
         "bank_change_audit": "Supplier", "po_submit_gate": "Purchase Order",
         "pending_freeze": "Purchase Order"}
EVENT = {"quote_guard": "Before Validate", "po_match_guard": "Before Validate",
         "bank_change_audit": "After Save", "po_submit_gate": "Before Validate",
         "pending_freeze": "Before Save"}

# 1. custom field on PO
if not frappe.db.exists("Custom Field", {"dt": "Purchase Order", "fieldname": "custom_supplier_quotation"}):
    frappe.get_doc({
        "doctype": "Custom Field",
        "dt": "Purchase Order",
        "fieldname": "custom_supplier_quotation",
        "label": "Supplier Quotation",
        "fieldtype": "Link",
        "options": "Supplier Quotation",
        "description": "Required for POs >= SAR 25,000 (competitive-quote control)",
        "insert_after": "supplier_name",
    }).insert(ignore_permissions=True)
    print("CF created")
else:
    print("CF exists")

# 2. server scripts from files
for name, fname in SFILE.items():
    script = open(f"{HERE}/{fname}").read()
    if frappe.db.exists("Server Script", name):
        d = frappe.get_doc("Server Script", name)
        d.script = script
        if frappe.db.get_value("Server Script", name, "modified") == frappe.db.get_value("Server Script", name, "creation"):
            d.doctype_event = EVENT[name]  # fix only a never-edited wrong default
        d.save(ignore_permissions=True)
        print(name, "updated")
    else:
        frappe.get_doc({
            "doctype": "Server Script",
            "name": name,
            "script_name": name,
            "script_type": "DocType Event",
            "reference_doctype": DOCTY[name],
            "doctype_event": EVENT[name],
            "script": script,
        }).insert(ignore_permissions=True)
        print(name, "created")

# 3. purchase VAT template
if not frappe.db.exists("Purchase Taxes and Charges Template", {"title": "VAT 15% - ATE"}):
    acct = frappe.db.get_value("Account", {"account_name": "Input VAT Recoverable", "company": "Al-Rehab Trading Est."}, "name")
    if not acct:
        # prefer an Input-side account — bare %VAT% can return VAT Output first
        acct = frappe.db.get_value("Account", {"company": "Al-Rehab Trading Est.", "account_name": ("like", "%Input%")}, "name")
    if not acct:
        # find any VAT-ish payable account
        acct = frappe.db.get_value("Account", {"company": "Al-Rehab Trading Est.", "account_name": ("like", "%VAT%")}, "name")
    frappe.get_doc({
        "doctype": "Purchase Taxes and Charges Template",
        "title": "VAT 15% - ATE",
        "company": "Al-Rehab Trading Est.",
        "taxes": [{
            "account_head": acct,
            "description": "VAT 15%",
            "rate": 15,
            "category": "Total",
        }],
    }).insert(ignore_permissions=True)
    print("VAT template created with account:", acct)
else:
    print("VAT template exists")

# 4. workflow (thresholds in BASE currency — the audit's worst find; see DECISIONS.md)
# Workflow states/actions are Link masters — create them first or the
# workflow insert dies with "Could not find Row #1: State: ..." (found on
# a real fresh-site replay 2026-09-22).
for st, style in [("Draft", ""), ("Pending Manager Approval", ""),
                  ("Pending Accountant Approval", ""), ("Approved", "Success"),
                  ("Rejected", "Danger")]:
    if frappe.db.exists("Workflow State", st):
        continue
    frappe.get_doc({"doctype": "Workflow State",
                    "workflow_state_name": st, "style": style}).insert(ignore_permissions=True)
    print("state", st, "created")
for act in ["Request Approval", "Direct Approve", "Manager Approve", "Final Approve", "Reject"]:
    if frappe.db.exists("Workflow Action Master", act):
        continue
    frappe.get_doc({"doctype": "Workflow Action Master",
                    "workflow_action_name": act}).insert(ignore_permissions=True)
    print("action", act, "created")
if frappe.db.exists("Workflow", "KSA PO Approval"):
    print("workflow exists")
else:
    frappe.get_doc({"doctype": "Workflow", "workflow_name": "KSA PO Approval",
                    "document_type": "Purchase Order", "is_active": 1,
                    "workflow_state_field": "workflow_state",
                    "states": [
                        {"state": "Draft", "doc_status": 0, "allow_edit": "Purchase User"},
                        {"state": "Pending Manager Approval", "doc_status": 0,
                         "allow_edit": "Purchase Manager"},
                        {"state": "Pending Accountant Approval", "doc_status": 0,
                         "allow_edit": "Accounts Manager"},
                        {"state": "Approved", "doc_status": 1, "allow_edit": "Accounts Manager"},
                        {"state": "Rejected", "doc_status": 0, "allow_edit": "Purchase User"},
                    ],
                    "transitions": [
                        {"action": "Request Approval", "state": "Draft",
                         "next_state": "Pending Manager Approval",
                         "allowed": "Purchase User",
                         "condition": "doc.base_grand_total > 10000"},
                        {"action": "Direct Approve", "state": "Draft", "next_state": "Approved",
                         "allowed": "Purchase Manager",
                         "condition": "doc.base_grand_total <= 10000"},
                        {"action": "Manager Approve", "state": "Pending Manager Approval",
                         "next_state": "Pending Accountant Approval",
                         "allowed": "Purchase Manager"},
                        {"action": "Final Approve", "state": "Pending Accountant Approval",
                         "next_state": "Approved", "allowed": "Accounts Manager"},
                        {"action": "Reject", "state": "Pending Manager Approval",
                         "next_state": "Rejected", "allowed": "Purchase Manager"},
                        {"action": "Reject", "state": "Pending Manager Approval",
                         "next_state": "Rejected", "allowed": "Accounts Manager"},
                        {"action": "Reject", "state": "Pending Accountant Approval",
                         "next_state": "Rejected", "allowed": "Accounts Manager"},
                    ]}).insert(ignore_permissions=True)
    print("workflow created")

# 5. passwords: DO NOT set via update_password() here — it double-fails against
# v16 __Auth and silently kills working hashes. Use bench set-password instead:
#   bench --site frontend set-password <user> demo123
frappe.db.commit()
print("INSTALL DONE")
