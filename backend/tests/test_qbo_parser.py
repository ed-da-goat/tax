"""
Tests for QBO CSV parser and validator (Module M1).

Compliance risk: HIGH — TDD required.
All test data is created inline via StringIO (no external file dependencies).
"""

import io
from datetime import date
from decimal import Decimal

import pytest

from app.services.migration.qbo_parser import QBOParser, ParseResult
from app.services.migration.validator import (
    QBOValidator,
    ValidationReport,
    Severity,
)
from app.services.migration.models import (
    ParsedAccount,
    ParsedTransaction,
    ParsedCustomer,
    ParsedInvoice,
    ParsedVendor,
    ParsedEmployee,
    ParsedPayrollRecord,
    ParsedJournalEntry,
)


# ======================================================================
# Fixtures
# ======================================================================


@pytest.fixture
def parser():
    return QBOParser()


@pytest.fixture
def validator():
    return QBOValidator()


# ======================================================================
# Helper to build StringIO from CSV text
# ======================================================================


def _csv(text: str) -> io.StringIO:
    """Create a StringIO from dedented CSV text."""
    return io.StringIO(text.strip())


# ======================================================================
# Chart of Accounts parsing tests
# ======================================================================


class TestParseChartOfAccounts:
    """Tests for QBOParser.parse_chart_of_accounts."""

    def test_valid_chart_of_accounts(self, parser: QBOParser):
        """Parse valid chart of accounts CSV into correct ParsedAccount objects."""
        csv_data = _csv(
            'Account,Type,Detail Type,Description,Balance,Currency,Account #\n'
            '"Checking","Bank","Checking","Primary checking","45,678.90","USD","1000"\n'
            '"Utilities:Electric","Expenses","Utilities","Electric bill","1,234.56","USD","6200"\n'
            '"Accounts Receivable (A/R)","Accounts Receivable (A/R)","Accounts Receivable (A/R)","","12,500.00","USD","1100"'
        )
        result = parser.parse_chart_of_accounts(csv_data)

        assert result.is_valid
        assert len(result.records) == 3

        checking = result.records[0]
        assert checking.name == "Checking"
        assert checking.type == "Bank"
        assert checking.detail_type == "Checking"
        assert checking.description == "Primary checking"
        assert checking.balance == Decimal("45678.90")
        assert checking.currency == "USD"
        assert checking.account_number == "1000"

        electric = result.records[1]
        assert electric.name == "Utilities:Electric"
        assert electric.type == "Expenses"
        assert electric.balance == Decimal("1234.56")

    def test_sub_account_colon_hierarchy(self, parser: QBOParser):
        """Colon-delimited sub-account names are preserved."""
        csv_data = _csv(
            'Account,Type,Detail Type,Balance\n'
            '"Travel:Airfare","Expenses","Travel","500.00"\n'
            '"Travel:Lodging","Expenses","Travel","300.00"'
        )
        result = parser.parse_chart_of_accounts(csv_data)
        assert result.is_valid
        assert result.records[0].name == "Travel:Airfare"
        assert result.records[1].name == "Travel:Lodging"

    def test_missing_required_column(self, parser: QBOParser):
        """Missing required column reports FATAL error."""
        csv_data = _csv(
            'Account,Detail Type,Balance\n'
            '"Checking","Checking","1000"'
        )
        result = parser.parse_chart_of_accounts(csv_data)
        assert not result.is_valid
        assert any("type" in e.message.lower() for e in result.errors)

    def test_headers_only_returns_empty(self, parser: QBOParser):
        """File with only headers returns empty result (not error)."""
        csv_data = _csv('Account,Type,Detail Type,Description,Balance')
        result = parser.parse_chart_of_accounts(csv_data)
        assert result.is_valid
        assert len(result.records) == 0

    def test_optional_fields_absent(self, parser: QBOParser):
        """Optional fields (description, currency, account#) are None when absent."""
        csv_data = _csv(
            'Account,Type,Detail Type,Balance\n'
            '"Checking","Bank","Checking","1000"'
        )
        result = parser.parse_chart_of_accounts(csv_data)
        assert result.is_valid
        assert result.records[0].description is None
        assert result.records[0].currency is None
        assert result.records[0].account_number is None

    def test_negative_balance(self, parser: QBOParser):
        """Negative balances parse correctly."""
        csv_data = _csv(
            'Account,Type,Detail Type,Balance\n'
            '"Credit Card","Credit Card","Credit Card","-2,500.00"'
        )
        result = parser.parse_chart_of_accounts(csv_data)
        assert result.is_valid
        assert result.records[0].balance == Decimal("-2500.00")

    def test_parenthesized_negative(self, parser: QBOParser):
        """Parenthesized negatives parse correctly: (1,234.56) -> -1234.56."""
        csv_data = _csv(
            'Account,Type,Detail Type,Balance\n'
            '"AP","Accounts Payable (A/P)","Accounts Payable (A/P)","(3,200.50)"'
        )
        result = parser.parse_chart_of_accounts(csv_data)
        assert result.is_valid
        assert result.records[0].balance == Decimal("-3200.50")

    def test_dollar_sign_stripped(self, parser: QBOParser):
        """Currency symbol ($) is stripped from amounts."""
        csv_data = _csv(
            'Account,Type,Detail Type,Balance\n'
            '"Checking","Bank","Checking","$45,678.90"'
        )
        result = parser.parse_chart_of_accounts(csv_data)
        assert result.is_valid
        assert result.records[0].balance == Decimal("45678.90")

    def test_non_numeric_balance_error(self, parser: QBOParser):
        """Non-numeric balance reports error."""
        csv_data = _csv(
            'Account,Type,Detail Type,Balance\n'
            '"Checking","Bank","Checking","not-a-number"'
        )
        result = parser.parse_chart_of_accounts(csv_data)
        assert not result.is_valid
        assert any("V-022" in e.rule_id for e in result.errors)


