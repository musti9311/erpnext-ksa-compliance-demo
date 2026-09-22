# Mock Fatoora — simulates ZATCA Phase 2 clearance/reporting API contract
from datetime import datetime, timezone
import hashlib
import uuid

from fastapi import FastAPI

try:
    import base64 as _b64
    import io as _io
    import qrcode as _qr

    def qr_data_uri(text: str) -> str:
        buf = _io.BytesIO()
        _qr.make(text).save(buf, format="PNG")
        return "data:image/png;base64," + _b64.b64encode(buf.getvalue()).decode("ascii")
except ImportError:  # mock stays runnable without the QR extras
    def qr_data_uri(text: str) -> str:
        return ""

app = FastAPI(title="Mock Fatoora (ZATCA Phase 2 simulation)")

LEDGER = []   # accepted invoices — our proof of the hash chain
SEEN = {}     # invoiceNumber -> entry (duplicate guard; real Fatoora rejects replays)


def sha256hex(data: str) -> str:
    return hashlib.sha256(data.encode()).hexdigest()


def previous_hash() -> str:
    return LEDGER[-1]["invoiceHash"] if LEDGER else "0" * 64


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _accept(payload: dict, kind: str):
    # payload arrives with: invoiceNumber, invoiceTotal, vatTotal, qrCode...
    inv = payload.get("invoiceNumber", "")
    if not inv:
        return {"status": "ERROR", "reasonCode": "MISSING_INVOICE_NUMBER",
                "errorDescription": "invoiceNumber is required"}
    if inv in SEEN:
        prev = SEEN[inv]
        return {"status": "ERROR", "reasonCode": "DUPLICATE_INVOICE",
                "errorDescription": "Invoice already cleared/reported",
                **{k: prev[k] for k in ("uuid", "invoiceHash", "qrDataUri") if k in prev}}
    # deterministic demo reject (kept from v1 so ACC-SINV-...00008 stays retryable)
    if inv.endswith("3") or inv.endswith("8"):
        return {"status": "ERROR",
                "reasonCode": "SIMULATED_REJECT",
                "errorDescription": "Simulated rejection for demo"}
    # hash covers the full submitted content so any field edit breaks the chain
    canonical = "|".join(str(payload.get(k, "")) for k in
                         ("invoiceNumber", "invoiceTotal", "vatTotal", "qrCode"))
    entry = {
        "invoiceNumber": inv,
        "kind": kind,  # clearance (B2B) vs reporting (B2C)
        "uuid": str(uuid.uuid4()),
        "invoiceHash": sha256hex(canonical),
        "previousInvoiceHash": previous_hash(),
        "acceptedAt": now_utc(),
        # renderer-ready QR: the bilingual print format embeds this per invoice
        # (the v1 format keeps its static evidence image for ACC-SINV-2026-00001)
        "qrDataUri": qr_data_uri(str(payload.get("qrCode", ""))),
    }
    LEDGER.append(entry)
    SEEN[inv] = entry
    return {"status": "OK", **entry}


@app.post("/api/v1/zakat/taxpayer/invoices/clearance")
def clearance(payload: dict):
    return _accept(payload, "clearance")


@app.post("/api/v1/zakat/taxpayer/invoices/reporting")
def reporting(payload: dict):
    return _accept(payload, "reporting")


@app.get("/api/v1/zakat/taxpayer/invoices/summary")
def summary():
    return {"accepted": len(LEDGER), "lastHash": previous_hash(),
            "clearance": sum(1 for e in LEDGER if e["kind"] == "clearance"),
            "reporting": sum(1 for e in LEDGER if e["kind"] == "reporting")}


if __name__ == "__main__":  # ponytail: minimal self-check, fails if logic breaks
    LEDGER.clear(); SEEN.clear()
    p = {"invoiceNumber": "ACC-SINV-2026-00001", "invoiceTotal": 1288.0,
         "vatTotal": 168.0, "qrCode": "abc"}
    r1 = _accept(dict(p), "clearance")
    assert r1["status"] == "OK" and r1["acceptedAt"] != "now", r1
    assert r1["qrDataUri"].startswith("data:image/png;base64,"), "renderer-ready QR missing"
    r2 = _accept(dict(p), "clearance")
    assert r2["status"] == "ERROR" and r2["reasonCode"] == "DUPLICATE_INVOICE", r2
    r3 = _accept({"invoiceNumber": "X8", "invoiceTotal": 1}, "reporting")
    assert r3["status"] == "ERROR" and r3["reasonCode"] == "SIMULATED_REJECT", r3
    r4 = _accept({"invoiceNumber": "B2C-1", "invoiceTotal": 100}, "reporting")
    assert r4["status"] == "OK" and r4["kind"] == "reporting", r4
    assert summary()["accepted"] == 2 and LEDGER[1]["previousInvoiceHash"] == LEDGER[0]["invoiceHash"]
    print("mock self-check OK")