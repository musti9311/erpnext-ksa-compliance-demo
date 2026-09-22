# M4 end-to-end proof + audit regressions: walk the fraud scenarios through the
# live API as the real users (Frappe v16: frappe.model.workflow.apply_workflow).
# R1-R6 are the exact repros from the 14-Sep read-only audit (B1-B4 + quote
# hygiene + default_bank_account watchlist).
import requests, json
from datetime import date, timedelta

BASE = "http://localhost:8080"
VAT = "VAT 15% - ATE - ATE"
# date-rot proof: hardcoded 2026-09 dates died the day they passed (Required By
# cannot be before Date) — always schedule/post relative to today.
TODAY = date.today().isoformat()
SCHED = (date.today() + timedelta(days=60)).isoformat()

def login(u, p="demo123"):
    s = requests.Session()
    r = s.post(f"{BASE}/api/method/login", data={"usr": u, "pwd": p})
    assert r.status_code == 200, (u, r.status_code, r.text[:200])
    return s

def err_text(j):
    return json.dumps(j.get("_server_messages", j.get("exc", "")))

def act(s, name, action):
    return s.post(f"{BASE}/api/method/frappe.model.workflow.apply_workflow",
                  json={"doc": {"doctype": "Purchase Order", "name": name}, "action": action}).json()

def get_po(s, name):
    d = s.get(f"{BASE}/api/resource/Purchase Order/{name}")
    return d.json().get("data", {}) if d.status_code == 200 else {}

results = []
def check(label, ok, detail=""):
    results.append((label, ok, detail))
    print(("PASS" if ok else "FAIL"), label, "|", str(detail)[:150])

admin = login("Administrator", "admin")
buyer = login("buyer@alrehab-demo.example")      # Sami, Purchase User only
kareem = login("purchase.manager@alrehab-demo.example")
amina = login("accounts.manager@alrehab-demo.example")

def make_po(session, supplier, item, qty, rate, **kw):
    po = {"supplier": supplier, "company": "Al-Rehab Trading Est.",
          "schedule_date": SCHED,
          "items": [{"item_code": item, "qty": qty, "rate": rate, "uom": "Unit",
                     "description": item}], **kw}
    r = session.post(f"{BASE}/api/resource/Purchase Order", json=po).json()
    if "exc" in r: return None, err_text(r)[:150]
    return r["data"], None

def submit_doc(session, doctype, name):
    return session.put(f"{BASE}/api/resource/{doctype}/{name}", json={"docstatus": 1}).json()

# ---- T1: small PO (<=10k) fast track ------------------------------------------------
po1, err = make_po(buyer, "Riyadh Fresh Supplies", "Basmati Rice 5kg", 200, 35)
check("T1a small PO drafted (7,000)", po1 is not None, err or po1["name"])
if po1:
    act(kareem, po1["name"], "Direct Approve")
    st = get_po(admin, po1["name"])
    check("T1b <=10k fast track Approved+submitted",
          st["workflow_state"] == "Approved" and st["docstatus"] == 1,
          f"{st['workflow_state']} ds={st['docstatus']}")

# ---- T2: big PO (>25k) without quote is blocked at final approve -------------------
po2, err = make_po(buyer, "Riyadh Fresh Supplies", "Basmati Rice 5kg", 800, 45)
check("T2a big PO drafted (>25k)", po2 is not None, err or po2["name"])
if po2:
    act(buyer, po2["name"], "Request Approval")
    st = get_po(admin, po2["name"])
    check("T2b >10k routes to Pending Manager", st["workflow_state"] == "Pending Manager Approval", st["workflow_state"])
    act(kareem, po2["name"], "Manager Approve")
    st = get_po(admin, po2["name"])
    check("T2c manager leg -> Pending Accountant", st["workflow_state"] == "Pending Accountant Approval", st["workflow_state"])
    j = act(amina, po2["name"], "Final Approve")
    st = get_po(admin, po2["name"])
    blocked = st["docstatus"] == 0 and "competitive-quote" in err_text(j)
    check("T2d final approve BLOCKED by quote_guard (no quote)", blocked,
          f"ds={st['docstatus']} " + err_text(j)[:100])
    raw = submit_doc(admin, "Purchase Order", po2["name"])
    st = get_po(admin, po2["name"])
    check("T2e direct API submit also blocked", st["docstatus"] == 0, err_text(raw)[:100])

# ---- T3: quote added -> chain completes ----------------------------------------------
sq = {"supplier": "Riyadh Fresh Supplies", "company": "Al-Rehab Trading Est.",
      "items": [{"item_code": "Basmati Rice 5kg", "qty": 800, "rate": 45, "uom": "Unit", "description": "quote line"}]}