# ======================================================================
# Transaction parsing tests
# ======================================================================


class TestParseTransactions:
    """Tests for QBOParser.parse_transactions."""

    def test_valid_transactions(self, parser: QBOParser):
        """Parse valid transaction CSV into correct ParsedTransaction objects."""
        csv_data = _csv(
            'Date,Transaction Type,No.,Name,Memo/Description,Split,Amount,Balance,Account\n'
            '03/15/2025,Invoice,1042,"Peachtree Landscaping LLC","Monthly service","Landscaping Income","1,500.00","13,500.00","Accounts Receivable (A/R)"\n'
            '03/20/2025,Check,5501,"Georgia Power","March electric","Utilities:Electric","-850.00","44,828.90","Checking"'
        )
        result = parser.parse_transactions(csv_data)

        assert result.is_valid
        assert len(result.records) == 2

        inv = result.records[0]
        assert inv.date == date(2025, 3, 15)
        assert inv.transaction_type == "Invoice"
        assert inv.num == "1042"
        assert inv.name == "Peachtree Landscaping LLC"
        assert inv.amount == Decimal("1500.00")
        assert inv.account == "Accounts Receivable (A/R)"
        assert inv.split == "Landscaping Income"

        chk = result.records[1]
        assert chk.amount == Decimal("-850.00")
        assert chk.account == "Checking"

    def test_invalid_date_format(self, parser: QBOParser):
        """Invalid date format reports FATAL error."""
        csv_data = _csv(
            'Date,Transaction Type,No.,Amount,Account\n'
            'not-a-date,Invoice,1042,"1500","Checking"'
        )
        result = parser.parse_transactions(csv_data)
        assert not result.is_valid
        assert any("V-020" in e.rule_id for e in result.errors)

    def test_invalid_amount(self, parser: QBOParser):
        """Non-numeric amount reports FATAL error."""
        csv_data = _csv(
            'Date,Transaction Type,No.,Amount,Account\n'
            '03/15/2025,Invoice,1042,"abc","Checking"'
        )
        result = parser.parse_transactions(csv_data)
        assert not result.is_valid
        assert any("V-022" in e.rule_id for e in result.errors)

    def test_missing_transaction_type_column(self, parser: QBOParser):
        """Missing Transaction Type column reports error."""
        csv_data = _csv(
            'Date,No.,Amount,Account\n'
            '03/15/2025,1042,"1500","Checking"'
        )
        result = parser.parse_transactions(csv_data)
        assert not result.is_valid
        assert any("transaction type" in e.message.lower() for e in result.errors)

    def test_skips_metadata_header_rows(self, parser: QBOParser):
        """QBO metadata rows above CSV header are skipped."""
        csv_data = _csv(
            '"Transaction Detail by Account"\n'
            '"Your Company Name"\n'
            '"All Dates"\n'
            '\n'
            'Date,Transaction Type,No.,Name,Amount,Balance,Account\n'
            '03/15/2025,Invoice,1042,"Client A","1,500.00","13,500.00","AR"'
        )
        result = parser.parse_transactions(csv_data)
        assert result.is_valid
        assert len(result.records) == 1
        assert result.records[0].date == date(2025, 3, 15)

    def test_skips_subtotal_rows(self, parser: QBOParser):
        """Subtotal rows ('Total for...') are filtered out."""
        csv_data = _csv(
            'Date,Transaction Type,No.,Amount,Balance,Account\n'
            '03/15/2025,Invoice,1042,"1,500.00","13,500.00","AR"\n'
            'Total for Checking,,,,,"45,678.90"'
        )
        result = parser.parse_transactions(csv_data)
        assert result.is_valid
        assert len(result.records) == 1

    def test_yyyy_mm_dd_date_format(self, parser: QBOParser):
        """YYYY-MM-DD date format is accepted."""
        csv_data = _csv(
            'Date,Transaction Type,Amount,Account\n'
            '2025-03-15,Invoice,"1500","Checking"'
        )
        result = parser.parse_transactions(csv_data)
        assert result.is_valid
        assert result.records[0].date == date(2025, 3, 15)

    def test_optional_fields_none(self, parser: QBOParser):
        """Optional fields are None when empty."""
        csv_data = _csv(
            'Date,Transaction Type,No.,Name,Memo/Description,Split,Amount,Balance,Account\n'
            '03/15/2025,Invoice,,,,,"1,500.00",,"AR"'
        )
        result = parser.parse_transactions(csv_data)
        assert result.is_valid
        assert result.records[0].num is None
        assert result.records[0].name is None
        assert result.records[0].memo is None
        assert result.records[0].split is None


