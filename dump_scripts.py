"""Dump all ERPNext customizations from the live instance into erpnext_scripts/:
9 Server Scripts + 1 Client Script + 2 Query Reports + the ZATCA Print Format.
Run from repo root:  python dump_scripts.py  (instance must be up)."""
import json
import os
import urllib.request
import http.cookiejar

cj = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
opener.open(urllib.request.Request("http://localhost:8080/api/method/login",
    data=b"usr=Administrator&pwd=admin"), timeout=20)

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "erpnext_scripts")
os.makedirs(OUT, exist_ok=True)

jobs = [
    ("Server%20Script/zatca_submit", "zatca_submit.server.py"),
    ("Server%20Script/vat_guard", "vat_guard.server.py"),
    ("Client%20Script/zatca_button", "zatca_button.client.js"),
    ("Server%20Script/employer_gosi", "employer_gosi.server.py"),
    ("Server%20Script/eosb_accrue", "eosb_accrue.server.py"),
    ("Server%20Script/quote_guard", "quote_guard.server.py"),
    ("Server%20Script/po_match_guard", "po_match_guard.server.py"),
    ("Server%20Script/po_submit_gate", "po_submit_gate.server.py"),
    ("Server%20Script/pending_freeze", "pending_freeze.server.py"),
    ("Server%20Script/bank_change_audit", "bank_change_audit.server.py"),
]
for path, fname in jobs:
    r = opener.open("http://localhost:8080/api/resource/" + path, timeout=30)
    d = json.loads(r.read().decode())["data"]
    script = d["script"]
    first = script.split("\n", 1)[0]
    if not (first.startswith("# ") and d["name"] in first):
        script = "# " + d.get("script_type", d.get("type", "")) + " — " + d["name"] + "\n" + script
    with open(os.path.join(OUT, fname), "w", encoding="utf-8") as f:
        f.write(script)
    print("saved", fname, len(d["script"]), "chars")

# Query Reports: dump their SQL + filter declarations
reports = [
    ("GOSI Monthly Contribution Register", "gosi_register.sql"),
    ("KSA EOSB Liability Register", "eosb_register.sql"),
]
import urllib.parse
for rname, fname in reports:
    q = urllib.parse.quote(rname, safe="")
    r = opener.open("http://localhost:8080/api/resource/Report/" + q, timeout=30)
    d = json.loads(r.read().decode())["data"]
    filters = "\n".join(
        f"-- filter: {f.get('fieldname')} ({f.get('fieldtype')}) default={f.get('default') or ''}"
        for f in d.get("filters", []))
    head = f"-- Query Report — {rname}\n{filters}\n\n"
    with open(os.path.join(OUT, fname), "w", encoding="utf-8") as f:
        f.write(head + d.get("query", ""))
    print("saved", fname, len(d.get("query", "")), "chars")

# Print Format: dump the Jinja HTML for the installer
r = opener.open("http://localhost:8080/api/resource/Print%20Format/ZATCA%20Phase%201%20Invoice",
                timeout=30)
d = json.loads(r.read().decode())["data"]
with open(os.path.join(OUT, "zatca_print_format.html"), "w", encoding="utf-8") as f:
    f.write(d.get("html") or "")
print("saved zatca_print_format.html", len(d.get("html") or ""), "chars")
print("DONE")
