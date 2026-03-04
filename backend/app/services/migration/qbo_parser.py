"""
QuickBooks Online CSV parser.

Parses QBO CSV exports into structured Pydantic model objects.
Does NOT write to the database — this is a pure parse-and-validate
layer consumed by the migration agent (M2-M7).

Each parse method:
  1. Accepts a file path (str/Path) or file-like object (StringIO).
  2. Validates required columns exist.
  3. Parses each row into the corresponding Pydantic model.
  4. Collects all errors without stopping (report ALL issues).
  5. Returns a ParseResult with parsed records and any errors.
"""

import csv
import io
import re
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import IO, Union

from .models import (
    ParsedAccount,
    ParsedCustomer,
    ParsedEmployee,
    ParsedInvoice,
    ParsedJournalEntry,
    ParsedPayrollRecord,
    ParsedTransaction,
    ParsedVendor,
)
from .validator import ValidationError, Severity


@dataclass
class ParseResult[T]:
    """Container for parsed records and any errors encountered."""

    records: list[T] = field(default_factory=list)
    errors: list[ValidationError] = field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        return not any(e.severity == Severity.FATAL for e in self.errors)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

_DATE_FORMATS = ["%m/%d/%Y", "%Y-%m-%d", "%m-%d-%Y", "%m/%d/%y"]

# Matches currency values: $1,234.56  or  (1,234.56)  or  -1234.56  etc.
_STRIP_CURRENCY_RE = re.compile(r"[^\d.\-]")


def _parse_date(value: str | None) -> date | None:
    """Parse a date string trying multiple QBO formats."""
    if not value or not value.strip():
        return None
    clean = value.strip()
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(clean, fmt).date()
        except ValueError:
            continue
    return None


def _parse_amount(value: str | None) -> Decimal | None:
    """
    Parse a QBO currency string to Decimal.

    Handles: $1,234.56   (1,234.56)   -1234.56   1234   etc.
    Returns None for empty/blank values.
    """
    if not value or not value.strip():
        return None
    clean = value.strip()

    # Detect parenthesized negatives: (1,234.56)
    is_negative = "(" in clean and ")" in clean

    # Strip everything except digits, dot, minus
    numeric = _STRIP_CURRENCY_RE.sub("", clean)
    if not numeric:
        return None

    try:
        result = Decimal(numeric)
    except InvalidOperation:
        return None

    if is_negative and result > 0:
        result = -result

    return result


def _normalize_header(header: str) -> str:
    """Lowercase and collapse whitespace."""
    return " ".join(header.lower().split())


def _get(row: dict, *candidates: str) -> str:
    """
    Get a value from *row* by trying multiple column names
    (case-insensitive). Returns empty string if none found.
    """
    for candidate in candidates:
        for key, val in row.items():
            if _normalize_header(key) == candidate:
                return (val or "").strip()
    return ""


def _read_csv(
    file_input: Union[str, Path, IO[str]],
) -> tuple[list[dict], str]:
    """
    Read a QBO CSV, skip metadata/header rows, return (rows, file_name).

    QBO exports often have 1-4 metadata rows before the real CSV header.
    We detect the header as the first row with >= 2 non-empty fields.
    Also filters out section-header rows, subtotal rows, and blanks.
    """
    if isinstance(file_input, (str, Path)):
        path = Path(file_input)
        file_name = path.name
        text = path.read_text(encoding="utf-8-sig")
    else:
        file_name = getattr(file_input, "name", "<stream>")
        text = file_input.read()

    # Strip BOM
    if text.startswith("\ufeff"):
        text = text[1:]

    lines = text.splitlines()
    if not lines:
        return [], file_name

    # Find real CSV header
    header_idx = 0
    for i, line in enumerate(lines):
        stripped = line.strip()
        if not stripped:
            continue
        parsed = list(csv.reader([stripped]))[0]
        non_empty = [f for f in parsed if f.strip()]
        if len(non_empty) >= 2:
            header_idx = i
            break

    data_text = "\n".join(lines[header_idx:])
    reader = csv.DictReader(io.StringIO(data_text))
    rows = []
    for row in reader:
        # Skip blank rows
        values = [v for v in row.values() if v and v.strip()]
        if not values:
            continue
        # Skip subtotal rows
        first = list(row.values())[0] or ""
        if first.strip().startswith("Total for") or first.strip() == "TOTAL":
            continue
        # Skip section header rows (single non-empty value, rest empty)
        if len(values) == 1:
            continue
        rows.append(row)

    return rows, file_name


