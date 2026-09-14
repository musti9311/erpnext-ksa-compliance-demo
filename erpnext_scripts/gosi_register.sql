-- Query Report — GOSI Monthly Contribution Register
-- filter: from_date (Date) default=2026-09-01
-- filter: end_date (Date) default=2026-09-30

SELECT
 e.gosi_membership_no AS `GOSI No`,
 e.employee_name AS `Employee`,
 e.nationality AS `Nationality`,
 (SELECT IFNULL(SUM(sd.amount),0) FROM `tabSalary Detail` sd WHERE sd.parent=ss.name AND sd.parentfield='earnings') AS `Gross Wage (Basic+Housing)`,
 (SELECT IFNULL(SUM(sd.amount),0) FROM `tabSalary Detail` sd WHERE sd.parent=ss.name AND sd.parentfield='deductions') AS `Employee Share`,
 (SELECT IFNULL(SUM(sd.amount),0) FROM `tabSalary Detail` sd WHERE sd.parent=ss.name AND sd.parentfield='employer_contributions') AS `Employer Share`,
 ss.name AS `Salary Slip:Link/Salary Slip`
FROM `tabSalary Slip` ss
JOIN `tabEmployee` e ON e.name = ss.employee
WHERE ss.docstatus = 1
 AND ss.start_date >= %(from_date)s
 AND ss.end_date <= %(end_date)s
ORDER BY e.employee_name