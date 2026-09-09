import requests
import json,sys 
# --- Pull the invoice live from ERPNext ---
s = requests.Session()

# worked example: login
s.post("http://localhost:8080/api/method/login",
       data={"usr": "Administrator", "pwd": "admin"})

# YOUR BLANKS ------------------------------------
# 1) GET the invoice as JSON (pattern: s.get(url).json()["data"])
#    url: http://localhost:8080/api/resource/Sales%20Invoice/ACC-SINV-2026-00001
inv = s.get("http://localhost:8080/api/resource/Sales%20Invoice/ACC-SINV-2026-00001").json()["data"]

print(sorted(inv.keys()))

comp_url = "http://localhost:8080/api/resource/Company/" + inv["company"].replace(" ", "%20")
comp = s.get(comp_url).json()["data"]
# ------------------------------------------------
# ZATCA Phase 1 TLV encoder — builds the QR payload for a submitted invoice
import base64

# The 5 mandatory fields, straight from ACC-SINV-2026-00001
SELLER_NAME = comp["company_name"]  # Replace with actual company name from the invoice
SELLER_VAT  = comp["tax_id"].strip()  # Replace with actual VAT number from the invoice
TIMESTAMP   = inv["posting_date"] + "T" + inv["posting_time"][:8] + "+03:00"  # Replace with actual timestamp from the invoice
TOTAL       = format(inv["grand_total"], ".2f")
VAT_TOTAL   = format(inv["total_taxes_and_charges"] , ".2f")

def tlv_encode(tag: int, value: str) -> bytes:
    """One TLV triplet: 1-byte tag, 1-byte length, then the value bytes."""
    v = value.encode("utf-8")
    return bytes([tag, len(v)]) + v

# Build the payload: tags 1-5 in ZATCA's mandated order
payload = b"".join([
    tlv_encode(1, SELLER_NAME),
    tlv_encode(2, SELLER_VAT),
    tlv_encode(3, TIMESTAMP),
    tlv_encode(4, TOTAL),
    tlv_encode(5, VAT_TOTAL),
])

qr_text = base64.b64encode(payload).decode("ascii")
print(qr_text)

import qrcode
img=qrcode.make(qr_text)
img.save("invoice_qr.png")
print("QR code saved as invoice_qr.png")

import hashlib

digest = hashlib.sha256(payload).hexdigest()
print("SHA-256:", digest)