2026-09-06: QR encodes Base64-of-TLV, not raw TLV — QR containers carry text; Base64 is the safe text form of arbitrary bytes. Generic scanners stop at Base64; ZATCA apps decode TLV too.
Names-as-URLs need space-encoding; company name comes from the invoice doc, never hardcoded — the payload must work for any company in the instance
Z = UTC claim; Jeddah posting times are +03:00. Used explicit offset — never append Z to local time
if someone edits the invoice, the recomputed hash won't match what the next invoice recorded" and it's bulletproof.