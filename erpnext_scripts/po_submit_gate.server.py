# Server Script: po_submit_gate  |  Before Validate  |  Purchase Order
# AUDIT FIX (14-Sep e2e audit, B3): the creator could PATCH {"docstatus": 1}
# directly and land in Approved with zero approval steps — even ESCAPE a
# Rejected state. The two-approver chain was decorative for anything the
# 25k quote guard doesn't police. Control: a PO may only be submitted when
# the workflow itself has put it in Approved state.
# (Frappe fires validate on the PATCH too, before the state flip, so the
# workflow's own Final/Direct Approve passes through untouched.)
# RestrictedPython sandbox: no imports; str.format BANNED.

if doc.company == "Al-Rehab Trading Est." and doc.docstatus == 1:
    if doc.get("workflow_state") != "Approved":
        frappe.throw(
            "Cannot submit outside the approval workflow: this PO is in state '"
            + str(doc.get("workflow_state")) + "'. Approval must come from the"
            " workflow actions (Request/Direct/Manager/Final Approve), not from"
            " a direct status change."
        )
