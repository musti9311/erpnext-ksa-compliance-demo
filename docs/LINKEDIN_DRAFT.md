# LinkedIn draft — post from Mustafa's account, Tue morning (paste, attach 2-3 screenshots)

---

ERPNext is open-source and excellent — and out of the box, it still leaves 7 gaps for a Saudi
SME: ZATCA e-invoicing, GOSI, EOSB, Iqama tracking, KSA leave types, procurement controls,
Saudi chart of accounts. (This is the list GSA Advisory itself published — [insert link])

So I closed all 7 in a working demo over 4 evenings. ERPNext v16 + frappe/hrms, local stack:

-> ZATCA Phase 1 QR (TLV/Base64, +03:00 timestamps) and the full Phase 2 clearance lifecycle
   against a mock Fatoora — submit / cleared / rejected / retry, SHA-256 hash chain
-> September payroll for 10 employees: legacy-tier GOSI splits, 45k wage cap, and the
   employer half posted to the ledger (HRMS v16 never did — I patched the gap with a Server
   Script), EOSB accrued to 2330 with a 7-year back-reserve
-> Procurement: two-level approval above SAR 10k, competitive-quote rule at SAR 25k,
   invoice-to-PO matching, bank-change fraud trail

The part I learned most from: my first version passed all 16 of my own tests. Then I ran a
read-only adversarial audit against it — and it found 4 real bypasses. A 90k-SAR PO priced in
USD sailed under the quote threshold. One token invoice line laundered a 375k invoice. A direct
status change skipped the entire approval chain. The buyer could inflate his own PO while it
sat pending approval.

All four fixed, each locked with a regression: 29 fraud checks, all green.

Controls you can't break are worth more than controls you just configured.

Repo (every script + decision journal + test suite):
https://github.com/musti9311/erpnext-ksa-compliance-demo

#ERPNext #ZATCA #SaudiArabia #InternalControls #Frappe #Jeddah

---
Attach: 1) invoice print with QR  2) blocked-PO screenshot (quote_guard message)
        3) the Supplier timeline showing a BANK CHANGE AUDIT note
Before posting: fill in the GSA article link where marked.
