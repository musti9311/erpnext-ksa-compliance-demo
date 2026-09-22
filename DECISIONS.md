2026-09-06: QR encodes Base64-of-TLV, not raw TLV — QR containers carry text; Base64 is the safe text form of arbitrary bytes. Generic scanners stop at Base64; ZATCA apps decode TLV too.
Names-as-URLs need space-encoding; company name comes from the invoice doc, never hardcoded — the payload must work for any company in the instance
Z = UTC claim; Jeddah posting times are +03:00. Used explicit offset — never append Z to local time
if someone edits the invoice, the recomputed hash won't match what the next invoice recorded" and it's bulletproof.

2026-09-12 (M3 prep): ERPNext v16 moved HR/Payroll out of core into frappe/hrms — installed v16.18.1. pwd.yml now has an init-hrms one-shot + named apps/env volumes so the install survives container rebuilds. Two gotchas: a fresh named volume races when two one-shot containers mount it at once (seed it first with `docker run --user root cp -a`), and `bench get-app` on an existing folder prompts interactively (rm -rf apps/hrms first).

2026-09-12 (M3 rates): the plan's GOSI split (9% employee + 9.75% employer) is outdated. 2026 actual for legacy Saudi registrants: 9.75% employee (9 pension + 0.75 SANED) + 11.75% employer (9 + 2 occupational hazards + 0.75), on basic + housing, wage cap 45,000 SAR; expats 2% employer-only. Demo models LEGACY rates (our employees registered pre-Jul-2024); the new-law tier (rising to 10%+10% from Jul 2026) is a README talking point, not modeled.

