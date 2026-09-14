# API — eosb_accrue
# API - eosb_accrue
# Posts the monthly EOSB accrual for expat employees: Dr 5130 EOSB Expense / Cr 2330 EOSB
# Liability. Tier by completed years at period end: <5yr = wage*0.5/12 per month, >=5yr = wage/12.
# Idempotent per period (remark key). wage = SSA base * 1.25 (basic + housing).

def rnd(v):
    return float(int(round(float(v or 0) * 100))) / 100

period_end = frappe.form_dict.period_end
company = frappe.form_dict.company or "Al-Rehab Trading Est."
remark = "EOSB accrual " + str(period_end)

existing = frappe.db.get_value("Journal Entry", {"remark": remark, "docstatus": 1}, "name")
if existing:
    res = {"status": "already_posted", "journal_entry": existing, "amount": 0}
else:
    rows = frappe.db.sql("""SELECT e.employee_name, a.base,
        TIMESTAMPDIFF(YEAR, e.date_of_joining, %(pe)s) AS yrs
        FROM `tabEmployee` e
        JOIN `tabSalary Structure Assignment` a ON a.employee = e.name AND a.docstatus = 1
        WHERE e.company = %(co)s AND e.nationality != 'Saudi Arabia' AND e.status = 'Active' AND e.date_of_joining <= %(pe)s""",
        {"pe": period_end, "co": company}, as_dict=1)
    total = 0.0
    detail = []
    for r in rows:
        wage = float(r["base"]) * 1.25
        monthly = (wage * 0.5 / 12.0) if int(r["yrs"]) < 5 else (wage / 12.0)
        monthly = rnd(monthly)
        detail.append({"employee": r["employee_name"], "accrual": monthly})
        total += monthly
    total = rnd(total)
    cc = frappe.db.get_value("Company", company, "cost_center") or "Main - ATE"
    je = frappe.new_doc("Journal Entry")
    je.voucher_type = "Journal Entry"
    je.company = company
    je.posting_date = period_end
    je.remark = remark
    je.user_remark = remark
    je.party_not_required = 1
    je.append("accounts", {"account": "EOSB Expense - ATE", "debit_in_account_currency": total, "cost_center": cc, "remarks": remark})
    je.append("accounts", {"account": "2330 - EOSB Liability - ATE", "credit_in_account_currency": total, "cost_center": cc, "remarks": remark})
    je.insert()
    je.submit()
    frappe.db.commit()
    res = {"status": "posted", "journal_entry": je.name, "amount": total, "employees": detail}

frappe.response["result"] = res
