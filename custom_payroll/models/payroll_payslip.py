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
    payroll_run_id = fields.Many2one('payroll.run', string='Payroll Run', ondelete='cascade', index=True)

    def _get_default_date_to(self):
        return fields.Date.context_today(self) + relativedelta(months=1)

    date_from = fields.Date(string='From', required=True, default=fields.Date.context_today)
    date_to = fields.Date(string='To', required=True, default=_get_default_date_to)

    state = fields.Selection([
        ('draft', 'Draft'),
        ('verify', 'Computed'),
        ('done', 'Done'),
        ('cancel', 'Canceled')
    ], string='Status', index=True, readonly=True, default='draft', tracking=True)

    line_ids = fields.One2many('payroll.payslip.line', 'payslip_id', string='Payslip Lines', readonly=True)
    worked_days_line_ids = fields.One2many('payroll.payslip.worked_days', 'payslip_id', string='Worked Days Lines',
                                           copy=True)
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

    @api.constrains('date_from', 'date_to')
    def _check_payslip_dates(self):
        for payslip in self:
            if payslip.date_from and payslip.date_to and payslip.date_from > payslip.date_to:
                raise ValidationError(_("The payslip start date (From) cannot be after its end date (To)."))

    @api.onchange('employee_id', 'date_from', 'date_to')
    def _onchange_employee_id(self):
        for payslip in self:
            if not payslip.employee_id:
                payslip.contract_id = False
                continue

            domain = [
                ('employee_id', '=', payslip.employee_id.id),
                ('state', '=', 'running'),
            ]
            if payslip.date_from:
                domain.append('|')
                domain.append(('date_end', '>=', payslip.date_from))
                domain.append(('date_end', '=', False))
            if payslip.date_to:
                domain.append(('date_start', '<=', payslip.date_to))

            contract = self.env['x_payroll.contract'].search(domain, limit=1)
            if contract:
                payslip.contract_id = contract.id
            else:
                contract = self.env['x_payroll.contract'].search([
                    ('employee_id', '=', payslip.employee_id.id),
                    ('state', '=', 'running')
                ], limit=1)
                if contract:
                    payslip.contract_id = contract.id
                else:
                    payslip.contract_id = False

            if not payslip.structure_id:
                structure = self.env['payroll.structure'].search([('active', '=', True)], limit=1)
                if structure:
                    payslip.structure_id = structure.id

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

    def _compute_worked_days(self):
        from datetime import timedelta
        for payslip in self:
            # Delete old worked days
            payslip.worked_days_line_ids.unlink()
            if not payslip.date_from or not payslip.date_to:
                continue

            # 1. Count standard weekdays (Mon-Fri) in payslip range
            d_from = payslip.date_from
            d_to = payslip.date_to
            standard_days = 0
            curr = d_from
            while curr <= d_to:
                if curr.weekday() < 5:
                    standard_days += 1
                curr += timedelta(days=1)

            # 2. Count approved leaves (if hr.leave is installed)
            leave_days = 0.0
            if 'hr.leave' in self.env:
                leaves = self.env['hr.leave'].search([
                    ('employee_id', '=', payslip.employee_id.id),
                    ('state', '=', 'validate'),
                    ('date_from', '<=', fields.Datetime.to_datetime(d_to)),
                    ('date_to', '>=', fields.Datetime.to_datetime(d_from)),
                ])
                for leave in leaves:
                    # Parse as date objects to count weekdays in intersection
                    leave_start = fields.Datetime.to_datetime(leave.date_from).date()
                    leave_end = fields.Datetime.to_datetime(leave.date_to).date()
                    start_intersection = max(leave_start, d_from)
                    end_intersection = min(leave_end, d_to)
                    if start_intersection <= end_intersection:
                        curr_l = start_intersection
                        while curr_l <= end_intersection:
                            if curr_l.weekday() < 5:
                                leave_days += 1.0
                            curr_l += timedelta(days=1)

            # 3. Count attendances (if hr.attendance is installed)
            attendance_hours = 0.0
            if 'hr.attendance' in self.env:
                attendances = self.env['hr.attendance'].search([
                    ('employee_id', '=', payslip.employee_id.id),
                    ('check_in', '>=', fields.Datetime.to_datetime(d_from)),
                    ('check_in', '<=', fields.Datetime.to_datetime(d_to)),
                ])
                for att in attendances:
                    if att.check_out:
                        diff = att.check_out - att.check_in
                        attendance_hours += diff.total_seconds() / 3600.0

            # 4. Prepare lines
            worked_vals = []

            # Normal worked days (WORK100)
            work_days = max(0.0, standard_days - leave_days)
            worked_vals.append({
                'payslip_id': payslip.id,
                'name': _('Normal Working Days'),
                'code': 'WORK100',
                'number_of_days': work_days,
                'number_of_hours': work_days * 8.0,
                'sequence': 1,
            })

            # Leaves (LEAVE)
            if leave_days > 0:
                worked_vals.append({
                    'payslip_id': payslip.id,
                    'name': _('Leaves'),
                    'code': 'LEAVE',
                    'number_of_days': leave_days,
                    'number_of_hours': leave_days * 8.0,
                    'sequence': 5,
                })

            # Attendances (ATTENDANCE)
            if attendance_hours > 0:
                worked_vals.append({
                    'payslip_id': payslip.id,
                    'name': _('Attendance Hours'),
                    'code': 'ATTENDANCE',
                    'number_of_days': attendance_hours / 8.0,
                    'number_of_hours': attendance_hours,
                    'sequence': 10,
                })

            self.env['payroll.payslip.worked_days'].create(worked_vals)

    def _get_prorated_basic_wage(self):
        self.ensure_one()
        if not self.contract_id:
            return 0.0

        # 1. Determine base wage per pay frequency
        freq = self.contract_id.schedule_pay or 'monthly'
        monthly_wage = self.contract_id.wage
        if freq == 'weekly':
            base_wage = (monthly_wage * 12.0) / 52.0
        elif freq == 'bi-weekly':
            base_wage = (monthly_wage * 12.0) / 26.0
        elif freq == 'semi-monthly':
            base_wage = monthly_wage / 2.0
        else:  # monthly
            base_wage = monthly_wage

        # 2. Prorate based on standard working days vs worked days in the period
        work_line = self.worked_days_line_ids.filtered(lambda l: l.code == 'WORK100')
        actual_work_days = sum(work_line.mapped('number_of_days'))

        # Calculate standard weekdays in period
        from datetime import timedelta
        d_from = self.date_from
        d_to = self.date_to
        standard_days = 0
        curr = d_from
        while curr <= d_to:
            if curr.weekday() < 5:
                standard_days += 1
            curr += timedelta(days=1)

        if standard_days > 0:
            return base_wage * (actual_work_days / standard_days)
        return base_wage

    def compute_sheet(self):
        self.mapped('line_ids').unlink()

        # Compute/recompute worked days for all payslips
        self._compute_worked_days()

        lines_vals = []

        # Helper classes for safe eval context
        class WorkedDaysWrapper:
            def __init__(self, number_of_days, number_of_hours):
                self.number_of_days = number_of_days
                self.number_of_hours = number_of_hours

        class WorkedDaysDict(dict):
            def __getattr__(self, name):
                if name in self:
                    return self[name]
                return WorkedDaysWrapper(0.0, 0.0)

            def __getitem__(self, name):
                if name in self:
                    return super().__getitem__(name)
                return WorkedDaysWrapper(0.0, 0.0)

        for payslip in self:
            if not payslip.contract_id:
                raise ValidationError(_("No active contract found for employee: %s") % payslip.employee_id.name)
            if not payslip.structure_id:
                raise ValidationError(
                    _("No salary structure linked to contract/payslip for employee: %s") % payslip.employee_id.name)

            rules_dict = {}

            # Calculate prorated basic wage according to pay frequency and worked days
            prorated_basic = payslip._get_prorated_basic_wage()

            categories_dict = {
                'basic': prorated_basic,
                'allowance': 0.0,
                'deduction': 0.0,
                'gross': 0.0,
                'net': 0.0
            }

            worked_days_dict = WorkedDaysDict()
            for wd in payslip.worked_days_line_ids:
                worked_days_dict[wd.code] = WorkedDaysWrapper(wd.number_of_days, wd.number_of_hours)

            eval_context = {
                'contract': payslip.contract_id,
                'payslip': payslip,
                'rules': rules_dict,
                'categories': categories_dict,
                'worked_days': worked_days_dict,
                'result': 0.0,
            }

            sorted_rules = payslip.structure_id.rule_ids.sorted(key=lambda r: r.sequence)

            for rule in sorted_rules:
                is_applicable = True

                if rule.condition_select == 'range':
                    try:
                        val = safe_eval(rule.condition_range_field, eval_context)
                        val = float(val or 0.0)
                        is_applicable = (rule.condition_range_min <= val <= rule.condition_range_max)
                    except Exception:
                        is_applicable = False
                elif rule.condition_select == 'python':
                    if rule.condition_python_code:
                        local_context = dict(eval_context)
                        try:
                            code = rule.condition_python_code.strip()
                            if '=' in code and not any(
                                    code.startswith(prefix) for prefix in ['contract.', 'payslip.', 'categories.']):
                                safe_eval(code, local_context, mode='exec')
                                is_applicable = bool(local_context.get('result', False))
                            else:
                                res = safe_eval(code, local_context, mode='eval')
                                is_applicable = bool(res)
                        except Exception:
                            is_applicable = False

                if not is_applicable:
                    continue

                amount = 0.0

                if rule.amount_type == 'fixed':
                    amount = rule.amount_fix

                elif rule.amount_type == 'percentage':
                    amount = categories_dict['basic'] * (rule.amount_percentage / 100.0)

                elif rule.amount_type == 'code':
                    if not rule.amount_python_code:
                        continue
                    local_context = dict(eval_context)
                    local_context['result'] = 0.0
                    try:
                        safe_eval(rule.amount_python_code, local_context, mode='exec')
                        amount = float(local_context.get('result', 0.0))
                    except ZeroDivisionError:
                        amount = 0.0
                    except Exception as e:
                        raise ValidationError(_("Error in Python Code of rule [%s]: %s") % (rule.name, str(e)))

                rules_dict[rule.code] = amount

                if rule.category == 'basic':
                    categories_dict['basic'] = amount
                elif rule.category == 'allowance':
                    categories_dict['allowance'] += amount
                elif rule.category == 'deduction':
                    categories_dict['deduction'] += amount

                categories_dict['gross'] = categories_dict['basic'] + categories_dict['allowance']
                categories_dict['net'] = categories_dict['gross'] - categories_dict['deduction']

                line_total = amount
                if rule.category == 'gross':
                    line_total = categories_dict['gross']
                elif rule.category == 'net':
                    line_total = categories_dict['net']

                lines_vals.append({
                    'payslip_id': payslip.id,
                    'name': rule.name,
                    'code': rule.code,
                    'sequence': rule.sequence,
                    'category': rule.category,
                    'total': line_total
                })

            payslip.write({
                'gross_total': categories_dict['gross'],
                'net_total': categories_dict['net']
            })

        if lines_vals:
            self.env['payroll.payslip.line'].create(lines_vals)

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