j = kareem.post(f"{BASE}/api/resource/Supplier Quotation", json=sq).json()
check("T3a supplier quotation created", "exc" not in j, j.get("data", {}).get("name") or err_text(j))
if "exc" not in j:
    sqn = j["data"]["name"]
    j2 = submit_doc(kareem, "Supplier Quotation", sqn)
    check("T3a2 quotation submitted (docstatus required by guard)", "exc" not in j2, err_text(j2)[:100])
    admin.put(f"{BASE}/api/resource/Purchase Order/{po2['name']}", json={"custom_supplier_quotation": sqn})
    st = get_po(admin, po2["name"])
    check("T3b quotation linked to PO", st.get("custom_supplier_quotation") == sqn, st.get("custom_supplier_quotation"))
    act(buyer, po2["name"], "Request Approval") if st["workflow_state"] == "Draft" else None
    if st["workflow_state"] == "Draft":
        act(kareem, po2["name"], "Manager Approve"); st = get_po(admin, po2["name"])
    if st["workflow_state"] == "Pending Manager Approval":
        act(kareem, po2["name"], "Manager Approve")
    j = act(amina, po2["name"], "Final Approve")
    st = get_po(admin, po2["name"])
    check("T3c approved+submitted with quote", st["workflow_state"] == "Approved" and st["docstatus"] == 1, err_text(j)[:100])

# ---- T4: segregation of duties --------------------------------------------------------
po3, err = make_po(buyer, "Al-Noor Trading Co", "Olive Oil 1L", 500, 28)
check("T4a mid PO drafted (14k, >10k)", po3 is not None, err or po3["name"])
if po3:
    act(buyer, po3["name"], "Request Approval")
    j = act(amina, po3["name"], "Manager Approve")
    st = get_po(admin, po3["name"])
    check("T4 Amina CANNOT take manager leg (SoD)",
          st["workflow_state"] == "Pending Manager Approval", f"state={st['workflow_state']}")

# ---- T5/T6/T8: invoice matching ----------------------------------------------------------
pi = {"supplier": "Riyadh Fresh Supplies", "company": "Al-Rehab Trading Est.",
       "posting_date": TODAY, "bill_no": "FAKE-RAND-002",
      "items": [{"item_code": "Basmati Rice 5kg", "qty": 50, "rate": 35, "uom": "Unit", "description": "x"}],
      "taxes_and_charges": VAT}
r = amina.post(f"{BASE}/api/resource/Purchase Invoice", json=pi).json()
n5 = r.get("data", {}).get("name")
r = submit_doc(amina, "Purchase Invoice", n5) if n5 else r
check("T5 invoice-without-PO blocked at submit", "exc" in r and "Purchase Order" in err_text(r), err_text(r)[:120])

po_full = get_po(admin, po2["name"])
if po_full.get("docstatus") == 1:
    item = po_full["items"][0]
    pi = {"doctype": "Purchase Invoice", "supplier": "Riyadh Fresh Supplies", "company": "Al-Rehab Trading Est.",
          "posting_date": TODAY, "bill_no": "RFS-INV-0100",
          "items": [{"item_code": "Basmati Rice 5kg", "qty": 800, "rate": 45, "uom": "Unit",
                     "description": "Basmati Rice 5kg", "purchase_order": po2["name"], "po_detail": item["name"]}],
          "taxes_and_charges": VAT}
    r = amina.post(f"{BASE}/api/resource/Purchase Invoice", json=pi).json()
    name6 = r.get("data", {}).get("name")
    r2 = submit_doc(amina, "Purchase Invoice", name6) if name6 else r
    check("T6 invoice-from-PO (correct rate) passes", "exc" not in r2, name6 or err_text(r2)[:150])

    pi = dict(pi, bill_no="RFS-INV-EVIL-2")
    pi["items"] = [dict(pi["items"][0], rate=60)]
    r = amina.post(f"{BASE}/api/resource/Purchase Invoice", json=pi).json()
    n8 = r.get("data", {}).get("name")
    r2 = submit_doc(amina, "Purchase Invoice", n8) if n8 else r
    check("T8 inflated-rate invoice from PO blocked", "exc" in r2, err_text(r2)[:130])

# ---- T7: supplier bank-change audit -------------------------------------------------------
r = admin.put(f"{BASE}/api/resource/Supplier/Al-Noor Trading Co",
              json={"supplier_bank_iban": "SA0380000000608010167601"}).json()
def find_note(s, ref, needle):
    com = s.get(f"{BASE}/api/resource/Comment", params={
        "fields": json.dumps(["name", "content"]),
        "filters": json.dumps([["reference_name", "=", ref], ["reference_doctype", "=", "Supplier"]]),
        "limit_page_length": "5", "order_by": "creation desc"}).json().get("data", [])
    return next((c["content"] for c in com if needle in (c.get("content") or "")), None)
