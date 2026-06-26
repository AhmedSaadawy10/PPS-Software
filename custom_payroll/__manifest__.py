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
        'security/security.xml',
        'security/ir.model.access.csv',
        'views/menus.xml',
        'views/payroll_contract_views.xml',
        'views/payroll_rules_views.xml',
        'views/payroll_structure_views.xml',
        'views/payroll_payslip_views.xml',
    ],
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}