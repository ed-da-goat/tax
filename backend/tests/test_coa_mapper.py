"""
Tests for Chart of Accounts Mapper (module M3).

Validates that QBO account types and detail types are correctly mapped
to the Georgia standard 5-category account_type system with proper
account numbering.

Uses unit tests only — no database needed. The mapper is a pure
transformation layer.
"""

import uuid
from decimal import Decimal

import pytest

from app.services.migration.coa_mapper import (
    COAMapper,
    MappedAccount,
    MappingResult,
    QBO_DETAIL_TO_SUB_TYPE,
    QBO_TYPE_TO_ACCOUNT_TYPE,
    UnmappedAccount,
)
from app.services.migration.models import ParsedAccount


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

CLIENT_ID = uuid.uuid4()


def _acct(
    name: str = "Test Account",
    type: str = "Bank",
    detail_type: str = "Checking",
    balance: Decimal | None = None,
    account_number: str | None = None,
) -> ParsedAccount:
    return ParsedAccount(
        name=name,
        type=type,
        detail_type=detail_type,
        balance=balance,
        account_number=account_number,
    )


# ---------------------------------------------------------------------------
# Basic mapping tests
# ---------------------------------------------------------------------------


class TestCOAMapperBasic:
    """Basic mapping functionality."""

    def test_empty_input(self):
        mapper = COAMapper()
        result = mapper.map_accounts([], CLIENT_ID)
        assert result.total_input == 0
        assert result.total_mapped == 0
        assert result.total_unmapped == 0
        assert result.mapped_accounts == []
        assert result.unmapped_accounts == []

    def test_single_bank_account(self):
        mapper = COAMapper()
        accounts = [_acct("Checking Account", "Bank", "Checking")]
        result = mapper.map_accounts(accounts, CLIENT_ID)

        assert result.total_input == 1
        assert result.total_mapped == 1
        assert result.total_unmapped == 0

        mapped = result.mapped_accounts[0]
        assert mapped.account_type == "ASSET"
        assert mapped.sub_type == "Cash and Cash Equivalents"
        assert mapped.account_name == "Checking Account"
        assert mapped.client_id == CLIENT_ID
        assert mapped.original_qbo_type == "Bank"
        assert mapped.original_qbo_detail_type == "Checking"

    def test_account_number_in_asset_range(self):
        mapper = COAMapper()
        accounts = [_acct("Checking", "Bank", "Checking")]
        result = mapper.map_accounts(accounts, CLIENT_ID)

        mapped = result.mapped_accounts[0]
        num = int(mapped.account_number)
        assert 1000 <= num <= 1999, f"Asset account number {num} out of range"

    def test_preserves_balance(self):
        mapper = COAMapper()
        accounts = [_acct("Checking", "Bank", "Checking", balance=Decimal("5432.10"))]
        result = mapper.map_accounts(accounts, CLIENT_ID)

        assert result.mapped_accounts[0].balance == Decimal("5432.10")


# ---------------------------------------------------------------------------
# Type mapping tests
# ---------------------------------------------------------------------------


