"""
Tests for Migration Audit Report (module M7).

Unit tests only — the report generator is a pure function that
transforms migration results into a report.
"""

import uuid
from datetime import date
from decimal import Decimal

import pytest

from app.services.migration.audit_report import (
    MigrationAuditReport,
    MigrationIssue,
    ClientMigrationSummary,
    generate_audit_report,
)
from app.services.migration.client_splitter import ClientDataset, UnmatchedRecord
from app.services.migration.coa_mapper import MappingResult, MappedAccount, UnmappedAccount
from app.services.migration.transaction_importer import ImportResult, SkippedTransaction
from app.services.migration.invoice_importer import InvoiceImportResult, SkippedInvoice
from app.services.migration.models import (
    ParsedAccount,
    ParsedTransaction,
    ParsedInvoice,
)


CLIENT_ID = uuid.uuid4()


class TestMigrationAuditReport:

    def test_empty_migration(self):
        report = generate_audit_report({})
        assert report.total_clients == 0
        assert report.total_issues == 0
        assert not report.has_errors

    def test_single_clean_client(self):
        datasets = {
            "Client A": ClientDataset(
                client_name="Client A",
                accounts=[ParsedAccount(name="Cash", type="Bank", detail_type="Checking")],
                transactions=[],
                invoices=[],
            ),
        }
        coa_results = {
            "Client A": MappingResult(
                total_input=1,
                total_mapped=1,
                total_unmapped=0,
                mapped_accounts=[MappedAccount(
                    client_id=CLIENT_ID,
                    account_number="1000",
                    account_name="Cash",
                    account_type="ASSET",
                    sub_type="Cash and Cash Equivalents",
                    original_qbo_type="Bank",
                    original_qbo_detail_type="Checking",
                    original_qbo_name="Cash",
                )],
            ),
        }

        report = generate_audit_report(datasets, coa_results=coa_results)
        assert report.total_clients == 1
        assert report.total_accounts_mapped == 1
        assert report.total_accounts_unmapped == 0

    def test_unmapped_accounts_flagged(self):
        datasets = {"Client A": ClientDataset(client_name="Client A")}
        coa_results = {
            "Client A": MappingResult(
                total_input=2,
                total_mapped=1,
                total_unmapped=1,
                unmapped_accounts=[UnmappedAccount(
                    original=ParsedAccount(name="Mystery", type="Unknown", detail_type=""),
                    reason="Type not recognized",
                )],
            ),
        }

        report = generate_audit_report(datasets, coa_results=coa_results)
        assert report.total_accounts_unmapped == 1
        assert len(report.client_summaries[0].issues) >= 1
        assert any("Unmapped" in i.description for i in report.client_summaries[0].issues)

    def test_skipped_transactions_flagged(self):
        datasets = {"Client A": ClientDataset(client_name="Client A")}
        txn_results = {
            "Client A": ImportResult(
                total_input=3,
                total_imported=2,
                total_skipped=1,
                skipped=[SkippedTransaction(
                    original=ParsedTransaction(
                        date=date(2024, 1, 1),
                        transaction_type="Check",
                        account="Unknown",
                        amount=Decimal("100"),
                    ),
                    reason="Account not found",
                )],
            ),
        }

        report = generate_audit_report(datasets, transaction_results=txn_results)
        assert report.total_transactions_skipped == 1

    def test_skipped_invoices_flagged(self):
        datasets = {"Client A": ClientDataset(client_name="Client A")}
        inv_results = {
            "Client A": InvoiceImportResult(
                total_input=2,
                total_imported=1,
                total_skipped=1,
                skipped=[SkippedInvoice(
                    original=ParsedInvoice(
                        invoice_date=date(2024, 1, 1),
                        invoice_no="DUP-001",
                        customer="Client X",
                        due_date=date(2024, 2, 1),
                        amount=Decimal("500"),
                    ),
                    reason="Duplicate invoice number",
                )],
            ),
        }

        report = generate_audit_report(datasets, invoice_results=inv_results)
        assert report.total_invoices_skipped == 1

    def test_unmatched_records_global(self):
        datasets = {
            "Client A": ClientDataset(client_name="Client A"),
            "__unmatched__": ClientDataset(
                client_name="__unmatched__",
                unmatched_records=[
                    UnmatchedRecord(
                        record_type="transaction",
                        record=ParsedTransaction(
                            date=date(2024, 1, 1),
                            transaction_type="Check",
                            account="Unknown",
                            amount=Decimal("50"),
                        ),
                        reason="No client match",
                    ),
                ],
            ),
        }

        report = generate_audit_report(datasets)
        assert report.total_unmatched_records == 1
        assert len(report.global_issues) == 1
        assert report.global_issues[0].category == "UNMATCHED"

    def test_no_accounts_is_error(self):
        datasets = {
            "Client A": ClientDataset(client_name="Client A", accounts=[]),
        }
        coa_results = {
            "Client A": MappingResult(total_input=0, total_mapped=0, total_unmapped=0),
        }

        report = generate_audit_report(datasets, coa_results=coa_results)
        assert report.has_errors
        assert any(
            i.severity == "ERROR" and "No chart of accounts" in i.description
            for i in report.client_summaries[0].issues
        )

    def test_text_report_generation(self):
        datasets = {
            "Client A": ClientDataset(
                client_name="Client A",
                accounts=[ParsedAccount(name="Cash", type="Bank", detail_type="Checking")],
            ),
        }

        report = generate_audit_report(datasets)
        text = report.to_text()

        assert "MIGRATION AUDIT REPORT" in text
        assert "Client A" in text
        assert "END OF REPORT" in text

    def test_has_errors_property(self):
        report = MigrationAuditReport()
        assert not report.has_errors

        report.global_issues.append(MigrationIssue(
            category="TEST", severity="WARNING", description="test",
        ))
        assert not report.has_errors

        report.global_issues.append(MigrationIssue(
            category="TEST", severity="ERROR", description="test error",
        ))
        assert report.has_errors

    def test_multiple_clients(self):
        datasets = {
            "Client A": ClientDataset(
                client_name="Client A",
                accounts=[ParsedAccount(name="Cash", type="Bank", detail_type="Checking")],
            ),
            "Client B": ClientDataset(
                client_name="Client B",
                accounts=[ParsedAccount(name="Cash", type="Bank", detail_type="Checking")],
            ),
        }
        coa_results = {
            "Client A": MappingResult(total_input=1, total_mapped=1, total_unmapped=0),
            "Client B": MappingResult(total_input=1, total_mapped=1, total_unmapped=0),
        }

        report = generate_audit_report(datasets, coa_results=coa_results)
        assert report.total_clients == 2
        assert report.total_accounts_mapped == 2
