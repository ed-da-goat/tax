"""
Chart of Accounts mapper for QuickBooks Online migration (module M3).

Maps QBO account types and detail types to the Georgia standard chart of
accounts used by this system. The mapping converts QBO's categorization
scheme (type + detail_type) into the 5-category account_type enum
(ASSET, LIABILITY, EQUITY, REVENUE, EXPENSE) and assigns standardized
account numbers in the Georgia CPA format.

This module does NOT write to the database — it transforms ParsedAccount
objects into MappedAccount objects that the importer (M4) will persist.

Usage:
    mapper = COAMapper()
    result = mapper.map_accounts(parsed_accounts, client_id)
    # result.mapped_accounts: ready to insert
    # result.unmapped_accounts: need manual review
    # result.warnings: informational messages
"""

import uuid
from dataclasses import dataclass, field
from decimal import Decimal

from .models import ParsedAccount


@dataclass
class MappedAccount:
    """A QBO account successfully mapped to the Georgia standard CoA."""

    client_id: uuid.UUID
    account_number: str
    account_name: str
    account_type: str  # ASSET, LIABILITY, EQUITY, REVENUE, EXPENSE
    sub_type: str | None
    original_qbo_type: str
    original_qbo_detail_type: str
    original_qbo_name: str
    balance: Decimal | None = None


@dataclass
class UnmappedAccount:
    """A QBO account that could not be automatically mapped."""

    original: ParsedAccount
    reason: str
    suggested_type: str | None = None
    suggested_number_prefix: str | None = None


@dataclass
class MappingResult:
    """Complete result of a chart of accounts mapping operation."""

    mapped_accounts: list[MappedAccount] = field(default_factory=list)
    unmapped_accounts: list[UnmappedAccount] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    total_input: int = 0
    total_mapped: int = 0
    total_unmapped: int = 0


# ---------------------------------------------------------------------------
# QBO type → Georgia standard account_type mapping
# ---------------------------------------------------------------------------
# QBO uses a two-level classification: type + detail_type.
# We map the top-level type to our 5-category enum, then use
# detail_type to assign a sub_type and number range.
# ---------------------------------------------------------------------------

QBO_TYPE_TO_ACCOUNT_TYPE: dict[str, str] = {
    # Assets
    "bank": "ASSET",
    "accounts receivable": "ASSET",
    "accounts receivable (a/r)": "ASSET",
    "other current asset": "ASSET",
    "other current assets": "ASSET",
    "fixed asset": "ASSET",
    "fixed assets": "ASSET",
    "other asset": "ASSET",
    "other assets": "ASSET",
    "current assets": "ASSET",
    # Liabilities
    "accounts payable": "LIABILITY",
    "accounts payable (a/p)": "LIABILITY",
    "credit card": "LIABILITY",
    "other current liability": "LIABILITY",
    "other current liabilities": "LIABILITY",
    "long term liability": "LIABILITY",
    "long term liabilities": "LIABILITY",
    "current liabilities": "LIABILITY",
    # Equity
    "equity": "EQUITY",
    # Revenue
    "income": "REVENUE",
    "other income": "REVENUE",
    "revenue": "REVENUE",
    # Expenses
    "expense": "EXPENSE",
    "expenses": "EXPENSE",
    "other expense": "EXPENSE",
    "other expenses": "EXPENSE",
    "cost of goods sold": "EXPENSE",
    "cogs": "EXPENSE",
}

# ---------------------------------------------------------------------------
# Account number prefix ranges by account_type + sub_type
# ---------------------------------------------------------------------------
# Georgia standard CoA numbering:
#   1000-1999: Assets
#   2000-2999: Liabilities
#   3000-3999: Equity
#   4000-4999: Revenue
#   5000-5999: Cost of Goods Sold
#   6000-7999: Operating Expenses
#   8000-8999: Other Income/Expense
#   9000-9999: Administrative/Other
# ---------------------------------------------------------------------------

_NUMBER_RANGES: dict[str, tuple[int, int]] = {
    "ASSET": (1000, 1999),
    "LIABILITY": (2000, 2999),
    "EQUITY": (3000, 3999),
    "REVENUE": (4000, 4999),
    "EXPENSE": (5000, 7999),
}

