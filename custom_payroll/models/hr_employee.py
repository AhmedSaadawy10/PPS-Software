from odoo import models, fields, api
from odoo.tools.translate import _


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    payslip_count = fields.Integer(compute='_compute_payslip_count', string="Payslips")
    contract_count = fields.Integer(compute='_compute_contract_count', string="Contracts")

    def _compute_payslip_count(self):
        for employee in self:
            employee.payslip_count = self.env['payroll.payslip'].search_count([
                ('employee_id', '=', employee.id)
            ])

    def _compute_contract_count(self):
        for employee in self:
            employee.contract_count = self.env['x_payroll.contract'].search_count([
                ('employee_id', '=', employee.id)
            ])

    def action_view_employee_payslips(self):
        self.ensure_one()
        return {
            'name': _('Employee Payslips'),
            'type': 'ir.actions.act_window',
            'res_model': 'payroll.payslip',
            'view_mode': 'list,form',
            'domain': [('employee_id', '=', self.id)],
            'context': {'default_employee_id': self.id},
        }

    def action_view_employee_contracts(self):
        self.ensure_one()
        return {
            'name': _('Employee Contracts'),
            'type': 'ir.actions.act_window',
            'res_model': 'x_payroll.contract',
            'view_mode': 'list,form',
            'domain': [('employee_id', '=', self.id)],
            'context': {'default_employee_id': self.id},
        }