# ======================================================================
# Customer parsing tests
# ======================================================================


class TestParseCustomers:
    """Tests for QBOParser.parse_customers."""

    def test_valid_customers(self, parser: QBOParser):
        """Parse valid customer CSV into correct ParsedCustomer objects."""
        csv_data = _csv(
            'Customer,Phone,Email,Company,Billing Street,Billing City,Billing State,Billing ZIP,Open Balance\n'
            '"Peachtree Landscaping LLC","(770) 555-1234","info@ptl.com","Peachtree Landscaping LLC","456 Magnolia Blvd","Marietta","GA","30060","3,500.00"\n'
            '"Smith Consulting","","smith@example.com","","123 Main St","Atlanta","GA","30301","0.00"'
        )
        result = parser.parse_customers(csv_data)

        assert result.is_valid
        assert len(result.records) == 2

        ptl = result.records[0]
        assert ptl.name == "Peachtree Landscaping LLC"
        assert ptl.phone == "(770) 555-1234"
        assert ptl.email == "info@ptl.com"
        assert ptl.billing_city == "Marietta"
        assert ptl.billing_state == "GA"
        assert ptl.open_balance == Decimal("3500.00")

    def test_missing_customer_column(self, parser: QBOParser):
        """Missing 'Customer' column reports error."""
        csv_data = _csv(
            'Name,Phone,Email\n'
            '"Test","555-1234","test@test.com"'
        )
        result = parser.parse_customers(csv_data)
        assert not result.is_valid

    def test_empty_customer_name(self, parser: QBOParser):
        """Empty customer name reports FATAL error per row."""
        csv_data = _csv(
            'Customer,Phone,Email\n'
            ',"555-1234","test@test.com"'
        )
        result = parser.parse_customers(csv_data)
        assert not result.is_valid

    def test_utf8_special_characters(self, parser: QBOParser):
        """UTF-8 encoding with special characters handled."""
        csv_data = _csv(
            'Customer,Phone,Email\n'
            '"Caf\u00e9 del Sol\u2019s LLC","555-1234","cafe@test.com"\n'
            '"M\u00fcller & S\u00f6hne GmbH","555-5678","muller@test.com"'
        )
        result = parser.parse_customers(csv_data)
        assert result.is_valid
        assert result.records[0].name == "Caf\u00e9 del Sol\u2019s LLC"
        assert result.records[1].name == "M\u00fcller & S\u00f6hne GmbH"


