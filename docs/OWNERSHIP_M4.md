# Ownership Lab — you finish these, then explain-back. No time pressure; each has a solution
# you can diff against the live instance afterwards (Server Script list in the UI).
# Rule: when stuck, re-read the audit story in DECISIONS.md — the answer is in the "why".

## S1. quote_guard — the currency-blind threshold (the audit's worst find)
Open erpnext_scripts/quote_guard.server.py and fill the ???:

    if doc.company == "???" and doc.docstatus == 1:
        if (???.??? or 0) >= ??? and not doc.get("custom_supplier_quotation"):

Q1a: why base_grand_total and not grand_total? Give the exact USD example that broke v1.
Q1b: why does the guard check docstatus == 1 instead of blocking at draft time?
Q1c: the guard compares the quotation's base_net_total to ??? — why those two fields specifically?

## S2. po_match_guard — the token-line laundering (B1)
The v1 check was:  if ??? item in doc.items if not item.???:   (a generator over ???)
The fix is per-row:  unlinked = [i for i in doc.items if ??? and not i.???]

Q2a: what did the auditor's invoice look like (2 lines, which amounts)?
Q2b: why "amount > 0" in the condition instead of checking every row unconditionally?

## S3. po_submit_gate — the escape hatch (B3)
Read the script. It compares ??? ??? ??? against the workflow's doc_status for the current state.

Q3a: the audit found a doc in state ??? could be submitted directly, skipping ??? approvers.
Q3b: why is "state says Approved" enough? Who alone can put a doc into that state?

## S4. pending_freeze — TOCTOU (B4)
The key line is:  prev = ???  — what does get_doc_before_save() give you, and when?
Then: allowed = ??? == "Administrator" or frappe.db.exists("Has Role", ???)

Q4a: allow_edit already said "Purchase Manager" — why did Sami still edit?? (UI vs permission)
Q4b: which two roles may edit a pending PO, and what legitimate job needs that?

## S5. The 30-second whiteboard test (this is the interview question)
Draw, from memory, the PO lifecycle: who creates, the two thresholds (10k / 25k),
where the quote attaches, what happens at Final Approve, what happens if someone
PUTs docstatus=1. If you can draw this without notes, M4 is yours.

## Numbers you must own cold
- 16/16 first suite -> audit found 4 bypasses -> 29/29 after fixes (the story arc)
- SAR 10,000 = two-level approval; SAR 25,000 = competitive quote (both on BASE/SAR)
- demo users: Sami buyer / Kareem manager / Amina accounts, password demo123
