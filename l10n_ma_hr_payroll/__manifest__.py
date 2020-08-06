# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Moroccan Payroll',
    'category': 'Human  Resources',
    'depends': ['hr_payroll'],
    'description': """
Moroccan Payroll Salary Rules.
============================

    -Configuration of hr_payroll for Morocco localization
    -All main contributions rules for Morocco payslip.
    * New payslip report
    * Employee Contracts
    * Allow to configure Basic / Gross / Net Salary
    * Employee PaySlip
    * Allowance / Deduction
    * Integrated with Leaves Management
    - Payroll Advice and Report
    - Yearly Salary by Head and Yearly Salary by Employee Report
    """,
    'data': [
         'views/l10n_ma_hr_payroll_view.xml',
         'data/l10n_ma_hr_payroll_data.xml',
         'security/ir.model.access.csv',
         'views/l10n_ma_hr_payroll_report.xml',
         'views/report_payroll_payslip_template.xml',
         'data/l10n_ma_hr_payroll_sequence_data.xml',
         'views/report_payslip_details_template.xml',
         'report/payment_advice_report_view.xml',
         'report/payslip_report_view.xml',
         'views/report_payroll_advice_template.xml',
     ],
    'demo': [],
}