# ======================================================================
# Invoice parsing tests
# ======================================================================


class TestParseInvoices:
    """Tests for QBOParser.parse_invoices."""

    def test_valid_invoices(self, parser: QBOParser):
        """Parse valid invoice CSV into correct ParsedInvoice objects."""
        csv_data = _csv(
            'Invoice Date,No.,Customer,Due Date,Amount,Open Balance,Status\n'
            '03/15/2025,1042,"Peachtree Landscaping LLC",04/14/2025,"1,500.00","0.00","Paid"\n'
            '03/20/2025,1043,"Atlanta Tech Solutions",04/19/2025,"4,500.00","4,500.00","Open"'
        )
        result = parser.parse_invoices(csv_data)

        assert result.is_valid
        assert len(result.records) == 2

        inv1 = result.records[0]
        assert inv1.invoice_date == date(2025, 3, 15)
        assert inv1.invoice_no == "1042"
        assert inv1.customer == "Peachtree Landscaping LLC"
        assert inv1.due_date == date(2025, 4, 14)
        assert inv1.amount == Decimal("1500.00")
        assert inv1.open_balance == Decimal("0.00")
        assert inv1.status == "Paid"

    def test_missing_due_date_column(self, parser: QBOParser):
        """Missing due date column reports error."""
        csv_data = _csv(
            'Invoice Date,No.,Customer,Amount\n'
            '03/15/2025,1042,"Client A","1500"'
        )
        result = parser.parse_invoices(csv_data)
        assert not result.is_valid

    def test_invalid_invoice_date(self, parser: QBOParser):
        """Invalid invoice date reports FATAL error."""
        csv_data = _csv(
            'Invoice Date,No.,Customer,Due Date,Amount\n'
            'bad-date,1042,"Client A",04/14/2025,"1500"'
        )
        result = parser.parse_invoices(csv_data)
        assert not result.is_valid
        assert any("V-020" in e.rule_id for e in result.errors)

    def test_empty_invoice_number_error(self, parser: QBOParser):
        """Empty invoice number reports error."""
        csv_data = _csv(
            'Invoice Date,No.,Customer,Due Date,Amount\n'
            '03/15/2025,,"Client A",04/14/2025,"1500"'
        )
        result = parser.parse_invoices(csv_data)
        assert not result.is_valid

    def test_all_statuses(self, parser: QBOParser):
        """All QBO invoice statuses are preserved."""
        csv_data = _csv(
            'Invoice Date,No.,Customer,Due Date,Amount,Status\n'
            '03/15/2025,1001,"A",04/14/2025,"100","Paid"\n'
            '03/15/2025,1002,"B",04/14/2025,"200","Open"\n'
            '03/15/2025,1003,"C",04/14/2025,"300","Overdue"\n'
            '03/15/2025,1004,"D",04/14/2025,"400","Voided"'
        )
        result = parser.parse_invoices(csv_data)
        assert result.is_valid
        statuses = [r.status for r in result.records]
        assert statuses == ["Paid", "Open", "Overdue", "Voided"]


# ======================================================================
# Vendor parsing tests
# ======================================================================


class TestParseVendors:
    """Tests for QBOParser.parse_vendors."""

    def test_valid_vendors(self, parser: QBOParser):
        """Parse valid vendor CSV."""
        csv_data = _csv(
            'Vendor,Company,Phone,Email,Street,City,State,ZIP\n'
            '"Georgia Power","Georgia Power Co","(800) 555-1234","gp@example.com","123 Power St","Atlanta","GA","30301"\n'
            '"Office Depot","Office Depot Inc","","od@example.com","","","",""'
        )
        result = parser.parse_vendors(csv_data)
        assert result.is_valid
        assert len(result.records) == 2
        assert result.records[0].name == "Georgia Power"
        assert result.records[0].state == "GA"
        assert result.records[1].street is None

    def test_missing_vendor_column(self, parser: QBOParser):
        """Missing vendor/name column reports error."""
        csv_data = _csv(
            'Company,Phone\n'
            '"GP","555-1234"'
        )
        result = parser.parse_vendors(csv_data)
        assert not result.is_valid

    def test_name_column_as_fallback(self, parser: QBOParser):
        """'Name' column is accepted as fallback for 'Vendor'."""
        csv_data = _csv(
            'Name,Phone\n'
            '"Georgia Power","555-1234"'
        )
        result = parser.parse_vendors(csv_data)
        assert result.is_valid
        assert result.records[0].name == "Georgia Power"