class TestTypeMapping:
    """Test QBO type → account_type mapping for all categories."""

    @pytest.mark.parametrize("qbo_type,expected", [
        ("Bank", "ASSET"),
        ("Accounts Receivable", "ASSET"),
        ("Accounts Receivable (A/R)", "ASSET"),
        ("Other Current Asset", "ASSET"),
        ("Fixed Asset", "ASSET"),
        ("Other Asset", "ASSET"),
    ])
    def test_asset_types(self, qbo_type, expected):
        mapper = COAMapper()
        result = mapper.map_accounts([_acct(type=qbo_type)], CLIENT_ID)
        assert result.mapped_accounts[0].account_type == expected

    @pytest.mark.parametrize("qbo_type,expected", [
        ("Accounts Payable", "LIABILITY"),
        ("Accounts Payable (A/P)", "LIABILITY"),
        ("Credit Card", "LIABILITY"),
        ("Other Current Liability", "LIABILITY"),
        ("Long Term Liability", "LIABILITY"),
    ])
    def test_liability_types(self, qbo_type, expected):
        mapper = COAMapper()
        result = mapper.map_accounts([_acct(type=qbo_type)], CLIENT_ID)
        assert result.mapped_accounts[0].account_type == expected

    def test_equity_type(self):
        mapper = COAMapper()
        result = mapper.map_accounts([_acct(type="Equity", detail_type="Retained Earnings")], CLIENT_ID)
        assert result.mapped_accounts[0].account_type == "EQUITY"

    @pytest.mark.parametrize("qbo_type,expected", [
        ("Income", "REVENUE"),
        ("Other Income", "REVENUE"),
    ])
    def test_revenue_types(self, qbo_type, expected):
        mapper = COAMapper()
        result = mapper.map_accounts([_acct(type=qbo_type)], CLIENT_ID)
        assert result.mapped_accounts[0].account_type == expected

    @pytest.mark.parametrize("qbo_type,expected", [
        ("Expense", "EXPENSE"),
        ("Other Expense", "EXPENSE"),
        ("Cost of Goods Sold", "EXPENSE"),
    ])
    def test_expense_types(self, qbo_type, expected):
        mapper = COAMapper()
        result = mapper.map_accounts([_acct(type=qbo_type)], CLIENT_ID)
        assert result.mapped_accounts[0].account_type == expected


# ---------------------------------------------------------------------------
# Account number assignment
# ---------------------------------------------------------------------------


class TestAccountNumbering:
    """Test sequential account number assignment within ranges."""

    def test_sequential_numbering(self):
        mapper = COAMapper()
        accounts = [
            _acct("Cash", "Bank", "Checking"),
            _acct("Savings", "Bank", "Savings"),
            _acct("AR", "Accounts Receivable", "Accounts Receivable"),
        ]
        result = mapper.map_accounts(accounts, CLIENT_ID)

        numbers = [m.account_number for m in result.mapped_accounts]
        assert numbers[0] == "1000"
        assert numbers[1] == "1001"
        assert numbers[2] == "1002"  # All ASSET type

    def test_different_types_get_different_ranges(self):
        mapper = COAMapper()
        accounts = [
            _acct("Cash", "Bank", "Checking"),
            _acct("AP", "Accounts Payable", "Accounts Payable"),
            _acct("Revenue", "Income", "Service/Fee Income"),
        ]
        result = mapper.map_accounts(accounts, CLIENT_ID)

        nums = {m.account_type: int(m.account_number) for m in result.mapped_accounts}
        assert 1000 <= nums["ASSET"] <= 1999
        assert 2000 <= nums["LIABILITY"] <= 2999
        assert 4000 <= nums["REVENUE"] <= 4999

    def test_preserves_qbo_account_number_when_available(self):
        mapper = COAMapper()
        accounts = [_acct("Cash", "Bank", "Checking", account_number="1100")]
        result = mapper.map_accounts(accounts, CLIENT_ID)

        assert result.mapped_accounts[0].account_number == "1100"

    def test_no_duplicate_numbers(self):
        mapper = COAMapper()
        accounts = [
            _acct("Cash", "Bank", "Checking", account_number="1000"),
            _acct("Savings", "Bank", "Savings", account_number="1000"),  # duplicate
        ]
        result = mapper.map_accounts(accounts, CLIENT_ID)

        numbers = [m.account_number for m in result.mapped_accounts]
        assert len(numbers) == len(set(numbers)), "Duplicate account numbers found"


# ---------------------------------------------------------------------------
# Sub-type mapping
# ---------------------------------------------------------------------------