def _col_present(rows: list[dict], *candidates: str) -> bool:
    """Check if at least one row has a key matching any candidate."""
    if not rows:
        return False
    first = rows[0]
    for candidate in candidates:
        for key in first:
            if _normalize_header(key) == candidate:
                return True
    return False


# ---------------------------------------------------------------------------
# Main parser class
# ---------------------------------------------------------------------------


class QBOParser:
    """
    Parses QuickBooks Online CSV exports into structured Python objects.

    Each parse_* method accepts a file path or file-like object (StringIO)
    and returns a ParseResult containing the parsed records and any
    validation errors encountered during parsing.
    """

    def parse_chart_of_accounts(
        self, file_input: Union[str, Path, IO[str]]
    ) -> ParseResult[ParsedAccount]:
        """Parse a QBO Chart of Accounts CSV export."""
        result: ParseResult[ParsedAccount] = ParseResult()
        rows, fname = _read_csv(file_input)

        if not rows:
            return result

        # Validate required columns
        for col in ("account", "type", "detail type"):
            if not _col_present(rows, col):
                result.errors.append(
                    ValidationError(
                        file=fname, row=0, column=col,
                        message=f"Missing required column: '{col}'",
                        severity=Severity.FATAL, rule_id="V-001",
                    )
                )
        if not result.is_valid:
            return result

        for i, row in enumerate(rows):
            row_num = i + 2
            try:
                name = _get(row, "account")
                acct_type = _get(row, "type")
                detail = _get(row, "detail type")

                if not name:
                    result.errors.append(
                        ValidationError(
                            file=fname, row=row_num, column="Account",
                            message="Account name is empty",
                            severity=Severity.FATAL, rule_id="V-010",
                        )
                    )
                    continue

                balance = _parse_amount(_get(row, "balance"))
                balance_raw = _get(row, "balance")
                if balance_raw and balance is None:
                    result.errors.append(
                        ValidationError(
                            file=fname, row=row_num, column="Balance",
                            message=f"Non-numeric balance: '{balance_raw}'",
                            severity=Severity.FATAL, rule_id="V-022",
                        )
                    )
                    continue

                result.records.append(ParsedAccount(
                    name=name,
                    type=acct_type,
                    detail_type=detail,
                    description=_get(row, "description") or None,
                    balance=balance,
                    currency=_get(row, "currency") or None,
                    account_number=_get(row, "account #", "account number") or None,
                ))
            except Exception as exc:
                result.errors.append(
                    ValidationError(
                        file=fname, row=row_num, column="",
                        message=f"Parse error: {exc}",
                        severity=Severity.FATAL, rule_id="V-099",
                    )
                )

        return result

    def parse_transactions(
        self, file_input: Union[str, Path, IO[str]]
    ) -> ParseResult[ParsedTransaction]:
        """Parse a QBO Transaction Detail by Account CSV export."""
        result: ParseResult[ParsedTransaction] = ParseResult()
        rows, fname = _read_csv(file_input)

        if not rows:
            return result

        for col in ("date", "transaction type", "amount"):
            if not _col_present(rows, col):
                result.errors.append(
                    ValidationError(
                        file=fname, row=0, column=col,
                        message=f"Missing required column: '{col}'",
                        severity=Severity.FATAL, rule_id="V-001",
                    )
                )
        if not result.is_valid:
            return result

        for i, row in enumerate(rows):
            row_num = i + 2
            try:
                date_str = _get(row, "date")
                parsed_date = _parse_date(date_str)
                if not parsed_date:
                    result.errors.append(
                        ValidationError(
                            file=fname, row=row_num, column="Date",
                            message=f"Unparseable date: '{date_str}'",
                            severity=Severity.FATAL, rule_id="V-020",
                        )
                    )
                    continue

                amount_str = _get(row, "amount")
                amount = _parse_amount(amount_str)
                if amount is None:
                    result.errors.append(
                        ValidationError(
                            file=fname, row=row_num, column="Amount",
                            message=f"Non-numeric amount: '{amount_str}'",
                            severity=Severity.FATAL, rule_id="V-022",
                        )
                    )
                    continue

                account = _get(row, "account")
                txn_type = _get(row, "transaction type")

                result.records.append(ParsedTransaction(
                    date=parsed_date,
                    transaction_type=txn_type,
                    num=_get(row, "no.", "num") or None,
                    name=_get(row, "name") or None,
                    memo=_get(row, "memo/description", "memo", "description") or None,
                    account=account if account else txn_type,
                    split=_get(row, "split") or None,
                    amount=amount,
                    balance=_parse_amount(_get(row, "balance")),
                ))
            except Exception as exc:
                result.errors.append(
                    ValidationError(
                        file=fname, row=row_num, column="",
                        message=f"Parse error: {exc}",
                        severity=Severity.FATAL, rule_id="V-099",
                    )
                )

        return result

    def parse_customers(
        self, file_input: Union[str, Path, IO[str]]
    ) -> ParseResult[ParsedCustomer]:
        """Parse a QBO Customer Contact List CSV export."""
        result: ParseResult[ParsedCustomer] = ParseResult()
        rows, fname = _read_csv(file_input)

        if not rows:
            return result

        if not _col_present(rows, "customer"):
            result.errors.append(
                ValidationError(
                    file=fname, row=0, column="customer",
                    message="Missing required column: 'customer'",
                    severity=Severity.FATAL, rule_id="V-001",
                )
            )
            return result

        for i, row in enumerate(rows):
            row_num = i + 2
            try:
                name = _get(row, "customer")
                if not name:
                    result.errors.append(
                        ValidationError(
                            file=fname, row=row_num, column="Customer",
                            message="Customer name is empty",
                            severity=Severity.FATAL, rule_id="V-010",
                        )
                    )
                    continue

                result.records.append(ParsedCustomer(
                    name=name,
                    company=_get(row, "company") or None,
                    email=_get(row, "email") or None,
                    phone=_get(row, "phone") or None,
                    billing_street=_get(row, "billing street", "street") or None,
                    billing_city=_get(row, "billing city", "city") or None,
                    billing_state=_get(row, "billing state", "state") or None,
                    billing_zip=_get(row, "billing zip", "zip") or None,
                    open_balance=_parse_amount(_get(row, "open balance")),
                ))
            except Exception as exc:
                result.errors.append(
                    ValidationError(
                        file=fname, row=row_num, column="",
                        message=f"Parse error: {exc}",
                        severity=Severity.FATAL, rule_id="V-099",
                    )
                )

        return result

    def parse_invoices(
        self, file_input: Union[str, Path, IO[str]]
    ) -> ParseResult[ParsedInvoice]:
        """Parse a QBO Invoice List CSV export."""
        result: ParseResult[ParsedInvoice] = ParseResult()
        rows, fname = _read_csv(file_input)

        if not rows:
            return result

        # Check required columns
        required_checks = [
            (("invoice date", "date"), "Invoice Date"),
            (("no.", "num", "invoice no", "invoice no."), "No."),
            (("customer",), "Customer"),
            (("due date", "due_date"), "Due Date"),
            (("amount",), "Amount"),
        ]
        for candidates, display in required_checks:
            if not _col_present(rows, *candidates):
                result.errors.append(
                    ValidationError(
                        file=fname, row=0, column=display,
                        message=f"Missing required column: '{display}'",
                        severity=Severity.FATAL, rule_id="V-001",
                    )
                )
        if not result.is_valid:
            return result

        for i, row in enumerate(rows):
            row_num = i + 2
            try:
                inv_date_str = _get(row, "invoice date", "date")
                inv_date = _parse_date(inv_date_str)
                if not inv_date:
                    result.errors.append(
                        ValidationError(
                            file=fname, row=row_num, column="Invoice Date",
                            message=f"Unparseable date: '{inv_date_str}'",
                            severity=Severity.FATAL, rule_id="V-020",
                        )
                    )
                    continue

                due_date_str = _get(row, "due date", "due_date")
                due_date = _parse_date(due_date_str)
                if not due_date:
                    result.errors.append(
                        ValidationError(
                            file=fname, row=row_num, column="Due Date",
                            message=f"Unparseable due date: '{due_date_str}'",
                            severity=Severity.FATAL, rule_id="V-020",
                        )
                    )
                    continue

                inv_no = _get(row, "no.", "num", "invoice no", "invoice no.")
                customer = _get(row, "customer")
                amount_str = _get(row, "amount")
                amount = _parse_amount(amount_str)

                if not inv_no:
                    result.errors.append(
                        ValidationError(
                            file=fname, row=row_num, column="No.",
                            message="Invoice number is empty",
                            severity=Severity.FATAL, rule_id="V-010",
                        )
                    )
                    continue

                if amount is None:
                    result.errors.append(
                        ValidationError(
                            file=fname, row=row_num, column="Amount",
                            message=f"Non-numeric amount: '{amount_str}'",
                            severity=Severity.FATAL, rule_id="V-022",
                        )
                    )
                    continue

                result.records.append(ParsedInvoice(
                    invoice_date=inv_date,
                    invoice_no=inv_no,
                    customer=customer,
                    due_date=due_date,
                    amount=amount,
                    open_balance=_parse_amount(_get(row, "open balance")),
                    status=_get(row, "status") or None,
                ))
            except Exception as exc:
                result.errors.append(
                    ValidationError(
                        file=fname, row=row_num, column="",
                        message=f"Parse error: {exc}",
                        severity=Severity.FATAL, rule_id="V-099",
                    )
                )

        return result

    def parse_vendors(
        self, file_input: Union[str, Path, IO[str]]
    ) -> ParseResult[ParsedVendor]:
        """Parse a QBO Vendor Contact List CSV export."""
        result: ParseResult[ParsedVendor] = ParseResult()
        rows, fname = _read_csv(file_input)

        if not rows:
            return result

        if not (_col_present(rows, "vendor") or _col_present(rows, "name")):
            result.errors.append(
                ValidationError(
                    file=fname, row=0, column="vendor",
                    message="Missing required column: 'Vendor' or 'Name'",
                    severity=Severity.FATAL, rule_id="V-001",
                )
            )
            return result

        for i, row in enumerate(rows):
            row_num = i + 2
            try:
                name = _get(row, "vendor", "name")
                if not name:
                    result.errors.append(
                        ValidationError(
                            file=fname, row=row_num, column="Vendor",
                            message="Vendor name is empty",
                            severity=Severity.FATAL, rule_id="V-010",
                        )
                    )
                    continue

                result.records.append(ParsedVendor(
                    name=name,
                    company=_get(row, "company") or None,
                    email=_get(row, "email") or None,
                    phone=_get(row, "phone") or None,
                    street=_get(row, "street") or None,
                    city=_get(row, "city") or None,
                    state=_get(row, "state") or None,
                    zip=_get(row, "zip") or None,
                ))
            except Exception as exc:
                result.errors.append(
                    ValidationError(
                        file=fname, row=row_num, column="",
                        message=f"Parse error: {exc}",
                        severity=Severity.FATAL, rule_id="V-099",
                    )
                )

        return result

    def parse_employees(
        self, file_input: Union[str, Path, IO[str]]
    ) -> ParseResult[ParsedEmployee]:
        """Parse a QBO Employee Details CSV export."""
        result: ParseResult[ParsedEmployee] = ParseResult()
        rows, fname = _read_csv(file_input)

        if not rows:
            return result

        if not (_col_present(rows, "employee") or _col_present(rows, "name")):
            result.errors.append(
                ValidationError(
                    file=fname, row=0, column="employee",
                    message="Missing required column: 'Employee' or 'Name'",
                    severity=Severity.FATAL, rule_id="V-001",
                )
            )
            return result

        for i, row in enumerate(rows):
            row_num = i + 2
            try:
                name = _get(row, "employee", "name")
                if not name:
                    result.errors.append(
                        ValidationError(
                            file=fname, row=row_num, column="Employee",
                            message="Employee name is empty",
                            severity=Severity.FATAL, rule_id="V-010",
                        )
                    )
                    continue

                result.records.append(ParsedEmployee(
                    name=name,
                    ssn_last4=_get(row, "ssn (last 4)", "ssn") or None,
                    hire_date=_parse_date(_get(row, "hire date", "hire_date")),
                    status=_get(row, "status") or None,
                    pay_type=_get(row, "pay type", "pay_type") or None,
                    pay_rate=_parse_amount(_get(row, "pay rate", "pay_rate")),
                    filing_status=_get(row, "filing status", "filing_status",
                                       "filing status (federal)") or None,
                ))
            except Exception as exc:
                result.errors.append(
                    ValidationError(
                        file=fname, row=row_num, column="",
                        message=f"Parse error: {exc}",
                        severity=Severity.FATAL, rule_id="V-099",
                    )
                )

        return result

    def parse_payroll_summary(
        self, file_input: Union[str, Path, IO[str]]
    ) -> ParseResult[ParsedPayrollRecord]:
        """Parse a QBO Payroll Summary CSV export."""
        result: ParseResult[ParsedPayrollRecord] = ParseResult()
        rows, fname = _read_csv(file_input)

        if not rows:
            return result

        if not (_col_present(rows, "employee") or _col_present(rows, "name")):
            result.errors.append(
                ValidationError(
                    file=fname, row=0, column="employee",
                    message="Missing required column: 'Employee' or 'Name'",
                    severity=Severity.FATAL, rule_id="V-001",
                )
            )
            return result

        if not _col_present(rows, "gross pay"):
            result.errors.append(
                ValidationError(
                    file=fname, row=0, column="gross pay",
                    message="Missing required column: 'Gross Pay'",
                    severity=Severity.FATAL, rule_id="V-001",
                )
            )
            return result

        for i, row in enumerate(rows):
            row_num = i + 2
            try:
                employee = _get(row, "employee", "name")
                if not employee:
                    result.errors.append(
                        ValidationError(
                            file=fname, row=row_num, column="Employee",
                            message="Employee name is empty",
                            severity=Severity.FATAL, rule_id="V-010",
                        )
                    )
                    continue

                gross_str = _get(row, "gross pay")
                gross = _parse_amount(gross_str)
                if gross is None:
                    result.errors.append(
                        ValidationError(
                            file=fname, row=row_num, column="Gross Pay",
                            message=f"Non-numeric gross pay: '{gross_str}'",
                            severity=Severity.FATAL, rule_id="V-022",
                        )
                    )
                    continue

                result.records.append(ParsedPayrollRecord(
                    employee=employee,
                    gross_pay=gross,
                    federal_withholding=_parse_amount(
                        _get(row, "federal withholding", "federal tax", "fed wh")
                    ),
                    state_withholding=_parse_amount(
                        _get(row, "ga withholding", "georgia withholding",
                             "state withholding", "state withholding - ga",
                             "state tax")
                    ),
                    social_security=_parse_amount(
                        _get(row, "social security employee", "social security",
                             "ss employee", "employee ss")
                    ),
                    medicare=_parse_amount(
                        _get(row, "medicare employee", "medicare",
                             "employee medicare")
                    ),
                    net_pay=_parse_amount(_get(row, "net pay")),
                    ga_suta=_parse_amount(
                        _get(row, "ga sui", "ga unemployment",
                             "state unemployment - ga", "ga suta")
                    ),
                    futa=_parse_amount(
                        _get(row, "federal unemployment", "futa")
                    ),
                ))
            except Exception as exc:
                result.errors.append(
                    ValidationError(
                        file=fname, row=row_num, column="",
                        message=f"Parse error: {exc}",
                        severity=Severity.FATAL, rule_id="V-099",
                    )
                )

        return result

    def parse_general_journal(
        self, file_input: Union[str, Path, IO[str]]
    ) -> ParseResult[ParsedJournalEntry]:
        """Parse a QBO General Journal CSV export."""
        result: ParseResult[ParsedJournalEntry] = ParseResult()
        rows, fname = _read_csv(file_input)

        if not rows:
            return result

        if not _col_present(rows, "date"):
            result.errors.append(
                ValidationError(
                    file=fname, row=0, column="date",
                    message="Missing required column: 'Date'",
                    severity=Severity.FATAL, rule_id="V-001",
                )
            )
        if not _col_present(rows, "account"):
            result.errors.append(
                ValidationError(
                    file=fname, row=0, column="account",
                    message="Missing required column: 'Account'",
                    severity=Severity.FATAL, rule_id="V-001",
                )
            )
        if not result.is_valid:
            return result

        for i, row in enumerate(rows):
            row_num = i + 2
            try:
                date_str = _get(row, "date")
                parsed_date = _parse_date(date_str)
                if not parsed_date:
                    result.errors.append(
                        ValidationError(
                            file=fname, row=row_num, column="Date",
                            message=f"Unparseable date: '{date_str}'",
                            severity=Severity.FATAL, rule_id="V-020",
                        )
                    )
                    continue

                account = _get(row, "account")
                if not account:
                    result.errors.append(
                        ValidationError(
                            file=fname, row=row_num, column="Account",
                            message="Account is empty",
                            severity=Severity.FATAL, rule_id="V-010",
                        )
                    )
                    continue

                debit_raw = _get(row, "debit")
                credit_raw = _get(row, "credit")
                debit = _parse_amount(debit_raw)
                credit = _parse_amount(credit_raw)

                # Validate numeric if non-empty
                if debit_raw and debit is None:
                    result.errors.append(
                        ValidationError(
                            file=fname, row=row_num, column="Debit",
                            message=f"Non-numeric debit: '{debit_raw}'",
                            severity=Severity.FATAL, rule_id="V-022",
                        )
                    )
                    continue
                if credit_raw and credit is None:
                    result.errors.append(
                        ValidationError(
                            file=fname, row=row_num, column="Credit",
                            message=f"Non-numeric credit: '{credit_raw}'",
                            severity=Severity.FATAL, rule_id="V-022",
                        )
                    )
                    continue

                result.records.append(ParsedJournalEntry(
                    date=parsed_date,
                    entry_no=_get(row, "no.", "num", "entry no", "entry no.") or None,
                    account=account,
                    debit=debit,
                    credit=credit,
                    name=_get(row, "name") or None,
                    memo=_get(row, "memo/description", "memo", "description") or None,
                ))
            except Exception as exc:
                result.errors.append(
                    ValidationError(
                        file=fname, row=row_num, column="",
                        message=f"Parse error: {exc}",
                        severity=Severity.FATAL, rule_id="V-099",
                    )
                )

        return result
