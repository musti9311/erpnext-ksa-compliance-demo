# Builds the one-page 'What I Built' handout PDF (evidence pack item 3).
# Run from repo root: C:/Python314/python.exe docs/make_handout.py
import os
os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import qrcode
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.colors import HexColor
from reportlab.pdfgen import canvas

OUT = "WhatIBuilt_Handout.pdf"
NAVY = HexColor("#0f172a")
SLATE = HexColor("#334155")
ACCENT = HexColor("#0369a1")
LIGHT = HexColor("#e2e8f0")

c = canvas.Canvas(OUT, pagesize=A4)
W, H = A4

qr = qrcode.QRCode(box_size=6, border=1)
qr.add_data("https://github.com/musti9311/erpnext-ksa-compliance-demo")
qr.make(fit=True)
qr.make_image(fill_color="#0f172a", back_color="white").save("docs/repo_qr.png")

c.setFillColor(NAVY)
c.rect(0, H - 34 * mm, W, 34 * mm, stroke=0, fill=1)
c.setFillColor(HexColor("#ffffff"))
c.setFont("Helvetica-Bold", 17)
c.drawString(14 * mm, H - 14 * mm, "KSA Compliance Demo on ERPNext - What I Built")
c.setFont("Helvetica", 9.5)
c.setFillColor(LIGHT)
c.drawString(14 * mm, H - 20.5 * mm, "ZATCA e-invoicing (Phase 1 + 2 lifecycle)  |  GOSI / EOSB / Iqama payroll compliance  |  procurement fraud controls")
c.drawString(14 * mm, H - 26 * mm, "Mustafa  -  Jeddah  -  Sept 2026  -  musti9311@yahoo.com")

y = H - 38 * mm
if os.path.exists("invoice_qr.png"):
    c.drawImage("invoice_qr.png", 14 * mm, y - 30 * mm, width=30 * mm, height=30 * mm)
    c.setFont("Helvetica-Oblique", 7.5); c.setFillColor(SLATE)
    c.drawCentredString(29 * mm, y - 33.5 * mm, "ZATCA TLV QR on invoice")
c.drawImage("docs/repo_qr.png", 50 * mm, y - 30 * mm, width=30 * mm, height=30 * mm)
c.setFont("Helvetica-Oblique", 7.5); c.setFillColor(SLATE)
c.drawCentredString(65 * mm, y - 33.5 * mm, "scan = the repo")

c.setFillColor(NAVY)
c.setFont("Helvetica-Bold", 10.5)
c.drawString(88 * mm, y - 6 * mm, "Built in 4 evenings. Runs locally, all data fictional,")
c.drawString(88 * mm, y - 11 * mm, "every claim reproducible from the repo:")
c.setFont("Helvetica", 8.6)
for i, line in enumerate([
    "QR = TLV/Base64: seller, VAT no, +03:00 timestamp, totals",
    "Mock Fatoora: submit -> cleared / rejected -> retry, SHA-256 chain",
    "Sept payroll for 10 employees: GOSI legacy rates + wage cap",
    "EOSB accruals booked to 2330, 7-year back-reserve, both GOSI",
    "halves on the ledger; 7 procurement controls incl. SAR 25k quote",
]):
    c.drawString(88 * mm, y - (17 + i * 4.6) * mm, "-  " + line)

y = H - 84 * mm
c.setFillColor(HexColor("#f1f5f9"))
c.rect(14 * mm, y - 30 * mm, W - 28 * mm, 30 * mm, stroke=0, fill=1)
c.setFillColor(ACCENT); c.setFont("Helvetica-Bold", 10)
c.drawString(17 * mm, y - 6 * mm, "Hired for this: the controls were audited, not just built")
c.setFillColor(SLATE); c.setFont("Helvetica", 8.4)
for i, line in enumerate([
    "First version passed my own tests. A read-only adversarial audit then found 4 real bypasses:",
    "currency-blind thresholds (a USD PO worth 90k SAR walked the chain quote-less) | a token invoice",
    "line laundering a 375k invoice | a direct docstatus change skipping approval | editing a PO while",
    "it sat under approval. All four fixed and locked with regressions: a 29-check fraud suite, idem-",
    "potent, run through the live API as three separate personas. Findings logged in DECISIONS.md.",
]):
    c.drawString(17 * mm, y - (12.5 + i * 4.4) * mm, line)

y -= 40 * mm
c.setFillColor(NAVY); c.setFont("Helvetica-Bold", 10.5)
c.drawString(14 * mm, y, "The control set (ERPNext v16 + frappe/hrms, custom Server Scripts)")
rows = [
    ("Two-level PO approval > SAR 10,000", "workflow; <=10k one-click fast track (materiality tiering)"),
    ("Competitive quote >= SAR 25,000", "SAR (base) threshold; quote must match supplier, be submitted, "),
    ("", "cover the PO value"),
    ("No supplier invoice without a PO", "every priced line needs the PO link; rate-match = Stop (core)"),
    ("Approval chain cannot be skipped", "submit is legal only when the workflow state says Approved"),
    ("Content frozen under approval", "buyer edits blocked while Pending (TOCTOU closed)"),
    ("Vendor bank-change fraud trail", "IBAN/account retarget -> visible timeline note naming doer"),
    ("Iqama / work-permit expiry alert", "ERPNext Notification, 30 days advance, to HR"),
]
ty = y - 6 * mm
for a, b in rows:
    c.setFillColor(NAVY); c.setFont("Helvetica-Bold", 8.5)
    c.drawString(16 * mm, ty, a)
    c.setFillColor(SLATE); c.setFont("Helvetica", 8.5)
    c.drawString(82 * mm, ty, b)
    ty -= 4.6 * mm

# honest limits + footer anchored near the page bottom
fy = 20 * mm                      # footer band y
c.setFillColor(NAVY)
c.rect(14 * mm, fy, W - 28 * mm, 7.5 * mm, stroke=0, fill=1)
c.setFillColor(HexColor("#ffffff")); c.setFont("Helvetica-Bold", 8.2)
c.drawCentredString(W / 2, fy + 2.4 * mm, "Available in Jeddah  |  full scripts + test suite + decision journal:")
c.drawCentredString(W / 2, fy - 2.2 * mm, "github.com/musti9311/erpnext-ksa-compliance-demo")

ly = fy + 15 * mm                 # limits block sits above the footer
c.setFillColor(NAVY); c.setFont("Helvetica-Bold", 10.5)
c.drawString(14 * mm, ly, "Honest limits (all in DECISIONS.md)")
c.setFillColor(SLATE); c.setFont("Helvetica", 8.5)
for line in [
    "Fatoora mocks the published Phase 2 contract faithfully - the endpoint is switched, not certified;",
    "no CR or CSID, so no real clearance. GOSI models legacy-tier rates; the new-law tier is a documented",
    "talking point, not modeled. Administrator can delete audit comments (Frappe's Version log backstops",
    "them). Everything else is real code running on a real instance, verifiable by cloning the repo.",
]:
    ly -= 4.6 * mm
    c.drawString(16 * mm, ly, line)

c.showPage()
c.save()
print("WROTE", OUT)
