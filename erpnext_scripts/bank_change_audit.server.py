# Server Script: bank_change_audit  |  DocType Event: After Save  |  Supplier
# Fraud vector this closes: someone emails "our bank details changed", a clerk
# quietly re-points supplier payments, and the next payment goes to the wrong
# IBAN. Real-world control: every change to bank/contact fields is stamped into
# the Supplier's Comment timeline (visible in the UI) with old + new + who did
# it — without anyone remembering to write a note.
# doc.get_doc_before_save() gives the previous stored state on after_save.
# RestrictedPython sandbox: no imports, and str.format is BANNED ("format is an
# unsafe attribute") — build strings with + and str() only.

BANK_FIELDS = ["supplier_bank_iban", "bank_change_reason", "default_bank_account"]
# (custom IBAN + approval-ref fields, plus core default_bank_account — audit
# found retargeting THAT field evaded the two-field watchlist entirely)

# Suppliers are site-wide docs (no company field on Supplier — no gate needed)
prev = doc.get_doc_before_save()
if prev:
    diffs = []
    for f in BANK_FIELDS:
        old = prev.get(f)
        new = doc.get(f)
        if old != new and (old or new):
            label = frappe.get_meta("Supplier").get_label(f) or f
            diffs.append(str(label) + ": '" + str(old or "-") + "' -> '" + str(new or "-") + "'")
    if diffs:
        who = frappe.session.user
        note = ("BANK CHANGE AUDIT by " + str(who) + " on " + str(frappe.utils.now())
                + " — verify with supplier via a known-good phone number before releasing payment. Changes: "
                + "; ".join(diffs))
        doc.add_comment("Comment", note)
        # no frappe.db.commit(): the sandbox bans it and it's wrong anyway —
        # after_save runs inside the document's save, comment flushes with it.
