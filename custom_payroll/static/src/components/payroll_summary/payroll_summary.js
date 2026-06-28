import { registry } from "@web/core/registry";
import { standardWidgetProps } from "@web/views/widgets/standard_widget_props";
import { Component } from "@odoo/owl";

export class PayrollSummaryWidget extends Component {
    static template = "custom_payroll.PayrollSummary";
    static props = {
        ...standardWidgetProps,
    };

    get totalEmployees() {
        return this.props.record.data.total_employees || 0;
    }

    get totalGross() {
        return this.formatCurrency(this.props.record.data.total_gross || 0);
    }

    get totalDeductions() {
        return this.formatCurrency(this.props.record.data.total_deductions || 0);
    }

    get totalNet() {
        return this.formatCurrency(this.props.record.data.total_net || 0);
    }

    formatCurrency(value) {
        if (!value) return "0.00";
        return value.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    }
}

export const payrollSummaryWidget = {
    component: PayrollSummaryWidget,
};

registry.category("view_widgets").add("payroll_summary", payrollSummaryWidget);
