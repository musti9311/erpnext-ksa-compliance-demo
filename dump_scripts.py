"""Dump the 3 ERPNext scripts (server + client) from the live instance into erpnext_scripts/."""
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
]
for path, fname in jobs:
    r = opener.open("http://localhost:8080/api/resource/" + path, timeout=30)
    d = json.loads(r.read().decode())["data"]
    header = "# " + d.get("script_type", d.get("type", "")) + " — " + d["name"] + "\n"
    with open(os.path.join(OUT, fname), "w", encoding="utf-8") as f:
        f.write(header + d["script"])
    print("saved", fname, len(d["script"]), "chars")
print("DONE")
