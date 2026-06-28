# PPS-Software
# Custom Payroll Management System for Odoo 19 Community Edition

This custom payroll module provides a standalone, high-performance payroll calculation engine, batch processing workflows, printable reports, and a real-time dashboard widget for Odoo 19 Community Edition, without relying on Enterprise dependencies.

---

## 1. Features Overview

- **Employee Contract Management** (`x_payroll.contract`): Track monthly gross wages, contract periods, and contract states (`Draft`, `Running`, `Expired`, `Cancelled`).
- **Flexible Salary Structures** (`payroll.structure`): Define unique structure groups mapped to salary rules.
- **Dynamic Salary Rules** (`payroll.rule`):
  - Category types: `Basic`, `Allowance`, `Deduction`, `Gross`, and `Net`.
  - Amount calculation types: `Fixed Amount`, `Percentage of Basic`, and dynamic `Python Code` execution.
  - Evaluation conditions: `Always True`, `Range Check` (on wage or other fields), and custom `Python Expression`.
- **Batch Processing / Payroll Runs** (`payroll.run`): Generate and compute payslips for multiple employees in bulk with single-click execution.
- **OWL 2 Dashboard Widget** (`payroll_summary`): Displays real-time aggregated metrics (Total Employees, Total Gross, Total Deductions, Total Net) reactively on the batch run view.
- **QWeb PDF Payslips**: Clean, printable HTML/PDF report template grouped by category.
- **Security & Access Control**: Row-level record rules restricting portal/standard users to see only their own contracts/payslips, while Managers have full global access.

---

## 2. Installation & Setup

### Prerequisites
- **Odoo 19 Community Edition** (installed and running).
- The base **HR (`hr`)** module installed.

### Installation
1. Place the `custom_payroll` folder into your Odoo custom addons directory.
2. Ensure the addons path includes your custom directory in your configuration (e.g., `odoo.conf`).
3. Update the Odoo Apps list:
   - Go to Apps -> Activate Developer Mode -> Click **Update Apps List**.
4. Search for **Custom Payroll Management** and click **Activate**.

---

## 3. Step-by-Step Configuration & Usage Guide

### Step 1: Employee Registration
1. Navigate to the **Employees** app.
2. Create or verify that employees are registered in the system (e.g., *Marc Demo*, *Beth Evans*).

### Step 2: Employee Contract Setup
1. Go to **Payroll -> Contracts**.
2. Click **New** to create a contract:
   - **Contract Reference**: Set a unique name or let it auto-sequence.
   - **Employee**: Select the corresponding employee.
   - **Wage**: Set the employee's monthly gross wage (e.g., `3,000.00`).
   - **Dates**: Enter the Start Date.
3. Save the contract and click **Running** in the status bar to make the contract active. *Only active (running) contracts are processed in payroll runs.*

### Step 3: Configure Salary Structures & Rules
1. Go to **Payroll -> Salary Structure -> Structures**.
2. Click **New** to create a structure:
   - Name it (e.g., *Standard Monthly Salary Structure*).
   - Code it (e.g., *SMS*).
3. Inside the **Rules** tab, add rules:
   - **Basic Salary** (`BASIC`): Category `Basic`, Amount Type `Percentage`, Percentage `100.00` (calculates 100% of contract wage).
   - **Housing Allowance** (`HRA`): Category `Allowance`, Amount Type `Fixed`, Fixed Amount `500.00`.
   - **Tax Deduction** (`TAX`): Category `Deduction`, Amount Type `Python code`.
     - Code: `result = categories["gross"] * 0.10` (calculates 10% of gross total).
     - Condition Type: `Python Expression` -> `result = contract.wage > 2000.0`.
4. Save the structure.

### Step 4: Individual Payslip (Manual Calculation)
1. Go to **Payroll -> Payslips**.
2. Click **New**:
   - Select the employee. The system will auto-select their active contract and structure.
   - Select dates.
3. Click **Compute Sheet** in the header. The **Salary Computation** tab will populate with lines for each rule, calculating Gross and Net totals.
4. Click **Confirm** to lock the payslip or **Print** to download the PDF.

### Step 5: Payroll Batch Run (Payroll Run)
1. Go to **Payroll -> Payroll Runs**.
2. Click **New**:
   - **Name**: e.g., *June 2026 Batch*.
   - **Start Date** and **End Date**: e.g., *2026-06-01* to *2026-06-30*.
   - **Employees**: (Optional) Select specific employees, or leave empty to process all active employees with running contracts.
3. Click **Generate & Compute Payslips**:
   - The system automatically creates a payslip for each employee, computes the salary lines, and updates the state.
4. **OWL Dashboard**: The top dashboard card widget will immediately show:
   - **Total Employees**: Total processed in the batch.
   - **Total Gross**: Aggregated gross payroll.
   - **Total Deductions**: Aggregated taxes/deductions.
   - **Total Net**: Total take-home pay.
5. Click **Close** or **Confirm** to finalize the batch run.
6. Click **Print Payslips** to print all payslips in this batch as a single consolidated PDF document.

---

## 4. Technical Architecture Details

