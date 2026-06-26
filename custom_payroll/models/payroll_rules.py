from odoo import models, fields, api
from odoo.tools.translate import _
import re


class PayrollRule(models.Model):
    _name = 'payroll.rule'
    _description = 'Salary Rule'
    _order = 'sequence, id'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Rule Name', required=True, tracking=True)
    code = fields.Char(string='Rule Code', required=True, tracking=True)
    struct_id = fields.Many2one('payroll.structure', string="Salary Structure", ondelete='cascade')
    sequence = fields.Integer(string='Sequence', default=5, required=True, index=True)
    active = fields.Boolean(default=True)

    category = fields.Selection([
        ('basic', 'Basic'),
        ('allowance', 'Allowance'),
        ('deduction', 'Deduction'),
        ('gross', 'Gross'),
        ('net', 'Net')
    ], string='Category', required=True, default='basic', tracking=True)

    amount_type = fields.Selection([
        ('fixed', 'Fixed'),
        ('percentage', 'Percentage of wage'),
        ('code', 'Python code'),
    ], string='Amount Type', required=True, default='fixed', tracking=True)

    amount_fix = fields.Float(string='Fixed Amount', digits=(16, 2))
    amount_percentage = fields.Float(string='Percentage of Wage (%)')
    amount_python_code = fields.Text(string='Python Code', default="result = 0.0")

    condition_select = fields.Selection([
        ('always', 'Always True'),
        ('range', 'Range Check'),
        ('python', 'Python Expression')
    ], string='Condition Type', default='always', required=True, tracking=True)
    condition_range_field = fields.Char(string='Range Field', default='contract.wage', tracking=True)
    condition_range_min = fields.Float(string='Minimum Range', tracking=True)
    condition_range_max = fields.Float(string='Maximum Range', tracking=True)
    condition_python_code = fields.Text(string='Python Condition Code', default="result = True")

    _sql_constraints = [
        ('code_unique', 'unique(code)', 'The Rule Code must be unique across the payroll system!')
    ]

    @api.onchange('name')
    def _onchange_name_suggest_code(self):
        if self.name:
            suggested_code = self.name.strip().upper()

            suggested_code = re.sub(r'[\s\-]+', '_', suggested_code)

            suggested_code = re.sub(r'[^A-Z0-9_]', '', suggested_code)

            self.code = suggested_code