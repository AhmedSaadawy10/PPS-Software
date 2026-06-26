from odoo import models, fields, api
from odoo.tools.translate import _
import re


class PayrollStructure(models.Model):
    _name = 'payroll.structure'
    _description = 'Salary Structure'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Structure Name', required=True, tracking=True)
    code = fields.Char(string='Structure Code', required=True, tracking=True)
    active = fields.Boolean(default=True, tracking=True)
    note = fields.Text(string='Description')
    rule_ids = fields.One2many(
        'payroll.rule', 'struct_id',
        string='Salary Rules', copy=True, default=lambda self: self._get_default_rule_ids()
    )

    _sql_constraints = [
        ('code_unique', 'unique(code)', 'The Structure Code must be unique!')
    ]

    @api.model
    def _get_default_rule_ids(self):
        existing_rules = self.env['payroll.rule'].search([('active', '=', True)], limit=10)
        if not existing_rules:
            return []
        vals = []
        for rule in existing_rules:
            vals.append((0, 0, {
                'name': rule.name,
                'code': rule.code,
                'sequence': rule.sequence,
                'category': rule.category,
                'amount_type': rule.amount_type,
                'amount_fix': rule.amount_fix,
                'amount_percentage': rule.amount_percentage,
                'amount_python_code': rule.amount_python_code,
                'condition_field': rule.condition_field,
            }))
        return vals

    @api.onchange('name')
    def _onchange_name_suggest_structure_code(self):
        if self.name:
            suggested_code = self.name.strip().upper()

            suggested_code = re.sub(r'[\s\-]+', '_', suggested_code)

            suggested_code = re.sub(r'[^A-Z0-9_]', '', suggested_code)

            self.code = suggested_code