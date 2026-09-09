# Mock Fatoora — simulates ZATCA Phase 2 clearance/reporting API contract
import hashlib
import uuid

from fastapi import FastAPI

app = FastAPI(title="Mock Fatoora (ZATCA Phase 2 simulation)")

LEDGER = []   # accepted invoices — our proof of the hash chain

def sha256hex(data: str) -> str:
    return hashlib.sha256(data.encode()).hexdigest()

def previous_hash() -> str:
    return LEDGER[-1]["invoiceHash"] if LEDGER else "0" * 64

def zats_id() -> str:
    return str(uuid.uuid4())

@app.post("/api/v1/zakat/taxpayer/invoices/clearance")
def clearance(payload: dict):
    # payload arrives with: invoiceNumber, uuid?, issueDate, invoiceTotal, vatTotal, qrCode...
    inv = payload.get("invoiceNumber", "")
    # --- BLANK 1: rejection rule ---
    # if inv ends with "3" or "8": return a rejection dict (see shape below)
    if inv.endswith("3") or inv.endswith("8"):
        return {"status": "ERROR",
                "reasonCode": "DUPLICATE_INFO",       # mimic a real Fatoora reject
                "errorDescription": "Simulated rejection for demo"}
    # --- BLANK 2: acceptance path ---
    entry = {
        "invoiceNumber": inv,
        "uuid": zats_id(),
        "invoiceHash": sha256hex(inv + str(payload.get("invoiceTotal"))),
        "previousInvoiceHash": previous_hash(),
    }
    LEDGER.append(entry)
    return {"status": "OK",
            "acceptedAt": "now",          # we'll upgrade to real timestamps
            **entry}

@app.post("/api/v1/zakat/taxpayer/invoices/reporting")
def reporting(payload: dict):
    return clearance(payload)             # demo: same handling, B2C path

@app.get("/api/v1/zakat/taxpayer/invoices/summary")
def summary():
    return {"accepted": len(LEDGER), "lastHash": previous_hash()}