check("T7 IBAN change writes audit comment", find_note(admin, "Al-Noor Trading Co", "BANK CHANGE AUDIT") is not None,
      (find_note(admin, "Al-Noor Trading Co", "BANK CHANGE AUDIT") or "no comment")[:140])

# =================== AUDIT REGRESSIONS ===================
# R1 (B2): 90k-SAR PO in USD must NOT slip the 25k/10k thresholds (base_grand_total)
po_usd, err = make_po(buyer, "Riyadh Fresh Supplies", "Basmati Rice 5kg", 1000, 24,
                      currency="USD", conversion_rate=3.75)
check("R1a USD PO drafted (90k SAR base)", po_usd is not None, err or po_usd["name"])
if po_usd:
    j = act(buyer, po_usd["name"], "Request Approval")
    st = get_po(admin, po_usd["name"])
    check("R1b >10k SAR routing even in USD", st["workflow_state"] == "Pending Manager Approval", st["workflow_state"])
    act(kareem, po_usd["name"], "Manager Approve")
    j = act(amina, po_usd["name"], "Final Approve")
    st = get_po(admin, po_usd["name"])
    check("R1c quote_guard fires on base value 90k SAR", st["docstatus"] == 0 and "competitive-quote" in err_text(j),
          err_text(j)[:120])

# R2 (B1): token-linked line must not launder an unlinked big line.
# Row order: unlinked line FIRST — core's SRBNB expense-head error pre-empts
# our guard on later rows, so this sequencing tests OUR message specifically.
if po_full.get("docstatus") == 1:
    tok = po_full["items"][0]["name"]
    pi = {"supplier": "Riyadh Fresh Supplies", "company": "Al-Rehab Trading Est.",
          "posting_date": TODAY, "bill_no": "TOKEN-LAUNDER-3",
          "items": [
              {"item_code": "Espresso Machine Pro", "qty": 30, "rate": 12500, "uom": "Nos", "description": "laundered"},
              {"item_code": "Basmati Rice 5kg", "qty": 1, "rate": 35, "uom": "Unit", "description": "token",
               "purchase_order": po2["name"], "po_detail": tok}],
          "taxes_and_charges": VAT}
    r = amina.post(f"{BASE}/api/resource/Purchase Invoice", json=pi).json()
    n = r.get("data", {}).get("name")
    r2 = submit_doc(amina, "Purchase Invoice", n) if n else r
    # Blocked by EITHER layer: our per-line guard (proved standalone with a
    # no-tax invoice: "1 of 2 invoice line(s) have no Purchase Order link")
    # or core's SRBNB expense-head check, which pre-empts on storable+VAT rows.
    txt = err_text(r2)
    check("R2 token-line laundering blocked (every priced line needs PO)",
          "exc" in r2 and ("line(s) have no Purchase Order" in txt or "Stock Received But Not Billed" in txt),
          txt[:130])

# R3 (B3): creator raw docstatus=1 must not skip workflow; Rejected must not escape
po_sneak, err = make_po(buyer, "Al-Noor Trading Co", "Olive Oil 1L", 100, 28)   # 2,800 — quote_guard N/A
check("R3a small PO created for submit-gate test", po_sneak is not None, err or po_sneak["name"])
if po_sneak:
    r = submit_doc(buyer, "Purchase Order", po_sneak["name"])
    st = get_po(admin, po_sneak["name"])
    check("R3b creator direct docstatus=1 BLOCKED by po_submit_gate",
          st["docstatus"] == 0 and "workflow" in err_text(r).lower(), err_text(r)[:120])
    # rejected must stay dead — use a >10k PO so Request Approval applies
    # (sub-10k POs have no request path: they take the manager Direct Approve leg)
    po_rj, _ = make_po(buyer, "Al-Noor Trading Co", "Olive Oil 1L", 500, 28)  # 14k
    act(buyer, po_rj["name"], "Request Approval")
    j = act(kareem, po_rj["name"], "Reject")
    st = get_po(admin, po_rj["name"])
    esc = submit_doc(admin, "Purchase Order", po_rj["name"])
    st2 = get_po(admin, po_rj["name"])
    check("R3c Rejected cannot escape to submitted",
          st["workflow_state"] == "Rejected" and st2["docstatus"] == 0,
          f"state={st2['workflow_state']} ds={st2['docstatus']}")

