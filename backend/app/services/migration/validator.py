"""
QBO CSV file validator.

Validates structural integrity, data types, and business rules
for QuickBooks Online CSV exports BEFORE parsing. Returns a
ValidationReport collecting all errors (does not stop on first error).
"""

import csv
import io
import re
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import IO, Union


class Severity(str, Enum):
    """Validation error severity."""

    FATAL = "FATAL"
    WARNING = "WARNING"


@dataclass
class ValidationError:
    """A single validation error found in a QBO CSV file."""

    file: str
    row: int
    column: str
    message: str
    severity: Severity = Severity.FATAL
    rule_id: str = ""


@dataclass
class ValidationReport:
    """Result of validating a QBO CSV file."""

    file_name: str
    records_scanned: int = 0
    errors: list[ValidationError] = field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        """True if no FATAL errors were found."""
        return not any(e.severity == Severity.FATAL for e in self.errors)

    @property
    def fatal_count(self) -> int:
        return sum(1 for e in self.errors if e.severity == Severity.FATAL)

    @property
    def warning_count(self) -> int:
        return sum(1 for e in self.errors if e.severity == Severity.WARNING)


# Required columns per CSV type (using normalized lowercase for matching).
# Alternate header names are grouped as tuples — any one match satisfies.
REQUIRED_COLUMNS: dict[str, list[Union[str, tuple[str, ...]]]] = {
    "chart_of_accounts": ["account", "type", "detail type"],
    "transactions": ["date", "transaction type", "amount"],
    "customers": ["customer"],
    "invoices": [
        ("invoice date", "date"),
        ("no.", "num", "invoice no", "invoice no."),
        "customer",
        ("due date", "due_date"),
        "amount",
    ],
    "vendors": [("vendor", "name")],
    "employees": [("employee", "name")],
    "payroll_summary": [
        ("employee", "name"),
        "gross pay",
    ],
    "general_journal": [
        "date",
        "account",
    ],
}

# Amount / currency pattern:  optional $ or (, digits with commas, optional decimals
_CURRENCY_RE = re.compile(
    r"^\s*[\$]?\s*\(?\s*[\-]?\s*[\d,]+(?:\.\d+)?\s*\)?\s*$"
)

_DATE_FORMATS = ["%m/%d/%Y", "%Y-%m-%d", "%m-%d-%Y", "%m/%d/%y"]


def _parse_date_check(value: str) -> bool:
    """Return True if *value* is parseable as a date."""
    for fmt in _DATE_FORMATS:
        try:
            datetime.strptime(value.strip(), fmt)
            return True
        except ValueError:
            continue
    return False


def _normalize_header(header: str) -> str:
    """Lowercase, strip whitespace, collapse internal whitespace."""
    return " ".join(header.lower().split())


def _open_reader(
    file_input: Union[str, Path, IO[str]],
) -> tuple[csv.DictReader, str, list[str]]:
    """
    Open *file_input* and return (DictReader, file_name, raw_lines).

    Handles file paths, Path objects, and StringIO/file-like objects.
    Skips QBO metadata/header rows that precede the actual CSV header.
    """
    if isinstance(file_input, (str, Path)):
        path = Path(file_input)
        file_name = path.name
        text = path.read_text(encoding="utf-8-sig")  # strips BOM
    else:
        file_name = getattr(file_input, "name", "<stream>")
        text = file_input.read()

    # Strip BOM if present (utf-8-sig handles file reads, but not StringIO)
    if text.startswith("\ufeff"):
        text = text[1:]

    lines = text.splitlines()
    return _build_reader(lines, file_name)


def _build_reader(
    lines: list[str], file_name: str
) -> tuple[csv.DictReader, str, list[str]]:
    """Find the real CSV header row among potential QBO metadata rows."""
    # Strategy: look for the first line that, when parsed as CSV, yields
    # at least 2 non-empty fields (QBO metadata rows are typically a
    # single value or blank).  We also stop if we see known header
    # patterns.
    header_idx = 0
    for i, line in enumerate(lines):
        stripped = line.strip()
        if not stripped:
            continue
        # Parse the line as CSV to count fields
        parsed = list(csv.reader([stripped]))[0]
        non_empty = [f for f in parsed if f.strip()]
        if len(non_empty) >= 2:
            header_idx = i
            break

    data_lines = lines[header_idx:]
    reader = csv.DictReader(io.StringIO("\n".join(data_lines)))
    return reader, file_name, data_lines