# Sub-type mapping from QBO detail_type
QBO_DETAIL_TO_SUB_TYPE: dict[str, str] = {
    # Asset sub-types
    "checking": "Cash and Cash Equivalents",
    "savings": "Cash and Cash Equivalents",
    "money market": "Cash and Cash Equivalents",
    "cash on hand": "Cash and Cash Equivalents",
    "cash and cash equivalents": "Cash and Cash Equivalents",
    "accounts receivable": "Accounts Receivable",
    "accounts receivable (a/r)": "Accounts Receivable",
    "allowance for bad debts": "Accounts Receivable",
    "inventory": "Inventory",
    "prepaid expenses": "Prepaid Expenses",
    "undeposited funds": "Cash and Cash Equivalents",
    "other current assets": "Other Current Asset",
    "other current asset": "Other Current Asset",
    "furniture & fixtures": "Fixed Asset",
    "furniture and fixtures": "Fixed Asset",
    "machinery & equipment": "Fixed Asset",
    "machinery and equipment": "Fixed Asset",
    "vehicles": "Fixed Asset",
    "buildings": "Fixed Asset",
    "land": "Fixed Asset",
    "leasehold improvements": "Fixed Asset",
    "accumulated depreciation": "Accumulated Depreciation",
    "other fixed assets": "Fixed Asset",
    "other fixed asset": "Fixed Asset",
    # Liability sub-types
    "accounts payable": "Accounts Payable",
    "accounts payable (a/p)": "Accounts Payable",
    "credit card": "Credit Card",
    "payroll liabilities": "Payroll Liabilities",
    "payroll clearing": "Payroll Liabilities",
    "federal tax payable": "Payroll Liabilities",
    "state tax payable": "Payroll Liabilities",
    "sales tax payable": "Sales Tax Payable",
    "line of credit": "Short-Term Debt",
    "other current liabilities": "Other Current Liability",
    "other current liability": "Other Current Liability",
    "notes payable": "Long-Term Debt",
    "long term debt": "Long-Term Debt",
    "other long term liabilities": "Other Long-Term Liability",
    "other long-term liabilities": "Other Long-Term Liability",
    "shareholder notes payable": "Long-Term Debt",
    # Equity sub-types
    "opening balance equity": "Opening Balance Equity",
    "owner's equity": "Owner's Equity",
    "owners equity": "Owner's Equity",
    "partner's equity": "Owner's Equity",
    "retained earnings": "Retained Earnings",
    "common stock": "Common Stock",
    "preferred stock": "Preferred Stock",
    "paid-in capital": "Paid-in Capital",
    "additional paid-in capital": "Paid-in Capital",
    "owner's draw": "Owner's Draw",
    "owner draws": "Owner's Draw",
    "partner distributions": "Owner's Draw",
    "accumulated adjustment": "Retained Earnings",
    # Revenue sub-types
    "sales of product income": "Sales Revenue",
    "service/fee income": "Service Revenue",
    "service income": "Service Revenue",
    "fee income": "Service Revenue",
    "non-profit income": "Other Revenue",
    "unapplied cash payment income": "Other Revenue",
    "discounts/refunds given": "Sales Discounts",
    "other primary income": "Other Revenue",
    "other income": "Other Income",
    "interest earned": "Interest Income",
    "dividend income": "Dividend Income",
    "other investment income": "Investment Income",
    # Expense sub-types
    "advertising": "Advertising",
    "advertising/promotional": "Advertising",
    "auto": "Auto Expense",
    "auto expense": "Auto Expense",
    "bad debts": "Bad Debt",
    "bank charges": "Bank Charges",
    "bank charges & fees": "Bank Charges",
    "charitable contributions": "Charitable Contributions",
    "cost of labor": "Cost of Goods Sold",
    "equipment rental": "Equipment Rental",
    "insurance": "Insurance",
    "insurance - general": "Insurance",
    "interest paid": "Interest Expense",
    "legal & professional fees": "Professional Fees",
    "legal and professional fees": "Professional Fees",
    "meals and entertainment": "Meals and Entertainment",
    "office/general administrative expenses": "Office Expense",
    "office expenses": "Office Expense",
    "other business expenses": "Other Expense",
    "other miscellaneous expense": "Other Expense",
    "other miscellaneous service cost": "Other Expense",
    "payroll expenses": "Payroll Expense",
    "rent or lease": "Rent Expense",
    "rent or lease of buildings": "Rent Expense",
    "repair & maintenance": "Repairs and Maintenance",
    "repair and maintenance": "Repairs and Maintenance",
    "shipping, freight & delivery": "Shipping",
    "shipping and delivery expense": "Shipping",
    "supplies & materials": "Supplies",
    "supplies and materials": "Supplies",
    "taxes & licenses": "Taxes and Licenses",
    "taxes and licenses": "Taxes and Licenses",
    "travel": "Travel",
    "travel expense": "Travel",
    "travel meals": "Meals and Entertainment",
    "utilities": "Utilities",
    "depreciation": "Depreciation",
    "amortization": "Amortization",
    "dues & subscriptions": "Dues and Subscriptions",
    "dues and subscriptions": "Dues and Subscriptions",
    "cost of goods sold": "Cost of Goods Sold",
    "supplies & materials - cogs": "Cost of Goods Sold",
    "other costs of services": "Cost of Goods Sold",
}


