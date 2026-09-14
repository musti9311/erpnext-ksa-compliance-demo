import frappe
for u in ["purchase.manager@alrehab-demo.example", "accounts.manager@alrehab-demo.example"]:
    rows = frappe.db.sql("select name, left(password,20) as pw, version from `__Auth` where name=%s", (u,), as_dict=True)
    print("AUTH", u.split("@")[0], rows)
from frappe.utils.password import check_password
for u in ["purchase.manager@alrehab-demo.example", "accounts.manager@alrehab-demo.example"]:
    try:
        check_password(u, "demo123"); print("CHECK_OK", u.split("@")[0])
    except Exception as e:
        print("CHECK_FAIL", u.split("@")[0], type(e).__name__, str(e)[:100])
