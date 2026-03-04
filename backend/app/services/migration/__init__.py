"""
QuickBooks Online migration services.

This package provides CSV parsing, validation, and data models for
importing QuickBooks Online exports into the accounting system.
Module M1 — Parser and Validator (no database writes).
"""

from .qbo_parser import QBOParser
from .validator import QBOValidator, ValidationReport, ValidationError
from .models import (
    ParsedAccount,
    ParsedTransaction,
    ParsedCustomer,
    ParsedInvoice,
    ParsedVendor,
    ParsedEmployee,
    ParsedPayrollRecord,
    ParsedJournalEntry,
)

__all__ = [
    "QBOParser",
    "QBOValidator",
    "ValidationReport",
    "ValidationError",
    "ParsedAccount",
    "ParsedTransaction",
    "ParsedCustomer",
    "ParsedInvoice",
    "ParsedVendor",
    "ParsedEmployee",
    "ParsedPayrollRecord",
    "ParsedJournalEntry",
]
