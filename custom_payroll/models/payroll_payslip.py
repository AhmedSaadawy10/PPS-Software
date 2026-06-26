from odoo import models, fields, api
from odoo.tools.translate import _
from odoo.exceptions import ValidationError
from odoo.tools.safe_eval import safe_eval
from dateutil.relativedelta import relativedelta


class PayrollPayslip(models.Model):
    _name = 'payroll.payslip'
    _description = 'Employee Payslip'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date_from desc, id desc'

    name = fields.Char(string='Reference', required=True, copy=False, readonly=True, default='New')

    employee_id = fields.Many2one('hr.employee', string='Employee', required=True, tracking=True)
    contract_id = fields.Many2one('x_payroll.contract', string='Contract', tracking=True)
    structure_id = fields.Many2one('payroll.structure', string='Salary Structure')

    def _get_default_date_to(self):
        return fields.Date.context_today(self) + relativedelta(months=1)
    date_from = fields.Date(string='From', required=True, default=fields.Date.context_today, readonly=True)
    date_to = fields.Date(string='To', required=True, default=_get_default_date_to, readonly=True)

    state = fields.Selection([
        ('draft', 'Draft'),
        ('verify', 'Computed'),
        ('done', 'Done'),
        ('cancel', 'Canceled')
    ], string='Status', index=True, readonly=True, default='draft', tracking=True)

    line_ids = fields.One2many('payroll.payslip.line', 'payslip_id', string='Payslip Lines', readonly=True)
    gross_total = fields.Float(string='Gross Total', readonly=True, tracking=True)
    net_total = fields.Float(string='Net Total', readonly=True, tracking=True)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('payroll.payslip') or 'New'
        return super(PayrollPayslip, self).create(vals_list)

    @api.onchange('date_from')
    def _onchange_date_from(self):
        if self.date_from:
            self.date_to = self.date_from + relativedelta(months=1)

    def action_payslip_verify(self):
        self.compute_sheet()
        self.write({'state': 'verify'})

    def action_payslip_done(self):
        self.write({'state': 'done'})

    def action_payslip_cancel(self):
        self.write({'state': 'cancel'})

    def action_payslip_draft(self):
        for payslip in self:
            payslip.line_ids.unlink()
            payslip.write({
                'state': 'draft',
                'gross_total': 0.0,
                'net_total': 0.0
            })

    def compute_sheet(self):
        for payslip in self:
            if not payslip.contract_id:
                raise ValidationError(_("No active contract found for employee: %s") % payslip.employee_id.name)
            if not payslip.structure_id:
                raise ValidationError(_("No salary structure linked to this contract!"))

            #  (Recompute Criteria)
            payslip.line_ids.unlink()

            #  safe_eval (Evaluation Context)
            rules_dict = {}
            categories_dict = {
                'basic': 0.0,
                'allowance': 0.0,
                'deduction': 0.0,
                'gross': 0.0,
                'net': 0.0
            }

            eval_context = {
                'contract': payslip.contract_id,
                'payslip': payslip,
                'rules': rules_dict,
                'categories': categories_dict,
                'result': None,
            }

            lines_to_create = []

            sorted_rules = payslip.structure_id.rule_ids.sorted(key=lambda r: r.sequence)

            for rule in sorted_rules:
                amount = 0.0

                if rule.amount_type == 'fixed':
                    amount = rule.amount_fix

                elif rule.amount_type == 'percentage':
                    amount = payslip.contract_id.wage * (rule.amount_percentage / 100.0)

                elif rule.amount_type == 'code':
                    if not rule.amount_python_code:
                        continue
                    try:
                        safe_eval(rule.amount_python_code, eval_context)
                        amount = float(eval_context.get('result', 0.0))
                    except ZeroDivisionError:
                        amount = 0.0
                    except Exception as e:
                        raise ValidationError(_("Error in Python Code of rule [%s]: %s") % (rule.name, str(e)))

                rules_dict[rule.code] = amount
                if rule.category in categories_dict:
                    categories_dict[rule.category] += amount

                if rule.category in ['basic', 'allowance']:
                    categories_dict['gross'] += amount
                    categories_dict['net'] += amount
                elif rule.category == 'deduction':
                    categories_dict['net'] -= amount

                lines_to_create.append((0, 0, {
                    'name': rule.name,
                    'code': rule.code,
                    'sequence': rule.sequence,
                    'category': rule.category,
                    'total': amount
                }))

            if lines_to_create:
                payslip.write({'line_ids': lines_to_create,
                               'gross_total': categories_dict['gross'],
                               'net_total': categories_dict['net']})

        return True


class PayrollPayslipLine(models.Model):
    _name = 'payroll.payslip.line'
    _description = 'Payslip Line'
    _order = 'sequence, id'

    payslip_id = fields.Many2one('payroll.payslip', string='Payslip', ondelete='cascade', required=True)
    name = fields.Char(string='Rule Name', required=True)
    code = fields.Char(string='Code', required=True)
    sequence = fields.Integer(string='Sequence', default=5)

    category = fields.Selection([
        ('basic', 'Basic'),
        ('allowance', 'Allowance'),
        ('deduction', 'Deduction'),
        ('gross', 'Gross'),
        ('net', 'Net')
    ], string='Category', required=True)

    total = fields.Float(string='Total', digits=(16, 2))
