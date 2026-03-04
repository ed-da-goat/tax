"""
Migration audit report generator (module M7).

Produces a comprehensive summary of a QBO migration, flagging any data
that didn't map cleanly. The report is intended for CPA review before
the migration is finalized.

This module is a pure reporting layer — it does not modify any data.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone

from .coa_mapper import MappingResult
from .transaction_importer import ImportResult as TransactionImportResult
from .invoice_importer import InvoiceImportResult
from .client_splitter import ClientDataset


@dataclass
class MigrationIssue:
    """A single issue flagged during migration."""

    category: str  # ACCOUNT_MAPPING, TRANSACTION, INVOICE, UNMATCHED, DATA_QUALITY
    severity: str  # ERROR, WARNING, INFO
    description: str
    details: str | None = None


@dataclass
class ClientMigrationSummary:
    """Migration summary for a single client."""

    client_name: str
    accounts_mapped: int = 0
    accounts_unmapped: int = 0
    transactions_imported: int = 0
    transactions_skipped: int = 0
    invoices_imported: int = 0
    invoices_skipped: int = 0
    unmatched_records: int = 0
    issues: list[MigrationIssue] = field(default_factory=list)


@dataclass
class MigrationAuditReport:
    """Complete audit report for a QBO → Georgia CPA migration."""

    generated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    client_summaries: list[ClientMigrationSummary] = field(default_factory=list)
    global_issues: list[MigrationIssue] = field(default_factory=list)

    # Totals
    total_clients: int = 0
    total_accounts_mapped: int = 0
    total_accounts_unmapped: int = 0
    total_transactions_imported: int = 0
    total_transactions_skipped: int = 0
    total_invoices_imported: int = 0
    total_invoices_skipped: int = 0
    total_unmatched_records: int = 0

    @property
    def has_errors(self) -> bool:
        """Return True if any ERROR-severity issues exist."""
        for issue in self.global_issues:
            if issue.severity == "ERROR":
                return True
        for summary in self.client_summaries:
            for issue in summary.issues:
                if issue.severity == "ERROR":
                    return True
        return False

    @property
    def total_issues(self) -> int:
        count = len(self.global_issues)
        for summary in self.client_summaries:
            count += len(summary.issues)
        return count

    def to_text(self) -> str:
        """Generate a human-readable text report."""
        lines = [
            "=" * 72,
            "QUICKBOOKS ONLINE → GEORGIA CPA MIGRATION AUDIT REPORT",
            f"Generated: {self.generated_at.strftime('%Y-%m-%d %H:%M:%S UTC')}",
            "=" * 72,
            "",
            "SUMMARY",
            "-" * 40,
            f"  Clients migrated:        {self.total_clients}",
            f"  Accounts mapped:         {self.total_accounts_mapped}",
            f"  Accounts unmapped:       {self.total_accounts_unmapped}",
            f"  Transactions imported:   {self.total_transactions_imported}",
            f"  Transactions skipped:    {self.total_transactions_skipped}",
            f"  Invoices imported:       {self.total_invoices_imported}",
            f"  Invoices skipped:        {self.total_invoices_skipped}",
            f"  Unmatched records:       {self.total_unmatched_records}",
            f"  Total issues:            {self.total_issues}",
            f"  Has errors:              {'YES' if self.has_errors else 'No'}",
            "",
        ]

        if self.global_issues:
            lines.append("GLOBAL ISSUES")
            lines.append("-" * 40)
            for issue in self.global_issues:
                lines.append(f"  [{issue.severity}] [{issue.category}] {issue.description}")
                if issue.details:
                    lines.append(f"    Details: {issue.details}")
            lines.append("")

        for summary in self.client_summaries:
            lines.append(f"CLIENT: {summary.client_name}")
            lines.append("-" * 40)
            lines.append(f"  Accounts:     {summary.accounts_mapped} mapped, {summary.accounts_unmapped} unmapped")
            lines.append(f"  Transactions: {summary.transactions_imported} imported, {summary.transactions_skipped} skipped")
            lines.append(f"  Invoices:     {summary.invoices_imported} imported, {summary.invoices_skipped} skipped")
            lines.append(f"  Unmatched:    {summary.unmatched_records} records")

            if summary.issues:
                lines.append(f"  Issues ({len(summary.issues)}):")
                for issue in summary.issues:
                    lines.append(f"    [{issue.severity}] [{issue.category}] {issue.description}")
                    if issue.details:
                        lines.append(f"      Details: {issue.details}")
            lines.append("")

        lines.append("=" * 72)
        lines.append("END OF REPORT")
        lines.append("=" * 72)
        return "\n".join(lines)


def generate_audit_report(
    client_datasets: dict[str, ClientDataset],
    coa_results: dict[str, MappingResult] | None = None,
    transaction_results: dict[str, TransactionImportResult] | None = None,
    invoice_results: dict[str, InvoiceImportResult] | None = None,
) -> MigrationAuditReport:
    """
    Generate a migration audit report from the results of all migration steps.

    Parameters
    ----------
    client_datasets : dict[str, ClientDataset]
        Output of ClientSplitter.split_by_client().
    coa_results : dict[str, MappingResult] | None
        CoA mapping results per client name.
    transaction_results : dict[str, TransactionImportResult] | None
        Transaction import results per client name.
    invoice_results : dict[str, InvoiceImportResult] | None
        Invoice import results per client name.

    Returns
    -------
    MigrationAuditReport
    """
    report = MigrationAuditReport()

    coa_results = coa_results or {}
    transaction_results = transaction_results or {}
    invoice_results = invoice_results or {}

    for client_name, dataset in client_datasets.items():
        if client_name == "__unmatched__":
            # Unmatched records go to global issues
            for rec in dataset.unmatched_records:
                report.global_issues.append(MigrationIssue(
                    category="UNMATCHED",
                    severity="WARNING",
                    description=f"Unmatched {rec.record_type}: {rec.reason}",
                ))
            report.total_unmatched_records += len(dataset.unmatched_records)
            continue

        summary = ClientMigrationSummary(client_name=client_name)

        # CoA mapping results
        coa = coa_results.get(client_name)
        if coa:
            summary.accounts_mapped = coa.total_mapped
            summary.accounts_unmapped = coa.total_unmapped
            report.total_accounts_mapped += coa.total_mapped
            report.total_accounts_unmapped += coa.total_unmapped

            for unmapped in coa.unmapped_accounts:
                summary.issues.append(MigrationIssue(
                    category="ACCOUNT_MAPPING",
                    severity="WARNING",
                    description=f"Unmapped account: {unmapped.original.name}",
                    details=unmapped.reason,
                ))

            for warning in coa.warnings:
                summary.issues.append(MigrationIssue(
                    category="ACCOUNT_MAPPING",
                    severity="INFO",
                    description=warning,
                ))

        # Transaction import results
        txn = transaction_results.get(client_name)
        if txn:
            summary.transactions_imported = txn.total_imported
            summary.transactions_skipped = txn.total_skipped
            report.total_transactions_imported += txn.total_imported
            report.total_transactions_skipped += txn.total_skipped

            for skipped in txn.skipped:
                summary.issues.append(MigrationIssue(
                    category="TRANSACTION",
                    severity="WARNING",
                    description=f"Skipped transaction: {skipped.reason}",
                    details=f"Date: {skipped.original.date}, "
                            f"Account: {skipped.original.account}, "
                            f"Amount: {skipped.original.amount}",
                ))

        # Invoice import results
        inv = invoice_results.get(client_name)
        if inv:
            summary.invoices_imported = inv.total_imported
            summary.invoices_skipped = inv.total_skipped
            report.total_invoices_imported += inv.total_imported
            report.total_invoices_skipped += inv.total_skipped

            for skipped in inv.skipped:
                summary.issues.append(MigrationIssue(
                    category="INVOICE",
                    severity="WARNING",
                    description=f"Skipped invoice: {skipped.reason}",
                    details=f"Invoice #{skipped.original.invoice_no}, "
                            f"Customer: {skipped.original.customer}",
                ))

        # Unmatched records from dataset
        summary.unmatched_records = len(dataset.unmatched_records)
        report.total_unmatched_records += len(dataset.unmatched_records)

        # Data quality checks
        if len(dataset.accounts) == 0:
            summary.issues.append(MigrationIssue(
                category="DATA_QUALITY",
                severity="ERROR",
                description="No chart of accounts data for this client",
            ))

        if len(dataset.transactions) == 0 and len(dataset.invoices) == 0:
            summary.issues.append(MigrationIssue(
                category="DATA_QUALITY",
                severity="WARNING",
                description="No transaction or invoice history for this client",
            ))

        report.client_summaries.append(summary)
        report.total_clients += 1

    return report
