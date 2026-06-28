# -*- coding: utf-8 -*-
{
    'name': 'Custom Payroll Management',
    'version': '19.0.1.0.0',
    'category': 'Human Resources',
    'summary': 'Standalone Payroll Engine for Odoo 19 Community Edition',
    'author': 'Ahmed Saadawy',
    'depends': ['hr'],
    'data': [
        'data/ir_sequence.xml',
        'data/payroll_data.xml',
        'security/security.xml',
        'security/ir.model.access.csv',
        'views/menus.xml',
        'views/payroll_contract_views.xml',
        'views/payroll_rules_views.xml',
        'views/payroll_structure_views.xml',
        'views/payroll_payslip_views.xml',
        'views/payroll_run_views.xml',
        'views/hr_employee_views.xml',
        'report/payroll_report.xml',
        'report/payroll_payslip_report_template.xml',
    ],
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
    'assets': {
        'web.assets_backend': [
            'custom_payroll/static/src/components/payroll_summary/payroll_summary.js',
            'custom_payroll/static/src/components/payroll_summary/payroll_summary.xml',
        ],
    },
}
