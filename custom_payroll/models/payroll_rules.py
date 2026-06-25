from odoo import models, fields, api
from odoo.tools.translate import _


class PayrollRule(models.Model):
    _name = 'payroll.rule'
    _description = 'Salary Rule'
    _order = 'sequence, id'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Rule Name', required=True, tracking=True)
    code = fields.Char(string='Rule Code', required=True, tracking=True)
    struct_id = fields.Many2one('payroll.structure', string="Salary Structure", required=True, ondelete='cascade')
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

    # حقل الشرط الصريح والوحيد المطلوب لتحديد هل تطبق القاعدة أم لا
    condition_field = fields.Text(
        string='Condition (Python Code)',
        required=True,
        default="result = True",
        help="Python expression to decide if the rule applies. Must set 'result' to True or False."
    )

    _sql_constraints = [
        ('code_unique', 'unique(code)', 'The Rule Code must be unique across the payroll system!')
    ]