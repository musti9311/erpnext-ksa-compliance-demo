# MIS notes — what the registers answer, and the reconciliation I investigated
# Written as an interview cheat sheet: every paragraph is an answer to a
# question a hiring manager actually asks junior analysts.

## GOSI Monthly Contribution Register (per employee, per month)
Answers: who owes what, split both ways — employee deduction (9.75% Saudi,
0% expat) and employer contribution (11.75% Saudi, 2% expat), on basic+housing
capped at 45,000 SAR. A payroll officer uses it to cross-check the GOSI portal
before paying; an auditor uses it to prove no Saudi was under-deducted.
Source: `erpnext_scripts/gosi_register.sql` (Query Report on Salary Slip).

## EOSB Liability Register (per expat, as-of any date)
Answers: what the company owes each expat if they left today — ½ month/year
under 5 years, 1 month/year after, accrued monthly, back-filled to 2019.
Source: `erpnext_scripts/eosb_register.sql` + `eosb_accrue.server.py`.

## The 0.3% delta (register 180,534.24 vs ledger 181,067.28)
The register accrues fractional months from exact joining dates; the ledger books
discrete month-end postings with the tier flipping on anniversaries. Neither is
wrong — they measure differently. Which to trust: the ledger for the balance sheet
(posted, auditable), the register for per-employee liability (precise tenure).
If asked "which is right?": both, and here's the bridge. That answer is the point.

## Gaps I know about
New-law GOSI tier (10%/10% from Jul 2026) is not modeled — our staff are all
legacy registrants, so legacy rates are correct for them. The registers would need
a registration-date rate lookup for mixed staff.
