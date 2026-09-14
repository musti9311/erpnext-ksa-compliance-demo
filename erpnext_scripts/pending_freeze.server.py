# Server Script: pending_freeze  |  Before Save  |  Purchase Order
# AUDIT FIX (14-Sep e2e audit, B4 TOCTOU): Sami inflated his own 41.4k PO to
# 375k WHILE it sat in Pending Accountant Approval — Kareem had approved the
# 41.4k version, Amina final-approved the inflated one. Approval must freeze
# content, not just state.
# Why a script: the workflow's allow_edit field only gates the transition UI —
# it does NOT override the doctype-level write permission that Purchase User
# already has. Enforced server-side here, before_save (after totals compute).
# Managers may still fix typos (role check); the buyer may not.
# RestrictedPython sandbox: no imports; str.format BANNED.

state = doc.get("workflow_state")
prev = doc.get_doc_before_save()
if (doc.company == "Al-Rehab Trading Est." and state and str(state).startswith("Pending")
        and prev and prev.get("workflow_state") == state):
    changed = (prev.base_grand_total != doc.base_grand_total
               or prev.supplier != doc.supplier
               or len(prev.items or []) != len(doc.items or []))
    if changed:
        # frappe.user.has_role is a LocalProxy — UNCALLABLE in the sandbox.
        # Query Has Role directly.
        allowed = frappe.session.user == "Administrator" or bool(frappe.db.exists(
            "Has Role", {"parent": frappe.session.user, "role": "Purchase Manager"})) or bool(frappe.db.exists(
            "Has Role", {"parent": frappe.session.user, "role": "Accounts Manager"}))
        if not allowed:
            frappe.throw(
                "Content is frozen while this PO is under '" + str(state)
                + "' approval (was SAR " + str(prev.base_grand_total) + ", now SAR "
                + str(doc.base_grand_total) + "). The approvers reviewed the earlier"
                " figures — withdraw through your manager if changes are needed."
            )
