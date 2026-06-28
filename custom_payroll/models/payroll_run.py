# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.tools.translate import _
from odoo.exceptions import ValidationError


class PayrollRun(models.Model):
    _name = 'payroll.run'
    _description = 'Payroll Batch Run'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date_start desc, id desc'

    name = fields.Char(string='Name', required=True, tracking=True)
    date_start = fields.Date(string='Start Date', required=True, default=fields.Date.context_today, tracking=True)
    date_end = fields.Date(string='End Date', required=True, default=fields.Date.context_today, tracking=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('verify', 'Verify'),
        ('done', 'Done'),
        ('close', 'Closed')
    ], string='Status', index=True, readonly=True, default='draft', tracking=True)

    payslip_ids = fields.One2many('payroll.payslip', 'payroll_run_id', string='Payslips')
    payslip_count = fields.Integer(compute='_compute_payslip_count', string="Payslips Count")

    employee_ids = fields.Many2many('hr.employee', 'payroll_run_employee_rel', 'run_id', 'employee_id',
                                    string='Employees',
                                    help='Select specific employees to generate payslips for. Leave empty to generate for all employees with active contracts.')

    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company)
    currency_id = fields.Many2one('res.currency', related='company_id.currency_id')

    # Aggregated fields for OWL Dashboard (Phase 3 requirements)
    total_employees = fields.Integer(string='Total Employees', compute='_compute_totals')
    total_gross = fields.Monetary(string='Total Gross', compute='_compute_totals', currency_field='currency_id')
    total_deductions = fields.Monetary(string='Total Deductions', compute='_compute_totals',
                                       currency_field='currency_id')
    total_net = fields.Monetary(string='Total Net', compute='_compute_totals', currency_field='currency_id')

    @api.depends('payslip_ids')
    def _compute_payslip_count(self):
        for run in self:
            run.payslip_count = len(run.payslip_ids)

    @api.constrains('date_start', 'date_end')
    def _check_run_dates(self):
        for run in self:
            if run.date_start and run.date_end and run.date_start > run.date_end:
                raise ValidationError(_("The payroll run start date cannot be after its end date."))

    def action_view_payslips(self):
        self.ensure_one()
        return {
            'name': _('Payslips'),
            'type': 'ir.actions.act_window',
            'res_model': 'payroll.payslip',
            'view_mode': 'list,form',
            'domain': [('payroll_run_id', '=', self.id)],
            'context': {'default_payroll_run_id': self.id},
        }

    @api.depends('payslip_ids', 'payslip_ids.gross_total', 'payslip_ids.net_total', 'payslip_ids.line_ids.total')
    def _compute_totals(self):
        for run in self:
            run.total_employees = len(run.payslip_ids)
            run.total_gross = sum(run.payslip_ids.mapped('gross_total'))
            run.total_net = sum(run.payslip_ids.mapped('net_total'))
            # Total deductions = Gross - Net
            run.total_deductions = run.total_gross - run.total_net

    def action_draft(self):
        for run in self:
            run.payslip_ids.action_payslip_draft()
        self.write({'state': 'draft'})

    def action_verify(self):
        self.write({'state': 'verify'})

    def action_done(self):
        for run in self:
            run.payslip_ids.action_payslip_done()
        self.write({'state': 'done'})

    def action_close(self):
        for run in self:
            run.payslip_ids.filtered(lambda p: p.state != 'done').write({'state': 'done'})
        self.write({'state': 'close'})

    def action_print_payslips(self):
        self.ensure_one()
        if not self.payslip_ids:
            raise ValidationError(_("There are no payslips to print for this batch."))

        return self.env.ref('custom_payroll.action_report_payslip').report_action(self.payslip_ids)

    def action_generate_payslips(self):
        for run in self:
            domain = [
                ('state', '=', 'running'),
                ('date_start', '<=', run.date_end),
                '|',
                ('date_end', '>=', run.date_start),
                ('date_end', '=', False),
            ]
            if run.employee_ids:
                domain.append(('employee_id', 'in', run.employee_ids.ids))

            contracts = self.env['x_payroll.contract'].search(domain)
            if not contracts:
                raise ValidationError(_("No running contracts found for the selected period/employees."))

            default_structure = self.env['payroll.structure'].search([('active', '=', True)], limit=1)

            payslip_vals = []
            existing_employees = run.payslip_ids.mapped('employee_id').ids

            for contract in contracts:
                if contract.employee_id.id in existing_employees:
                    continue

                structure_id = False
                if hasattr(contract, 'structure_id') and contract.structure_id:
                    structure_id = contract.structure_id.id
                elif default_structure:
                    structure_id = default_structure.id

                if not structure_id:
                    raise ValidationError(_("No active salary structure found for employee %s or contract %s!") % (
                        contract.employee_id.name, contract.name))

                payslip_vals.append({
                    'name': _('Payslip for %s') % contract.employee_id.name,
                    'employee_id': contract.employee_id.id,
                    'contract_id': contract.id,
                    'structure_id': structure_id,
                    'date_from': run.date_start,
                    'date_to': run.date_end,
                    'payroll_run_id': run.id,
                    'state': 'draft',
                })

            if payslip_vals:
                self.env['payroll.payslip'].create(payslip_vals)

            # Recompute and verify all payslips (both existing and newly created) in the batch
            run.payslip_ids.action_payslip_verify()

            run.write({'state': 'verify'})
        return True
