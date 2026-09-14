-- Query Report — KSA EOSB Liability Register
-- filter: as_of (Date) default=2026-09-30
-- filter: company (Link) default=Al-Rehab Trading Est.

SELECT
 e.employee_name AS `Employee`,
 e.nationality AS `Nationality`,
 e.date_of_joining AS `Joined`,
 ROUND(TIMESTAMPDIFF(DAY, e.date_of_joining, %(as_of)s)/365.0, 2) AS `Service Years`,
 ROUND(a.base*1.25, 2) AS `Last Wage (SAR)`,
 ROUND(CASE WHEN TIMESTAMPDIFF(YEAR, e.date_of_joining, %(as_of)s) < 5
     THEN TIMESTAMPDIFF(DAY, e.date_of_joining, %(as_of)s)/365.0 * 0.5
     ELSE 2.5 + (TIMESTAMPDIFF(DAY, e.date_of_joining, %(as_of)s)/365.0 - 5) * 1.0 END, 2) AS `Accrued Months`,
 ROUND(CASE WHEN TIMESTAMPDIFF(YEAR, e.date_of_joining, %(as_of)s) < 5
     THEN TIMESTAMPDIFF(DAY, e.date_of_joining, %(as_of)s)/365.0 * 0.5
     ELSE 2.5 + (TIMESTAMPDIFF(DAY, e.date_of_joining, %(as_of)s)/365.0 - 5) * 1.0 END
     * a.base*1.25, 2) AS `EOSB Liability (SAR)`
FROM `tabEmployee` e
JOIN `tabSalary Structure Assignment` a ON a.employee = e.name AND a.docstatus = 1
WHERE e.company = %(company)s AND e.nationality != 'Saudi Arabia' AND e.status = 'Active'
ORDER BY e.employee_name