2026-09-13 (M3 audit): a delegated read-only audit of the September run recomputed every slip from raw DB and found a genuine product gap: **HRMS v16.18.1 never posts employer contributions to the GL** — its payroll journal aggregates only earnings+deductions rows, so the company's 12,000.54 SAR GOSI share existed only as display rows on slips. Decision: don't fork HRMS — write our own posting Server Script (Dr GOSI Expense / Cr GOSI Payable per Payroll Entry), same philosophy as zatca_submit: when the tool has a gap, close it with a documented customization. Audit also exposed our half-configured Holiday List (weekly_off field set but no Fri/Sat rows generated → Sept counted as 29 working days; Fahad's proration 25/29 instead of 18/21). Decision: fix holiday rows properly and re-run September rather than ship a payroll demo whose mid-month math is calendar-based; keep the Saturday-joiner nuance as a documented policy choice.
2026-09-14 (M4 procurement controls): workflow 'KSA PO Approval' predates tonight; we added the
three missing legs as Server Scripts + proved the chain end-to-end (m4_e2e_test.py, 16/16).
Gotchas that cost an hour, all v16-specific: (1) Server Script doctype-bind field was renamed
doctype_code -> reference_doctype — writing the old name installs a script bound to NOTHING
(silent no-op, looks installed); (2) RestrictedPython bans str.format AND frappe.db.commit —
build audit strings with +, never commit inside after_save; (3) frappe.utils.password.update_password()
run against v16 __Auth silently KILLS working hashes (bench set-password is the safe path);
(4) workflow apply endpoint moved: frappe.model.workflow.apply_workflow(doc dict + named action),
frappe.model.workflow.apply_action is gone.
Decisions: buyer/approver split — seeded Sami (Purchase User ONLY) as PO creator; approval legs
keep allow_self_approval=0 so the owner can never approve their own PO; only the
"Request Approval" leg allows self-approval (submitting a request is not an approval).
quote_guard fires at docstatus==1 only (drafting stays free, same semantics as vat_guard).
PO->quotation link = one custom Link field, not a child table — demo needs the minimum that
proves the control. Rate inflation caught by stock Buying Settings (maintain_same_rate_action=Stop),
NOT our script — interview talking point: we verified the platform's own control instead of
reinventing it. bank_change_audit writes to Comment timeline (visible in UI) not a hidden log.

2026-09-15 (M4 audit round): read-only bypass audit REFUTED first version ("blocks naive fraud
only"). 4 confirmed bypasses, all fixed + regression-tested (m4_e2e_test.py now 29/29, idempotent):
B2 thresholds read PO-currency grand_total -> a USD PO walked the FULL chain at 90k SAR with no
quote. Fix: quote_guard AND workflow conditions use base_grand_total (SAR). Lesson: every money
threshold must be stated in company currency, never doc currency.
B1 po_match_guard checked ANY line linked -> a SAR 35 token line laundered a 375k invoice. Fix:
EVERY priced line must carry a PO link (proved with non-storable service item so core's SRBNB
check can't pre-empt and mask the test).
B3 creator could PUT docstatus=1 straight into Approved, escaping even Rejected. Fix: new
po_submit_gate (Before Validate): submit allowed only when workflow_state == Approved.
B4 TOCTOU: buyer inflated own PO from 41.4k to 375k WHILE pending approval (allow_edit gates the
transition UI, not write permission). Fix: new pending_freeze (Before Save): content changes in
Pending states require Purchase/Accounts Manager role. Also quote hygiene: linked quote must be
same supplier, submitted, and cover PO base net value.
Watchlist gap: retargeting core default_bank_account evaded the 2-field audit -> added to
BANK_FIELDS. Residuals we accept + will say out loud in the interview: Administrator can delete
audit comments (Version log backstops), sub-10k fast-track is one manager click (by design —
materiality tiering). Sandbox gotchas: str.format banned, frappe.db.commit banned inside
after_save, frappe.user.has_role is an uncalled LocalProxy -> query Has Role via frappe.db.

2026-09-21 (hardening + replay): mock now rejects duplicates (DUPLICATE_INVOICE),
stamps real UTC acceptedAt, hashes full content (number+totals+QR, not number+total),
and splits reporting (B2C) from clearance (B2B) over one ledger. zatca_submit
short-circuits re-submit of Cleared invoices and maps mock-down to Failed instead
of a dead button — verified live against ACC-SINV-2026-00001 (ALREADY_CLEARED, zero
mutation). Fresh-site replay now exists: zatca_install.py + m3_install.py (new) and
the KSA PO Approval workflow block in m4_install.py; all three ran idempotent
against the live instance. dump_scripts.py covers all 9 Server Scripts + client +
reports + Print Format HTML and is round-trip stable (it also normalized two
pre-existing doubled API headers in the repo). m4_e2e_test dates are relative to
today — the suite had date-rotted (2026-09-20 schedule < today). HR/CoA truth-check:
leave types (Annual 21/carry, Hajj 10/730d, Maternity 70d, Paternity 3d) and VAT
accounts (1140 Input / 2110 Output) all verified live; installers look VAT accounts
up by name so a fresh Saudi-CoA site needs them first. Notification message
replaced with clean ASCII (live copy carries a mojibake dash).

2026-09-22 (fresh-site replay, site `replay`): installers create everything from
zero — with five fixes the live instance never needed: (1) Workflow states/actions
are Link masters (Workflow State / Workflow Action Master) — create them before the
workflow or the insert dies; (2) server-side invoice insert does NOT copy
Sales-Taxes-Template rows (the desk UI does) — append tax rows explicitly or VAT
books 0; (3) bench console has no request language — set frappe.local.lang or an
UnboundLocalError in locale kills the run (installers now self-guard; console-piped
scripts must avoid nested functions reading exec-locals); (4) fresh sites need FY,
SAR default currency, Standard Selling price list, group/leaf selling fixtures, UOM,
Item Group, Warehouse Type before any invoice; (5) m4_install's %VAT% fallback
grabbed VAT Output for the purchase template — now prefers %Input%. Replay proof:
fresh invoice cleared via bench request with genesis prevHash, re-submit returned
ALREADY_CLEARED with the mock ledger at exactly 1, and a 36k quoteless PO walked
Request→Manager legs as seeded users then died at Final Approve on the quote rule.
Mock round-trip suite (clear/dupe/reject/reporting/chain) green independently.