# ======================================================================
# Employee parsing tests
# ======================================================================


class TestParseEmployees:
    """Tests for QBOParser.parse_employees."""

    def test_valid_employees(self, parser: QBOParser):
        """Parse valid employee CSV."""
        csv_data = _csv(
            'Employee,SSN (last 4),Hire Date,Status,Pay Type,Pay Rate,Filing Status\n'
            '"John Smith","6789",01/15/2020,"Active","Salary","$5,000.00","Single"\n'
            '"Jane Doe","4321",06/01/2021,"Active","Hourly","$25.00","Married"'
        )
        result = parser.parse_employees(csv_data)

        assert result.is_valid
        assert len(result.records) == 2

        john = result.records[0]
        assert john.name == "John Smith"
        assert john.ssn_last4 == "6789"
        assert john.hire_date == date(2020, 1, 15)
        assert john.status == "Active"
        assert john.pay_type == "Salary"
        assert john.pay_rate == Decimal("5000.00")
        assert john.filing_status == "Single"

    def test_terminated_employee(self, parser: QBOParser):
        """Terminated status is preserved."""
        csv_data = _csv(
            'Employee,Status,Pay Type\n'
            '"Former Worker","Terminated","Hourly"'
        )
        result = parser.parse_employees(csv_data)
        assert result.is_valid
        assert result.records[0].status == "Terminated"

    def test_missing_optional_fields(self, parser: QBOParser):
        """Optional fields are None when absent."""
        csv_data = _csv(
            'Employee,Status\n'
            '"Jane Doe","Active"'
        )
        result = parser.parse_employees(csv_data)
        assert result.is_valid
        assert result.records[0].ssn_last4 is None
        assert result.records[0].hire_date is None
        assert result.records[0].pay_rate is None


# ======================================================================
# Payroll Summary parsing tests
# ======================================================================


class TestParsePayrollSummary:
    """Tests for QBOParser.parse_payroll_summary."""

    def test_valid_payroll(self, parser: QBOParser):
        """Parse valid payroll summary CSV."""
        csv_data = _csv(
            'Employee,Gross Pay,Federal Withholding,Social Security Employee,Medicare Employee,GA Withholding,Net Pay,Federal Unemployment,GA SUI\n'
            '"John Smith","5,000.00","625.00","310.00","72.50","250.00","3,742.50","42.00","135.00"\n'
            '"Jane Doe","4,200.00","504.00","260.40","60.90","210.00","3,164.70","25.20","113.40"'
        )
        result = parser.parse_payroll_summary(csv_data)

        assert result.is_valid
        assert len(result.records) == 2

        john = result.records[0]
        assert john.employee == "John Smith"
        assert john.gross_pay == Decimal("5000.00")
        assert john.federal_withholding == Decimal("625.00")
        assert john.social_security == Decimal("310.00")
        assert john.medicare == Decimal("72.50")
        assert john.state_withholding == Decimal("250.00")
        assert john.net_pay == Decimal("3742.50")
        assert john.futa == Decimal("42.00")
        assert john.ga_suta == Decimal("135.00")

    def test_alternate_column_names(self, parser: QBOParser):
        """Alternate column names (State Tax, GA Unemployment) are accepted."""
        csv_data = _csv(
            'Employee,Gross Pay,Federal Tax,State Tax,Net Pay,GA Unemployment\n'
            '"John Smith","5,000.00","625.00","250.00","3,742.50","135.00"'
        )
        result = parser.parse_payroll_summary(csv_data)
        assert result.is_valid
        # "Federal Tax" -> federal_withholding via alias
        # "State Tax" -> state_withholding via alias
        # "GA Unemployment" -> ga_suta via alias

    def test_missing_gross_pay_column(self, parser: QBOParser):
        """Missing Gross Pay column reports error."""
        csv_data = _csv(
            'Employee,Net Pay\n'
            '"John Smith","3742.50"'
        )
        result = parser.parse_payroll_summary(csv_data)
        assert not result.is_valid

    def test_non_numeric_gross_pay(self, parser: QBOParser):
        """Non-numeric gross pay reports error."""
        csv_data = _csv(
            'Employee,Gross Pay\n'
            '"John Smith","invalid"'
        )
        result = parser.parse_payroll_summary(csv_data)
        assert not result.is_valid
        assert any("V-022" in e.rule_id for e in result.errors)

    def test_skips_qbo_metadata_headers(self, parser: QBOParser):
        """Payroll Summary with QBO metadata rows is parsed correctly."""
        csv_data = _csv(
            '"Payroll Summary"\n'
            '"Your Company Name"\n'
            '"Jan 1 - Dec 31, 2025"\n'
            '\n'
            'Employee,Gross Pay,Net Pay\n'
            '"John Smith","5,000.00","3,742.50"'
        )
        result = parser.parse_payroll_summary(csv_data)
        assert result.is_valid
        assert len(result.records) == 1
        assert result.records[0].gross_pay == Decimal("5000.00")


