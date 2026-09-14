# API — employer_gosi
# API — employer_gosi
# HRMS v16.18.1 gap: slip employer_contributions rows never reach the GL
# (make_accrual_jv_entry aggregates only earnings+deductions). This books the
# company-side GOSI liability per payroll run: Dr GOSI Expense / Cr GOSI Payable.
# Idempotent: one journal per payroll entry, matched by remark.

def rnd(v):
    return float(int(round(float(v or 0) * 100))) / 100

GOSI_EXPENSE = "GOSI Expense - ATE"
GOSI_PAYABLE = "2320 - GOSI Payable - ATE"

payroll_entry = frappe.form_dict.payroll_entry
pe = frappe.get_doc("Payroll Entry", payroll_entry)
if pe.docstatus != 1:
    frappe.throw("Payroll Entry must be submitted first")

remark = "Employer GOSI " + payroll_entry
existing = frappe.db.get_value("Journal Entry", {"remark": remark, "docstatus": 1}, "name")
if existing:
    res = {"status": "already_posted", "journal_entry": existing, "amount": 0}
else:
    slips = frappe.get_all("Salary Slip",
        filters={"payroll_entry": payroll_entry, "docstatus": 1}, pluck="name")
    total = 0.0
    breakdown = []
    for s in slips:
        d = frappe.get_doc("Salary Slip", s)
        emp_total = 0.0
        for row in d.get("employer_contributions"):
            emp_total += float(row.amount or 0)
        if emp_total:
            breakdown.append({"employee": d.employee_name, "amount": rnd(emp_total)})
        total += emp_total
    total = rnd(total)
    if not total:
        res = {"status": "no_employer_contributions", "amount": 0}
    else:
        cc = pe.cost_center or frappe.db.get_value("Company", pe.company, "cost_center")
        je = frappe.new_doc("Journal Entry")
        je.voucher_type = "Journal Entry"
        je.company = pe.company
        je.posting_date = pe.end_date
        je.remark = remark
        je.user_remark = remark
        je.party_not_required = 1  # same flag HRMS's payroll JV uses for the payable leg
        je.append("accounts", {"account": GOSI_EXPENSE,
            "debit_in_account_currency": total, "cost_center": cc, "remarks": remark})
        je.append("accounts", {"account": GOSI_PAYABLE,
            "credit_in_account_currency": total, "cost_center": cc, "remarks": remark})
        je.insert()
        je.submit()
        res = {"status": "posted", "journal_entry": je.name, "amount": total,
               "slips": len(slips), "breakdown": breakdown}
        frappe.db.commit()

frappe.response["result"] = res