class TestSubTypeMapping:
    """Test QBO detail_type → sub_type mapping."""

    @pytest.mark.parametrize("detail_type,expected_sub", [
        ("Checking", "Cash and Cash Equivalents"),
        ("Savings", "Cash and Cash Equivalents"),
        ("Accounts Receivable", "Accounts Receivable"),
        ("Inventory", "Inventory"),
        ("Prepaid Expenses", "Prepaid Expenses"),
    ])
    def test_asset_sub_types(self, detail_type, expected_sub):
        mapper = COAMapper()
        result = mapper.map_accounts([_acct(type="Bank", detail_type=detail_type)], CLIENT_ID)
        assert result.mapped_accounts[0].sub_type == expected_sub

    @pytest.mark.parametrize("detail_type,expected_sub", [
        ("Accounts Payable", "Accounts Payable"),
        ("Credit Card", "Credit Card"),
        ("Payroll Liabilities", "Payroll Liabilities"),
        ("Sales Tax Payable", "Sales Tax Payable"),
    ])
    def test_liability_sub_types(self, detail_type, expected_sub):
        mapper = COAMapper()
        result = mapper.map_accounts(
            [_acct(type="Other Current Liability", detail_type=detail_type)], CLIENT_ID
        )
        assert result.mapped_accounts[0].sub_type == expected_sub

    @pytest.mark.parametrize("detail_type,expected_sub", [
        ("Advertising", "Advertising"),
        ("Insurance", "Insurance"),
        ("Rent or Lease", "Rent Expense"),
        ("Utilities", "Utilities"),
        ("Legal & Professional Fees", "Professional Fees"),
    ])
    def test_expense_sub_types(self, detail_type, expected_sub):
        mapper = COAMapper()
        result = mapper.map_accounts(
            [_acct(type="Expense", detail_type=detail_type)], CLIENT_ID
        )
        assert result.mapped_accounts[0].sub_type == expected_sub


# ---------------------------------------------------------------------------
# Unmapped / unrecognized accounts
# ---------------------------------------------------------------------------


class TestUnmappedAccounts:
    """Test handling of unrecognized QBO types."""

    def test_unknown_type_goes_to_unmapped(self):
        mapper = COAMapper()
        accounts = [_acct("Mystery", "NonExistentType", "SomeDetail")]
        result = mapper.map_accounts(accounts, CLIENT_ID)

        assert result.total_mapped == 0
        assert result.total_unmapped == 1
        assert result.unmapped_accounts[0].reason == "QBO type 'NonExistentType' not recognized"
        assert result.unmapped_accounts[0].original.name == "Mystery"

    def test_mixed_mapped_and_unmapped(self):
        mapper = COAMapper()
        accounts = [
            _acct("Cash", "Bank", "Checking"),
            _acct("Mystery", "UnknownType", "Unknown"),
            _acct("Revenue", "Income", "Service/Fee Income"),
        ]
        result = mapper.map_accounts(accounts, CLIENT_ID)

        assert result.total_input == 3
        assert result.total_mapped == 2
        assert result.total_unmapped == 1


# ---------------------------------------------------------------------------
# Sub-account handling (colon-delimited names)
# ---------------------------------------------------------------------------


class TestSubAccounts:
    """Test handling of QBO sub-accounts (colon-delimited names)."""

    def test_sub_account_generates_warning(self):
        mapper = COAMapper()
        accounts = [_acct("Expenses:Office Supplies:Paper", "Expense", "Office Expenses")]
        result = mapper.map_accounts(accounts, CLIENT_ID)

        assert result.total_mapped == 1
        assert len(result.warnings) == 1
        assert "sub-account" in result.warnings[0].lower()

    def test_sub_account_preserves_full_name(self):
        mapper = COAMapper()
        accounts = [_acct("Expenses:Office Supplies:Paper", "Expense", "Office Expenses")]
        result = mapper.map_accounts(accounts, CLIENT_ID)

        assert result.mapped_accounts[0].account_name == "Expenses:Office Supplies:Paper"


