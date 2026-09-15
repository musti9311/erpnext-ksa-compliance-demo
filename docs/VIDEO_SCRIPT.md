# 3-Minute Demo Video — Narration Script

Record the screen (phone over monitor is fine), speak over it, one take per scene, stitch later.
Rehearse twice, then record. Every claim here is already true in the running instance.

## Scene 0 — Setup (0:00–0:15)
"Hi, I'm Mustafa. This is a Saudi compliance demo I built on ERPNext v16 — ZATCA invoicing,
KSA payroll, and a procurement control chain. Everything runs locally, all data is fictional."
Show: browser at localhost:8080 dashboard.

## Scene 1 — ZATCA QR (0:15–0:45)
"First, tax. This sales invoice — watch the print format." Print ACC-SINV-2026-00001 → zoom QR.
"The QR is a TLV payload, base64-encoded: seller name, VAT number, timestamp with the plus-three
offset, totals. An inspector verifies it offline — no API, no login. And notice the timestamp:
KSA local time with an explicit offset, because appending Z would be a false UTC claim."

## Scene 2 — Clearance lifecycle (0:45–1:20)
"Phase 2: one click Submit to ZATCA." Click → Cleared. "The mock Fatoora returns a UUID and
chains a SHA-256 hash — tamper evidence: change any earlier field and the chain visibly breaks."
Open invoice ending in 8 → "this one gets rejected deterministically — status Failed, and the
button stays, so retries are visible. In production this endpoint is just switched to Fatoora."

## Scene 3 — Payroll (1:20–1:50)
"Payroll compliance. Five Saudi, five expat employees." Open a Saudi slip → "GOSI split: the
Saudi sees 9.75 percent deducted, the employer pays 11.75 on basic plus housing, capped at
45,000. The expat slip shows zero employee deduction — two percent employer-only."
"HRMS v16 never posts the employer half to the ledger — I found that in its source code, so
my own script posts it: Dr GOSI Expense, Cr GOSI Payable, idempotent per run." Show GL entry.
"And end-of-service benefits: seven years back-reserved monthly against account 2330."

## Scene 4 — Procurement fraud chain (1:50–2:40)
"Finally, controls. Three users: Sami raises a purchase order, Kareem and Amina approve."
Show 36k PO without quote → Final Approve → "blocked: anything at or above 25 thousand SAR
needs a competitive quotation." "Now the sneaky one — this PO is priced in US dollars, ninety
thousand riyals. An early version of my guard read the PO-currency total and let it through.
An adversarial audit caught that, plus three more bypasses — a token invoice line laundering
a 375 thousand invoice, a direct status change skipping the whole workflow, and editing the
PO while it sat under approval. All four fixed, each locked with a regression test. 29 fraud
checks, all passing."
Open the Supplier → "and any bank-detail change is stamped into this timeline — who, old, new."

## Scene 5 — Close (2:40–3:00)
"Everything's in the repo — scripts, the decision journal, the test suite. Link in the
comments. Thanks for watching." Show the GitHub repo README.

## Do NOT say
- "integrated with ZATCA" → "simulated the Fatoora contract, endpoint-switchable"
- "production-ready" → "a demo proving the compliance logic"
- don't rush Scene 4 — that's the differentiator; the audit story beats every feature
