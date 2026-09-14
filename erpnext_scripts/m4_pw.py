import frappe
from frappe.utils.password import update_password
for u in ["purchase.manager@alrehab-demo.example", "accounts.manager@alrehab-demo.example"]:
    update_password(user=u, pwd="demo123")
    print("pw set", u)
frappe.db.commit()
print("PW DONE")