# ======================================================================
# General Journal parsing tests
# ======================================================================


class TestParseGeneralJournal:
    """Tests for QBOParser.parse_general_journal."""

    def test_valid_journal(self, parser: QBOParser):
        """Parse valid general journal CSV."""
        csv_data = _csv(
            'Date,No.,Account,Debit,Credit,Name,Memo/Description\n'
            '03/20/2025,JE-001,"Depreciation Expense","2,500.00","","","Depreciation - March"\n'
            '03/20/2025,JE-001,"Accumulated Depreciation","","2,500.00","","Depreciation - March"'
        )
        result = parser.parse_general_journal(csv_data)

        assert result.is_valid
        assert len(result.records) == 2

        debit_line = result.records[0]
        assert debit_line.date == date(2025, 3, 20)
        assert debit_line.entry_no == "JE-001"
        assert debit_line.account == "Depreciation Expense"
        assert debit_line.debit == Decimal("2500.00")
        assert debit_line.credit is None
        assert debit_line.memo == "Depreciation - March"

        credit_line = result.records[1]
        assert credit_line.debit is None
        assert credit_line.credit == Decimal("2500.00")

    def test_missing_account_column(self, parser: QBOParser):
        """Missing Account column reports error."""
        csv_data = _csv(
            'Date,Debit,Credit\n'
            '03/20/2025,"100","100"'
        )
        result = parser.parse_general_journal(csv_data)
        assert not result.is_valid

    def test_invalid_debit_amount(self, parser: QBOParser):
        """Non-numeric debit reports error."""
        csv_data = _csv(
            'Date,Account,Debit,Credit\n'
            '03/20/2025,"Checking","abc",""'
        )
        result = parser.parse_general_journal(csv_data)
        assert not result.is_valid
        assert any("V-022" in e.rule_id for e in result.errors)


# ======================================================================
# Validator tests
# ======================================================================