### Calculation Engine Context
For Python-based rule and condition calculations, the following local variables are exposed:
- `contract`: Recordset of the employee's active contract.
- `payslip`: Recordset of the current payslip.
- `rules`: A dictionary of previously calculated rules in the sequence (e.g., `rules['BASIC']` returns the computed basic amount).
- `categories`: A dictionary of accumulated category totals (e.g., `categories['gross']` or `categories['deduction']`).
- `worked_days`: A dynamic dictionary exposing worked days and hours (e.g., `worked_days.WORK100.number_of_days`, `worked_days.LEAVE.number_of_days`, `worked_days.ATTENDANCE.number_of_hours`). Missing codes default to 0.0 to prevent crashes.
- `result`: The output variable to assign the calculated amount/condition flag (e.g., `result = contract.wage * 0.05`).

### Performance Optimization
- Payslip line calculations use a pre-fetched batch mechanism.
- The compute method bulk-deletes old lines using `unlink()` and bulk-inserts new lines using `create()` in a single transaction query, avoiding typical N+1 query overhead.
- Total aggregations on the `payroll.run` model are computed reactively using `@api.depends` mappings to ensure UI responsiveness.

---

## 5. Worked Days, Leaves & Pay Frequencies Guide

This custom payroll system integrates worked days calculations, pay frequency scheduling, and pro-rata rules to ensure financial accuracy.

### 5.1 Pay Frequency Configuration
On any active **Contract** (`x_payroll.contract`), you can configure the **Scheduled Pay** frequency under the following options:
1. **Monthly** (Default): Calculations assume standard monthly periods.
2. **Weekly**: The monthly contract wage is converted to weekly basic salary:
   $$\text{Weekly Wage} = \frac{\text{Monthly Wage} \times 12}{52}$$
3. **Bi-weekly**: Monthly wage converted to 26 periods:
   $$\text{Bi-weekly Wage} = \frac{\text{Monthly Wage} \times 12}{26}$$
4. **Semi-monthly**: Monthly wage divided by 2:
   $$\text{Semi-monthly Wage} = \frac{\text{Monthly Wage}}{2}$$

### 5.2 Automatic Worked Days Calculation
When a payslip is computed, the engine calculates three categories of worked days:
- **Normal Working Days** (`WORK100`): Computed as standard weekdays (Monday-Friday) in the payslip period minus any approved leaves.
- **Leaves** (`LEAVE`): Integrates with standard Odoo **Time Off** (`hr.leave`) module. Validated leaves overlapping with the payslip period are automatically deducted.
- **Attendance Hours** (`ATTENDANCE`): Integrates with standard Odoo **Attendances** (`hr.attendance`). Actual clocked-in hours in the period are aggregated.

---

### 5.3 Business Cases & Examples

#### Case 1: Weekly Payroll with 5-day Period (No Leaves)
*   **Contract Wage:** \$3,000.00 / month.
*   **Pay Frequency:** Weekly.
*   **Payslip Dates:** `2026-06-01` (Monday) to `2026-06-05` (Friday).
*   **What happens:**
    1.  The engine counts standard weekdays in `[2026-06-01, 2026-06-05]`, which equals **5 days**.
    2.  No leaves are detected, so `WORK100` is **5 days**.
    3.  Weekly base wage is:
        $$\text{Weekly Wage} = \frac{\$3,000 \times 12}{52} = \$692.31$$
    4.  Proration:
        $$\text{Basic Salary} = \$692.31 \times \frac{5 \text{ worked days}}{5 \text{ standard weekdays}} = \$692.31$$

#### Case 2: Monthly Payroll with mid-month Leaves (Pro-rata Deductions)
*   **Contract Wage:** \$3,000.00 / month.
*   **Pay Frequency:** Monthly.
*   **Payslip Dates:** `2026-06-01` to `2026-06-30` (22 weekdays).
*   **Time Off:** The employee has **2 days** of approved leave (e.g., `2026-06-08` and `2026-06-09`).
*   **What happens:**
    1.  The engine counts standard weekdays in June, which equals **22 days**.
    2.  Leaves overlapping June equal **2 days**.
    3.  `WORK100` is set to $22 - 2 = \mathbf{20\text{ days}}$.
    4.  Proration:
        $$\text{Basic Salary} = \$3,000.00 \times \frac{20 \text{ worked days}}{22 \text{ weekdays}} = \$2,727.27$$

#### Case 3: Hourly Wage Based on Actual Attendances
*   **Contract Wage:** (Used as base or ignored for hourly-only calculation).
*   **Salary Rule (HOURLY):** Amount Type set to `Python Code`.
    *   Code: `result = worked_days.ATTENDANCE.number_of_hours * 15.0`
*   **What happens:**
    1.  Employee clocks in/out via Odoo Attendance app for a total of **20 hours** during the period.
    2.  The engine creates an `ATTENDANCE` worked days line with `number_of_hours = 20.0`.
    3.  The rule safe evaluation executes:
        $$\text{HOURLY Pay} = 20.0 \text{ hours} \times \$15.0 = \$300.00$$