class QBOValidator:
    """Validates QBO CSV files before parsing."""

    def validate_file(
        self,
        file_input: Union[str, Path, IO[str]],
        expected_type: str,
    ) -> ValidationReport:
        """
        Validate a QBO CSV file.

        Parameters
        ----------
        file_input : path, Path, or file-like object
            The CSV to validate.
        expected_type : str
            One of: chart_of_accounts, transactions, customers, invoices,
            vendors, employees, payroll_summary, general_journal.

        Returns
        -------
        ValidationReport
        """
        file_name = "<unknown>"
        try:
            reader, file_name, data_lines = _open_reader(file_input)
        except Exception as exc:
            report = ValidationReport(file_name=file_name)
            report.errors.append(
                ValidationError(
                    file=file_name,
                    row=0,
                    column="",
                    message=f"Cannot read file: {exc}",
                    severity=Severity.FATAL,
                    rule_id="V-000",
                )
            )
            return report

        report = ValidationReport(file_name=file_name)

        # --- V-001: required columns present ---
        if reader.fieldnames is None:
            report.errors.append(
                ValidationError(
                    file=file_name,
                    row=0,
                    column="",
                    message="File appears empty or has no header row",
                    severity=Severity.FATAL,
                    rule_id="V-002",
                )
            )
            return report

        normalized_headers = [_normalize_header(h) for h in reader.fieldnames if h]
        required = REQUIRED_COLUMNS.get(expected_type, [])
        for req in required:
            if isinstance(req, tuple):
                # Any one of the alternatives satisfies
                if not any(alt in normalized_headers for alt in req):
                    report.errors.append(
                        ValidationError(
                            file=file_name,
                            row=0,
                            column=str(req),
                            message=(
                                f"Missing required column: one of {req}"
                            ),
                            severity=Severity.FATAL,
                            rule_id="V-001",
                        )
                    )
            else:
                if req not in normalized_headers:
                    report.errors.append(
                        ValidationError(
                            file=file_name,
                            row=0,
                            column=req,
                            message=f"Missing required column: '{req}'",
                            severity=Severity.FATAL,
                            rule_id="V-001",
                        )
                    )

        # --- Read all rows for data-level checks ---
        rows: list[dict] = []
        try:
            for row in reader:
                rows.append(row)
        except csv.Error as exc:
            report.errors.append(
                ValidationError(
                    file=file_name,
                    row=len(rows) + 2,
                    column="",
                    message=f"CSV parse error: {exc}",
                    severity=Severity.FATAL,
                    rule_id="V-003",
                )
            )
            return report

        # Filter out section header / subtotal / blank rows
        data_rows = []
        for row in rows:
            values = [v for v in row.values() if v and v.strip()]
            if len(values) == 0:
                continue  # blank row
            first_val = list(row.values())[0] or ""
            if first_val.strip().startswith("Total for"):
                continue  # subtotal row
            data_rows.append(row)

        report.records_scanned = len(data_rows)

        # --- V-002: no empty files ---
        if len(data_rows) == 0:
            # Headers-only is valid (empty result set)
            return report

        # --- Per-row validations ---
        date_columns = self._date_columns(expected_type)
        amount_columns = self._amount_columns(expected_type)
        required_value_columns = self._required_value_columns(expected_type)

        for i, row in enumerate(data_rows):
            row_num = i + 2  # +1 for header, +1 for 1-based

            # Check required value fields
            for col_spec in required_value_columns:
                col_name = self._resolve_column(col_spec, row)
                if col_name and not (row.get(col_name) or "").strip():
                    report.errors.append(
                        ValidationError(
                            file=file_name,
                            row=row_num,
                            column=col_name,
                            message=f"Required field '{col_name}' is empty",
                            severity=Severity.FATAL,
                            rule_id="V-010",
                        )
                    )

            # V-020: date validation
            for col_spec in date_columns:
                col_name = self._resolve_column(col_spec, row)
                if col_name:
                    val = (row.get(col_name) or "").strip()
                    if val and not _parse_date_check(val):
                        report.errors.append(
                            ValidationError(
                                file=file_name,
                                row=row_num,
                                column=col_name,
                                message=(
                                    f"Unparseable date '{val}' in column '{col_name}'"
                                ),
                                severity=Severity.FATAL,
                                rule_id="V-020",
                            )
                        )

            # V-022: amount validation
            for col_spec in amount_columns:
                col_name = self._resolve_column(col_spec, row)
                if col_name:
                    val = (row.get(col_name) or "").strip()
                    if val and not _CURRENCY_RE.match(val):
                        report.errors.append(
                            ValidationError(
                                file=file_name,
                                row=row_num,
                                column=col_name,
                                message=(
                                    f"Non-numeric amount '{val}' in column '{col_name}'"
                                ),
                                severity=Severity.FATAL,
                                rule_id="V-022",
                            )
                        )

        return report

    # --- Column specification helpers ---

    @staticmethod
    def _resolve_column(
        spec: Union[str, tuple[str, ...]], row: dict
    ) -> str | None:
        """Return the actual column name present in *row* for a spec."""
        if isinstance(spec, tuple):
            for alt in spec:
                # Case-insensitive match against row keys
                for key in row:
                    if _normalize_header(key) == alt:
                        return key
            return None
        for key in row:
            if _normalize_header(key) == spec:
                return key
        return None

    @staticmethod
    def _date_columns(expected_type: str) -> list[Union[str, tuple[str, ...]]]:
        mapping: dict[str, list] = {
            "chart_of_accounts": [],
            "transactions": ["date"],
            "customers": [],
            "invoices": [("invoice date", "date"), ("due date", "due_date")],
            "vendors": [],
            "employees": [("hire date", "hire_date")],
            "payroll_summary": [],
            "general_journal": ["date"],
        }
        return mapping.get(expected_type, [])

    @staticmethod
    def _amount_columns(expected_type: str) -> list[Union[str, tuple[str, ...]]]:
        mapping: dict[str, list] = {
            "chart_of_accounts": ["balance"],
            "transactions": ["amount", "balance"],
            "customers": [("open balance",)],
            "invoices": ["amount", ("open balance",)],
            "vendors": [],
            "employees": [("pay rate",)],
            "payroll_summary": [
                "gross pay",
                ("federal withholding",),
                ("net pay",),
            ],
            "general_journal": [("debit",), ("credit",)],
        }
        return mapping.get(expected_type, [])

    @staticmethod
    def _required_value_columns(
        expected_type: str,
    ) -> list[Union[str, tuple[str, ...]]]:
        mapping: dict[str, list] = {
            "chart_of_accounts": ["account", "type", "detail type"],
            "transactions": ["date", ("transaction type",), "amount"],
            "customers": ["customer"],
            "invoices": [
                ("invoice date", "date"),
                ("no.", "num", "invoice no", "invoice no."),
                "customer",
            ],
            "vendors": [("vendor", "name")],
            "employees": [("employee", "name")],
            "payroll_summary": [("employee", "name"), "gross pay"],
            "general_journal": ["date", "account"],
        }
        return mapping.get(expected_type, [])
