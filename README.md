# ERPNext KSA Compliance Demo — ZATCA, Payroll & Procurement Controls

A working Saudi-compliance demo built on a local ERPNext v16 stack: every invoice gets a
**ZATCA Phase 1 QR** (TLV/Base64), a **mock Fatoora** exercises the full Phase 2 clearance
lifecycle — submit → cleared → rejected → retried — with a SHA-256 chain for tamper evidence,
**HR/Payroll models GOSI + EOSB + Iqama expiry** end-to-end (real September payroll for 10
employees, both contribution halves posted to the ledger), and **procurement enforces the
7-control approval chain** — two-level PO approval, competitive-quote threshold, invoice-to-PO
matching — proven against an adversarial bypass audit (29/29 fraud checks).

> Built as a portfolio project (Sept 2026). All data is fictional (Al-Rehab Trading Est.,
> Jeddah). No real CR, no real tax authority connection — see [Honest limitations](#honest-limitations).

## Architecture

```
ERPNext v16 (Docker, :8080)                    Mock Fatoora (FastAPI, :8090)
┌─────────────────────────────┐    HTTP       ┌──────────────────────────┐
│ Sales Invoice               │──submit──────▶│ /invoices/clearance      │
│  • zatca_submit (API script)│  (out of      │ /invoices/reporting      │
│  • vat_guard (validate)     │   container   │ • deterministic rejects  │
│  • zatca_button (client JS) │   via         │ • SHA-256 hash chain     │
│  • ZATCA Status/UUID/hashes │   host.       │ • UUID "stamps"          │
│  • Print Format w/ QR       │   docker.     └──────────────────────────┘
└─────────────────────────────┘   internal
        ▲
        │ TLV(Base64) QR payload — identical from both signers:
qr-generator/tlv_generator.py  (standalone Python signer, base64 lib)
erpnext_scripts/zatca_submit   (in-sandbox signer, hand-rolled base64)
```

## The compliance lifecycle, as proven in this instance

| State | Invoice | Evidence |
|---|---|---|
| ✅ Cleared (with VAT) | `ACC-SINV-2026-00001` — 1,288.00 SAR, VAT 168.00 | QR round-trip: PDF → extract image → decode → all 5 TLV fields match |
| ✅ Cleared via one-click button | `ACC-SINV-2026-00002` | mock ledger genesis link (`prevHash = 0000…0`) |
| 🟥 Blocked by VAT guard | `ACC-SINV-2026-00003` (cancelled) | submission refused: no `VAT 15% - ATE` template |
| 🔴 Rejected + retryable | `ACC-SINV-2026-00008` — status `Failed`, button stays visible | deterministic reject rule (invoice ends 3/8) |

## People compliance (M3) — the payroll side of the same story

**September 2026 payroll, 10 employees, run and posted in the live instance:**

| Rule modeled | Proof |
|---|---|
| GOSI split by nationality: Saudi = 9.75% employee (deduction) + 11.75% employer; expat = 2% employer only | 5 Saudis show deductions, 5 expats show zero |
| Wage base = basic + housing, capped at 45,000 | Khalid: 50,000 wage base → deduction **4,387.50** = 9.75% × 45,000 |
| Mid-month joiner proration on a real KSA work-week (Sun–Thu; Fri/Sat + National Day holidays) | Fahad joined Sep 5 → 18/21 working days → gross 10,714.29 |
| Full money trail: slips → accrual JV → employer-GOSI JV → bank payment | GL: 2320 GOSI Payable 20,959.83; Payroll Payable settles to 0 via Bank Entry |
| EOSB reserve (½ month/yr ≤5 yrs, 1 month/yr after) accrued monthly, back-filled 2019→2026 | account 2330 holds 181,067.28 vs register liability 180,534.24 (see below) |
| Iqama expiry alert, 30 days ahead → HR role | Notification fired "Iqama expiring: Ahmed" into the HR Manager's bell |

Two compliance registers ship as **Query Reports** (`erpnext_scripts/*.sql`): a GOSI monthly
contribution register (portal-shaped, both contribution halves per employee) and an EOSB
liability register. The register-vs-ledger delta (~0.3%) is intentional and explainable —
the register accrues fractional months since exact joining dates; the ledger books discrete
month-end postings with the tier flipping on anniversaries. That reconciliation is exactly
the MIS finding an interviewer should ask about.

**Two customization scripts exist because the product has gaps I verified in its source:**
`employer_gosi.server.py` — HRMS v16.18.1's payroll journal aggregates only earnings +
deductions, so *employer-contribution rows never reach the GL* (found by audit; code-confirmed
in `payroll_entry.py`) — this posts them: Dr GOSI Expense / Cr GOSI Payable, idempotent per
run. `eosb_accrue.server.py` — no EOSB accrual machinery exists in core HR for KSA rules at
all; this books monthly liability per the tier above.

## Procurement controls (M4) — the 7-control approval chain

Mirrors the internal-controls vocabulary a Saudi audit firm cares about. Three demo users act
out the fraud scenarios: **Sami** (Purchase User — creates POs, can never approve), **Kareem**
(Purchase Manager), **Amina** (Accounts Manager).

| Control | Mechanism |
|---|---|
| Two-level approval above SAR 10,000 | Workflow `KSA PO Approval`: Request → Manager → Final Approve; ≤10k fast-tracks in one manager click (materiality tiering) |
| Competitive quote ≥ SAR 25,000 | `quote_guard` on submit: link must exist, same supplier, submitted, and **covering the PO's SAR value** — thresholds read `base_grand_total`, so a USD-priced PO can't sail under them |
| No invoice without a PO | `po_match_guard`: **every** priced line must carry a PO link (an `any()` check was launderable with one token line — audit caught it) |
| Approval chain can't be skipped | `po_submit_gate`: direct `docstatus=1` PUT lands in Approved (even escaping Rejected — audit found this); submit is now only legal when the workflow itself says Approved |
| Approval = content freeze | `pending_freeze`: buyer inflated his own PO 41.4k → 375k *while pending* (allow_edit gates the UI, not write permission — audit found this); content changes in Pending states now need a Manager role |
| Rate integrity | ERPNext core `maintain_same_rate_action=Stop` verified (PO 45 → invoice 60 blocked) — not re-invented |
| Vendor-payment fraud trail | `bank_change_audit`: any IBAN / default-bank-account retarget is stamped into the Supplier's visible timeline naming the doer, old→new |

**The audit story is the point.** First version passed 16/16 of my own tests; a read-only
adversarial audit then found **4 real bypasses** (currency-blind thresholds, token-line
laundering, docstatus escape hatch, mid-approval TOCTOU). All four fixed, each converted into
a permanent regression: `erpnext_scripts/m4_e2e_test.py` — 29 checks, idempotent, run as the
real users through the live API. Every decision and sandbox gotcha in `DECISIONS.md`.

Residual risks, stated openly: Administrator can delete audit comments (Frappe's Version log
backstops them); the ≤10k fast-track is one click by design.

## What's inside

```
pwd.yml                  Docker compose stack (ERPNext v16.34.1 + HRMS v16.18.1 + MariaDB + redis;
                         init-hrms one-shot makes the HRMS install survive container rebuilds)
qr-generator/            M1: standalone TLV→Base64→QR signer (fetches live from ERPNext API)
mock_fatoora/main.py     M2a: Phase 2 clearance/reporting API contract simulation
erpnext_scripts/         M2b–d + M3: live ERPNext customizations, dumped from the instance
  zatca_submit.server.py   API Server Script: builds QR, calls mock, stamps invoice
  vat_guard.server.py      validate event: blocks VAT-less submissions
  zatca_button.client.js   "Submit to ZATCA" button with status reload + alerts
  employer_gosi.server.py  posts the employer-side GOSI HRMS's payroll JV omits (idempotent)
  eosb_accrue.server.py    monthly EOSB liability accrual, tiered, idempotent per month
  gosi_register.sql        Query Report: GOSI monthly contribution register (portal-shaped)
  eosb_register.sql        Query Report: EOSB liability per expat, as-of any date
  quote_guard.server.py    M4: SAR 25k competitive-quote threshold (base currency, coverage-checked)
  po_match_guard.server.py M4: every priced invoice line needs a PO link
  po_submit_gate.server.py M4: submit only via workflow (docstatus escape hatch closed)
  pending_freeze.server.py M4: content frozen while a PO is pending approval (TOCTOU)
  bank_change_audit.server.py M4: IBAN/bank-account retarget -> visible audit comment
  m4_install.py            idempotent installer (custom fields + Server Scripts + VAT template)
  m4_e2e_test.py           29-check fraud regression suite (runs as Sami/Kareem/Amina)
dump_scripts.py          re-export all of the above from a running instance
ACC-SINV-2026-00001_ZATCA.pdf   M1 evidence: printed invoice with embedded QR
DECISIONS.md              decision journal — what was chosen and why
```

## Running it

```bash
# 1. ERPNext stack (HRMS is installed automatically on first up by the init-hrms service)
docker desktop start
cd ZATCA-Compliance-Demo
docker compose -f pwd.yml -p erpnext-zatca-demo up -d      # ~40s; first ever run: +10–20 min HRMS install; http://localhost:8080

# 2. Mock Fatoora
cd mock_fatoora && pip install fastapi "uvicorn[standard]" && uvicorn main:app --port 8090

# 3. Standalone signer (needs requests)
cd qr-generator && python tlv_generator.py
```

Login `Administrator` / `admin`. Demo personas for the M4 chain (password `demo123`):
`buyer@…` Sami, `purchase.manager@…` Kareem, `accounts.manager@…` Amina.
To replay the fraud suite against a running instance: `python erpnext_scripts/m4_e2e_test.py`
(recreates its own POs/invoices; idempotent). The customizations (Server Scripts, Client Script,
ZATCA custom fields, Print Format, VAT templates/accounts) live **inside the instance** —
to recreate from scratch on a fresh site, follow `DECISIONS.md` + `erpnext_scripts/`.

## ZATCA notes (the stuff the QR actually guarantees)

- **QR payload**: TLV tags 1–5 — seller name, VAT number, timestamp, total incl. VAT, VAT
  total — Base64'd, so an inspector verifies offline with no API or login.
- **Timestamp**: local KSA time with explicit `+03:00` offset. Never `Z` on local time —
  `Z` is a UTC *claim* and would falsify the record by 3–4 hours.
- **Hash**: SHA-256 over the TLV payload; the mock chains each accepted invoice's hash into
  the next response — tampering with any earlier field visibly breaks the chain.
- **Phase 2 workflow split**: B2B = clearance (this demo's path), B2C = reporting; both
  endpoints share the ledger.

## Honest limitations

- **Fatoora is a mock** of the API contract (clearance/reporting/summary). Real Phase 2
  needs a company CR, ZATCA device certificates and CSID — impossible for an individual to
  hold, so the workflow, failure handling and hash chain are real, the counterparty is
  simulated. The client is endpoint-switchable for a real integration.
- **No re-submission guard**: our mock happily accepts the same invoice twice (real Fatoora
  rejects duplicates). `zatca_status` makes double-clearing visible, not impossible —
  idempotency is on the roadmap.
- `acceptedAt` in the mock is a stub string, not a server timestamp.
- `ACC-SINV-2026-00002` cleared *before* the VAT guard existed and shows 0.00 VAT — kept
  deliberately as the "why the guard was needed" exhibit.
- Container's wkhtmltopdf can't fetch internal URLs (Docker network wall): QR is embedded
  as a **data-URI**, PDFs rendered with WeasyPrint. Documented in DECISIONS.md.
- Server Scripts require `server_script_enabled` (bench) + sandbox rules (no `import`,
  no `format()` builtins) — our signer hand-rolls Base64 to match `base64.b64encode`
  byte-for-byte, which doubles as proof we understand the encoding.

## Known bugs found on purpose (from DECISIONS.md)

Invoice drafts burn numbers (`00003-1` suffix dodged a rejection rule once), submitted
docs refuse renames, silent mock downtime looked like a dead button — all documented in
`DECISIONS.md` with fixes.
