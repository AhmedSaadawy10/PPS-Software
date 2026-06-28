from odoo import models, fields, api
from odoo.tools.translate import _
import re


class PayrollStructure(models.Model):
    _name = 'payroll.structure'
    _description = 'Salary Structure'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    @api.model
    def _get_default_rule_ids(self):
        default_structure = self.env.ref('custom_payroll.default_payroll_structure', False)

        if not default_structure or not default_structure.rule_ids:
            return []

        vals = [
            (0, 0, {
                'name': rule.name,
                'code': rule.code,
                'sequence': rule.sequence,
                'category': rule.category,
                'amount_type': rule.amount_type,
                'amount_fix': rule.amount_fix,
                'amount_percentage': rule.amount_percentage,
                'amount_python_code': rule.amount_python_code,
                'condition_select': rule.condition_select,
                'condition_range_field': rule.condition_range_field,
                'condition_range_min': rule.condition_range_min,
                'condition_range_max': rule.condition_range_max,
                'condition_python_code': rule.condition_python_code,
            }) for rule in default_structure.rule_ids
        ]
        return vals

    name = fields.Char(string='Structure Name', required=True, tracking=True)
    code = fields.Char(string='Structure Code', required=True, tracking=True)
    active = fields.Boolean(default=True, tracking=True)
    note = fields.Text(string='Description')
    rule_ids = fields.One2many(
        'payroll.rule', 'struct_id',
        string='Salary Rules', copy=True, default=_get_default_rule_ids
    )

    _code_unique = models.Constraint(
        'unique(code)',
        'The Structure Code must be unique!'
    )

    @api.onchange('name')
    def _onchange_name_suggest_structure_code(self):
        if self.name:
            suggested_code = self.name.strip().upper()

            suggested_code = re.sub(r'[\s\-]+', '_', suggested_code)

            suggested_code = re.sub(r'[^A-Z0-9_]', '', suggested_code)

            self.code = suggested_code