class TestQBOValidator:
    """Tests for QBOValidator.validate_file."""

    def test_valid_chart_of_accounts(self, validator: QBOValidator):
        """Valid chart of accounts passes validation."""
        csv_data = _csv(
            'Account,Type,Detail Type,Balance\n'
            '"Checking","Bank","Checking","1000"'
        )
        report = validator.validate_file(csv_data, "chart_of_accounts")
        assert report.is_valid
        assert report.records_scanned == 1

    def test_missing_column_fatal(self, validator: QBOValidator):
        """Missing required column is FATAL."""
        csv_data = _csv(
            'Account,Balance\n'
            '"Checking","1000"'
        )
        report = validator.validate_file(csv_data, "chart_of_accounts")
        assert not report.is_valid
        assert report.fatal_count > 0

    def test_invalid_date_in_transactions(self, validator: QBOValidator):
        """Invalid date in transactions is flagged."""
        csv_data = _csv(
            'Date,Transaction Type,Amount,Account\n'
            'not-a-date,Invoice,"1500","Checking"'
        )
        report = validator.validate_file(csv_data, "transactions")
        assert not report.is_valid
        assert any("V-020" in e.rule_id for e in report.errors)

    def test_non_numeric_amount(self, validator: QBOValidator):
        """Non-numeric amount is flagged."""
        csv_data = _csv(
            'Date,Transaction Type,Amount,Account\n'
            '03/15/2025,Invoice,"abc","Checking"'
        )
        report = validator.validate_file(csv_data, "transactions")
        assert not report.is_valid
        assert any("V-022" in e.rule_id for e in report.errors)

    def test_empty_file(self, validator: QBOValidator):
        """Empty file produces report with no records and is valid (no fatal)."""
        csv_data = _csv(
            'Account,Type,Detail Type\n'
        )
        report = validator.validate_file(csv_data, "chart_of_accounts")
        # Headers only, no data => valid but 0 records
        assert report.is_valid
        assert report.records_scanned == 0

    def test_completely_empty_file(self, validator: QBOValidator):
        """Completely empty file (no headers) is FATAL."""
        csv_data = io.StringIO("")
        report = validator.validate_file(csv_data, "chart_of_accounts")
        assert not report.is_valid

    def test_currency_formatting_accepted(self, validator: QBOValidator):
        """Currency-formatted amounts ($1,234.56) pass validation."""
        csv_data = _csv(
            'Date,Transaction Type,Amount,Account\n'
            '03/15/2025,Invoice,"$1,234.56","Checking"'
        )
        report = validator.validate_file(csv_data, "transactions")
        assert report.is_valid

    def test_parenthesized_negative_accepted(self, validator: QBOValidator):
        """Parenthesized negatives (1,234.56) pass validation."""
        csv_data = _csv(
            'Date,Transaction Type,Amount,Account\n'
            '03/15/2025,Check,"(850.00)","Checking"'
        )
        report = validator.validate_file(csv_data, "transactions")
        assert report.is_valid

    def test_invoice_validation(self, validator: QBOValidator):
        """Invoice validation checks required columns."""
        csv_data = _csv(
            'Invoice Date,No.,Customer,Due Date,Amount\n'
            '03/15/2025,1042,"Client A",04/14/2025,"1500"'
        )
        report = validator.validate_file(csv_data, "invoices")
        assert report.is_valid

    def test_invoice_missing_amount(self, validator: QBOValidator):
        """Invoice missing amount column is flagged."""
        csv_data = _csv(
            'Invoice Date,No.,Customer,Due Date\n'
            '03/15/2025,1042,"Client A",04/14/2025'
        )
        report = validator.validate_file(csv_data, "invoices")
        assert not report.is_valid

    def test_validation_report_properties(self, validator: QBOValidator):
        """ValidationReport properties (fatal_count, warning_count) work."""
        csv_data = _csv(
            'Account,Balance\n'
            '"Checking","1000"'
        )
        report = validator.validate_file(csv_data, "chart_of_accounts")
        # Missing 'type' and 'detail type' columns
        assert report.fatal_count >= 1
        assert isinstance(report.warning_count, int)

    def test_alternate_column_names_accepted(self, validator: QBOValidator):
        """Alternate column names (Num vs No.) are accepted."""
        csv_data = _csv(
            'Invoice Date,Num,Customer,Due Date,Amount\n'
            '03/15/2025,1042,"Client A",04/14/2025,"1500"'
        )
        report = validator.validate_file(csv_data, "invoices")
        assert report.is_valid


# ======================================================================
# Edge cases
# ======================================================================


