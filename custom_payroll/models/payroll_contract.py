from odoo import models, fields, api
from odoo.tools.translate import _
from odoo.exceptions import ValidationError


class PayrollContract(models.Model):
    _name = 'x_payroll.contract'
    _description = 'Payroll Contract'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Contract Reference', required=True, copy=False,
                       default=lambda self: _('New'), tracking=True)
    employee_id = fields.Many2one('hr.employee', string='Employee', index=True, required=True, ondelete='cascade', tracking=True)
    date_start = fields.Date(string='Start Date', required=True, default=fields.Date.today, tracking=True)
    date_end = fields.Date(string='End Date', tracking=True)
    wage = fields.Monetary(
        string='Wage',
        required=True,
        tracking=True,
        help="Employee's monthly gross wage.",
        group_operator="avg"
    )
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company)
    currency_id = fields.Many2one('res.currency', related='company_id.currency_id')

    state = fields.Selection([
        ('draft', 'Draft'),
        ('running', 'Running'),
        ('expired', 'Expired'),
        ('cancelled', 'Cancelled')
    ], string='Status', default='draft', tracking=True, required=True)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('x_payroll.contract') or _('New')
        return super(PayrollContract, self).create(vals_list)

    @api.constrains('date_start', 'date_end')
    def _check_contract_dates(self):
        for contract in self:
            if contract.date_end and contract.date_start > contract.date_end:
                raise ValidationError(_('The contract start date cannot be later than its end date.'))