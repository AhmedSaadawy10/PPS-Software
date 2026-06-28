# -*- coding: utf-8 -*-
from odoo import models, fields


class PayrollPayslipWorkedDays(models.Model):
    _name = 'payroll.payslip.worked_days'
    _description = 'Payslip Worked Days'
    _order = 'sequence, id'

    payslip_id = fields.Many2one('payroll.payslip', string='Payslip', ondelete='cascade', required=True, index=True)
    name = fields.Char(string='Description', required=True)
    code = fields.Char(string='Code', required=True)
    number_of_days = fields.Float(string='Number of Days', default=0.0)
    number_of_hours = fields.Float(string='Number of Hours', default=0.0)
    sequence = fields.Integer(string='Sequence', default=10)