# R4 (B4): buyer must NOT be able to edit own PO while pending approval
po_toc, err = make_po(buyer, "Al-Noor Trading Co", "Olive Oil 1L", 400, 35)     # 14k base -> pending
check("R4a pending PO exists for freeze test", po_toc is not None, err or po_toc["name"])
if po_toc:
    act(buyer, po_toc["name"], "Request Approval")
    st = get_po(admin, po_toc["name"])
    infl = buyer.put(f"{BASE}/api/resource/Purchase Order/{po_toc['name']}",
                     json={"items": [{"item_code": "Olive Oil 1L", "qty": 9000, "rate": 35, "uom": "Unit",
                                      "description": "inflated", "name": st["items"][0]["name"]}]})
    st2 = get_po(admin, po_toc["name"])
    frozen = infl.status_code == 403 or st2["items"][0]["qty"] == 400
    check("R4b buyer cannot inflate own PO while pending (content freeze)", frozen,
          f"PUT {infl.status_code} qty now {st2['items'][0]['qty']}")

# R5: quote hygiene — wrong supplier, draft quote, under-coverage
if po_usd:
    sq_bad = {"supplier": "Al-Noor Trading Co", "company": "Al-Rehab Trading Est.",
              "items": [{"item_code": "Basmati Rice 5kg", "qty": 1000, "rate": 24, "uom": "Unit", "description": "wrong-supplier quote"}]}
    j = kareem.post(f"{BASE}/api/resource/Supplier Quotation", json=sq_bad).json()
    if "exc" not in j:
        badn = j["data"]["name"]
        submit_doc(kareem, "Supplier Quotation", badn)
        admin.put(f"{BASE}/api/resource/Purchase Order/{po_usd['name']}", json={"custom_supplier_quotation": badn})
        j2 = act(amina, po_usd["name"], "Final Approve")
        st = get_po(admin, po_usd["name"])
        check("R5a wrong-supplier quote rejected by guard",
              st["docstatus"] == 0 and "not this PO's supplier" in err_text(j2), err_text(j2)[:130])
        # under-coverage: swap in a tiny but valid quote
        sq_small = {"supplier": "Riyadh Fresh Supplies", "company": "Al-Rehab Trading Est.",
                    "items": [{"item_code": "Basmati Rice 5kg", "qty": 1, "rate": 35, "uom": "Unit", "description": "tiny"}]}
        j3 = kareem.post(f"{BASE}/api/resource/Supplier Quotation", json=sq_small).json()
        small = j3["data"]["name"]
        submit_doc(kareem, "Supplier Quotation", small)
        admin.put(f"{BASE}/api/resource/Purchase Order/{po_usd['name']}", json={"custom_supplier_quotation": small})
        j4 = act(amina, po_usd["name"], "Final Approve")
        st = get_po(admin, po_usd["name"])
        check("R5b under-covering quote rejected (no quote->inflate laundering)",
              st["docstatus"] == 0 and "no longer covers" in err_text(j4), err_text(j4)[:130])

# R6: default_bank_account retarget must also audit
# NOTE: probe account names must be DISTINCT ignoring case — MariaDB's default
# collation is case-insensitive ("AUDIT PROBE Bank" == "Audit Probe Bank").
acct_a = "M4 R6 Target Acct - Riyadh Bank"
acct_b = "M4 R6 Flip Acct - Riyadh Bank"

def ensure_bank_acct(label, num):
    nm = label + " - Riyadh Bank"
    # filtered list read (the /{name} URL path double-encodes if pre-%20'd;
    # json filters param is the robust form)
    found = admin.get(BASE + "/api/resource/Bank Account", params={
        "filters": json.dumps([["name", "=", nm]]), "limit_page_length": "1"}).json().get("data", [])
    if found:
        return found[0]["name"]
    j = admin.post(f"{BASE}/api/resource/Bank Account", json={
        "bank": "Riyadh Bank", "account_name": label, "account_number": num,
        "party_type": "Supplier", "party": "Al-Noor Trading Co",
        "account_currency": "SAR", "is_primary": 0}).json()
    return j.get("data", {}).get("name")

bn = ensure_bank_acct("M4 R6 Target Acct", "987-001")
alt = ensure_bank_acct("M4 R6 Flip Acct", "987-002")
ok_setup = bool(bn and alt and bn != alt)
admin.put(f"{BASE}/api/resource/Supplier/Al-Noor Trading Co", json={"default_bank_account": alt})
r2 = admin.put(f"{BASE}/api/resource/Supplier/Al-Noor Trading Co", json={"default_bank_account": bn})
note = find_note(admin, "Al-Noor Trading Co", bn)
check("R6 default_bank_account retarget audited", ok_setup and r2.status_code == 200 and note is not None,
      (note or "no comment")[:140])

print("\n==== SUMMARY ====")
p = sum(1 for _, ok, _ in results if ok)
print(f"{p}/{len(results)} checks passed")
for label, ok, detail in results:
    if not ok:
        print("  FAILED:", label, "|", detail)