class TestEdgeCases:
    """Edge-case and robustness tests."""

    def test_bom_handling(self, parser: QBOParser):
        """UTF-8 BOM character at start of file is handled."""
        csv_data = io.StringIO(
            "\ufeffAccount,Type,Detail Type,Balance\n"
            '"Checking","Bank","Checking","1000"'
        )
        result = parser.parse_chart_of_accounts(csv_data)
        assert result.is_valid
        assert len(result.records) == 1

    def test_multiple_errors_collected(self, parser: QBOParser):
        """Multiple errors are collected (does not stop at first)."""
        csv_data = _csv(
            'Date,Transaction Type,Amount,Account\n'
            'bad-date-1,Invoice,"1500","Checking"\n'
            'bad-date-2,Check,"850","Checking"\n'
            '03/15/2025,Invoice,"valid","Checking"'
        )
        result = parser.parse_transactions(csv_data)
        # Should have 2 date errors and 1 amount error (3 total)
        # but the third row has valid date, amount = "valid" -> error
        assert len(result.errors) >= 2

    def test_commas_in_amounts(self, parser: QBOParser):
        """Amounts with comma thousands separators parse correctly."""
        csv_data = _csv(
            'Account,Type,Detail Type,Balance\n'
            '"Revenue","Income","Sales","1,234,567.89"'
        )
        result = parser.parse_chart_of_accounts(csv_data)
        assert result.is_valid
        assert result.records[0].balance == Decimal("1234567.89")

    def test_whitespace_trimming(self, parser: QBOParser):
        """Leading/trailing whitespace in values is trimmed."""
        csv_data = _csv(
            'Customer,Phone,Email\n'
            '"  Peachtree LLC  "," (770) 555-1234 "," info@ptl.com "'
        )
        result = parser.parse_customers(csv_data)
        assert result.is_valid
        assert result.records[0].name == "Peachtree LLC"
        assert result.records[0].phone == "(770) 555-1234"
        assert result.records[0].email == "info@ptl.com"

    def test_parse_result_is_valid_property(self, parser: QBOParser):
        """ParseResult.is_valid is True when no FATAL errors exist."""
        csv_data = _csv(
            'Account,Type,Detail Type\n'
            '"Checking","Bank","Checking"'
        )
        result = parser.parse_chart_of_accounts(csv_data)
        assert result.is_valid is True

    def test_zero_balance(self, parser: QBOParser):
        """Zero balance parses correctly."""
        csv_data = _csv(
            'Account,Type,Detail Type,Balance\n'
            '"Empty Account","Bank","Checking","0.00"'
        )
        result = parser.parse_chart_of_accounts(csv_data)
        assert result.is_valid
        assert result.records[0].balance == Decimal("0.00")

    def test_large_amount(self, parser: QBOParser):
        """Large amounts (realistic max for GA small business) parse."""
        csv_data = _csv(
            'Account,Type,Detail Type,Balance\n'
            '"Revenue","Income","Sales","$9,999,999.99"'
        )
        result = parser.parse_chart_of_accounts(csv_data)
        assert result.is_valid
        assert result.records[0].balance == Decimal("9999999.99")

    def test_empty_balance_is_none(self, parser: QBOParser):
        """Empty balance field becomes None, not an error."""
        csv_data = _csv(
            'Account,Type,Detail Type,Balance\n'
            '"New Account","Bank","Checking",""'
        )
        result = parser.parse_chart_of_accounts(csv_data)
        assert result.is_valid
        assert result.records[0].balance is None

    def test_case_insensitive_headers(self, parser: QBOParser):
        """Column headers are matched case-insensitively."""
        csv_data = _csv(
            'ACCOUNT,TYPE,DETAIL TYPE,BALANCE\n'
            '"Checking","Bank","Checking","1000"'
        )
        result = parser.parse_chart_of_accounts(csv_data)
        assert result.is_valid
        assert len(result.records) == 1

    def test_vendor_headers_only_empty_result(self, parser: QBOParser):
        """Vendor CSV with headers only returns empty result."""
        csv_data = _csv('Vendor,Company,Phone')
        result = parser.parse_vendors(csv_data)
        assert result.is_valid
        assert len(result.records) == 0

    def test_employee_headers_only(self, parser: QBOParser):
        """Employee CSV with headers only returns empty result."""
        csv_data = _csv('Employee,Status')
        result = parser.parse_employees(csv_data)
        assert result.is_valid
        assert len(result.records) == 0

    def test_payroll_headers_only(self, parser: QBOParser):
        """Payroll CSV with headers only returns empty result."""
        csv_data = _csv('Employee,Gross Pay,Net Pay')
        result = parser.parse_payroll_summary(csv_data)
        assert result.is_valid
        assert len(result.records) == 0

    def test_journal_headers_only(self, parser: QBOParser):
        """General journal with headers only returns empty result."""
        csv_data = _csv('Date,Account,Debit,Credit')
        result = parser.parse_general_journal(csv_data)
        assert result.is_valid
        assert len(result.records) == 0