class COAMapper:
    """
    Maps QuickBooks Online chart of accounts to Georgia standard categories.

    The mapper:
    1. Converts QBO type to the 5-category account_type enum
    2. Converts QBO detail_type to a sub_type classification
    3. Assigns sequential account numbers within the correct range
    4. Preserves the original QBO name as the account_name
    5. Flags accounts that cannot be automatically mapped
    """

    def __init__(self) -> None:
        # Track assigned numbers per account_type to avoid collisions
        self._counters: dict[str, int] = {}

    def _next_account_number(self, account_type: str) -> str:
        """Generate the next sequential account number for a given type."""
        if account_type not in self._counters:
            start, _ = _NUMBER_RANGES.get(account_type, (9000, 9999))
            self._counters[account_type] = start

        number = self._counters[account_type]
        self._counters[account_type] = number + 1

        _, end = _NUMBER_RANGES.get(account_type, (9000, 9999))
        if number > end:
            # Overflow — should not happen in practice for <200 accounts
            return str(number)

        return str(number)

    def _resolve_account_type(self, qbo_type: str) -> str | None:
        """Resolve a QBO account type string to our standard account_type."""
        return QBO_TYPE_TO_ACCOUNT_TYPE.get(qbo_type.lower().strip())

    def _resolve_sub_type(self, qbo_detail_type: str) -> str | None:
        """Resolve a QBO detail_type string to our standard sub_type."""
        return QBO_DETAIL_TO_SUB_TYPE.get(qbo_detail_type.lower().strip())

    def map_accounts(
        self,
        parsed_accounts: list[ParsedAccount],
        client_id: uuid.UUID,
    ) -> MappingResult:
        """
        Map a list of parsed QBO accounts to the Georgia standard CoA.

        Parameters
        ----------
        parsed_accounts : list[ParsedAccount]
            Accounts produced by QBOParser.parse_chart_of_accounts().
        client_id : uuid.UUID
            The client these accounts belong to.

        Returns
        -------
        MappingResult
            Contains mapped accounts, unmapped accounts, and warnings.
        """
        result = MappingResult(total_input=len(parsed_accounts))

        # Reset counters for this mapping run
        self._counters = {}

        # If a ParsedAccount has an existing account_number, try to use it
        used_numbers: set[str] = set()

        for acct in parsed_accounts:
            account_type = self._resolve_account_type(acct.type)

            if account_type is None:
                result.unmapped_accounts.append(UnmappedAccount(
                    original=acct,
                    reason=f"QBO type '{acct.type}' not recognized",
                    suggested_type=None,
                    suggested_number_prefix=None,
                ))
                continue

            sub_type = self._resolve_sub_type(acct.detail_type) if acct.detail_type else None

            # Use the QBO-provided account number if available and valid
            if acct.account_number and acct.account_number not in used_numbers:
                account_number = acct.account_number
            else:
                account_number = self._next_account_number(account_type)
                # Ensure no collision
                while account_number in used_numbers:
                    account_number = self._next_account_number(account_type)

            used_numbers.add(account_number)

            # Extract the leaf account name (QBO uses colon-delimited
            # hierarchy like "Expenses:Office Supplies:Paper")
            account_name = acct.name
            if ":" in account_name:
                # Use the full path but note the hierarchy
                result.warnings.append(
                    f"Account '{acct.name}' is a sub-account (colon-delimited). "
                    f"Mapped as flat account with full path name."
                )

            mapped = MappedAccount(
                client_id=client_id,
                account_number=account_number,
                account_name=account_name,
                account_type=account_type,
                sub_type=sub_type,
                original_qbo_type=acct.type,
                original_qbo_detail_type=acct.detail_type,
                original_qbo_name=acct.name,
                balance=acct.balance,
            )
            result.mapped_accounts.append(mapped)

        result.total_mapped = len(result.mapped_accounts)
        result.total_unmapped = len(result.unmapped_accounts)

        return result