# ---------------------------------------------------------------------------
# Case insensitivity
# ---------------------------------------------------------------------------


class TestCaseInsensitivity:
    """Test that mapping handles case variations in QBO data."""

    def test_type_case_insensitive(self):
        mapper = COAMapper()
        for variant in ["bank", "Bank", "BANK", "bAnK"]:
            result = mapper.map_accounts([_acct(type=variant)], CLIENT_ID)
            assert result.total_mapped == 1, f"Failed to map type '{variant}'"
            assert result.mapped_accounts[0].account_type == "ASSET"

    def test_detail_type_case_insensitive(self):
        mapper = COAMapper()
        for variant in ["checking", "Checking", "CHECKING"]:
            result = mapper.map_accounts(
                [_acct(type="Bank", detail_type=variant)], CLIENT_ID
            )
            assert result.mapped_accounts[0].sub_type == "Cash and Cash Equivalents"


# ---------------------------------------------------------------------------
# Realistic QBO data scenario
# ---------------------------------------------------------------------------


class TestRealisticScenario:
    """Test with a realistic set of QBO accounts."""

    def test_typical_small_business_coa(self):
        mapper = COAMapper()
        accounts = [
            _acct("Checking", "Bank", "Checking", balance=Decimal("15000.00")),
            _acct("Savings", "Bank", "Savings", balance=Decimal("50000.00")),
            _acct("Accounts Receivable", "Accounts Receivable (A/R)", "Accounts Receivable"),
            _acct("Office Equipment", "Fixed Asset", "Furniture & Fixtures"),
            _acct("Accounts Payable", "Accounts Payable (A/P)", "Accounts Payable"),
            _acct("Credit Card - Visa", "Credit Card", "Credit Card"),
            _acct("Payroll Liabilities", "Other Current Liability", "Payroll Liabilities"),
            _acct("Opening Balance Equity", "Equity", "Opening Balance Equity"),
            _acct("Retained Earnings", "Equity", "Retained Earnings"),
            _acct("Services", "Income", "Service/Fee Income"),
            _acct("Advertising", "Expense", "Advertising"),
            _acct("Insurance", "Expense", "Insurance"),
            _acct("Office Supplies", "Expense", "Office Expenses"),
            _acct("Rent", "Expense", "Rent or Lease"),
            _acct("Utilities", "Expense", "Utilities"),
        ]
        result = mapper.map_accounts(accounts, CLIENT_ID)

        assert result.total_input == 15
        assert result.total_mapped == 15
        assert result.total_unmapped == 0

        # Verify type distribution
        types = [m.account_type for m in result.mapped_accounts]
        assert types.count("ASSET") == 4
        assert types.count("LIABILITY") == 3
        assert types.count("EQUITY") == 2
        assert types.count("REVENUE") == 1
        assert types.count("EXPENSE") == 5

        # Verify no duplicate account numbers
        numbers = [m.account_number for m in result.mapped_accounts]
        assert len(numbers) == len(set(numbers))


# ---------------------------------------------------------------------------
# Mapping tables completeness
# ---------------------------------------------------------------------------


class TestMappingTablesCompleteness:
    """Verify the mapping tables are internally consistent."""

    def test_all_type_mappings_produce_valid_account_types(self):
        valid_types = {"ASSET", "LIABILITY", "EQUITY", "REVENUE", "EXPENSE"}
        for qbo_type, account_type in QBO_TYPE_TO_ACCOUNT_TYPE.items():
            assert account_type in valid_types, (
                f"QBO type '{qbo_type}' maps to invalid account_type '{account_type}'"
            )

    def test_all_detail_type_mappings_are_non_empty_strings(self):
        for detail_type, sub_type in QBO_DETAIL_TO_SUB_TYPE.items():
            assert isinstance(sub_type, str) and len(sub_type) > 0, (
                f"QBO detail_type '{detail_type}' maps to empty sub_type"
            )
