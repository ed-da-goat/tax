"""
Splitting report generator for QBO client splitting results.

Module M2 — Produces a summary report of client splitting results
including record counts per client, unmatched records, and warnings.
"""

from dataclasses import dataclass, field

from .client_splitter import ClientDataset


@dataclass
class RecordCounts:
    """Counts of each record type for a single client."""

    accounts: int = 0
    transactions: int = 0
    customers: int = 0
    invoices: int = 0
    vendors: int = 0
    employees: int = 0
    payroll_records: int = 0
    journal_entries: int = 0


@dataclass
class SplittingReport:
    """Summary report of a client-splitting operation."""

    clients_found: list[str] = field(default_factory=list)
    records_per_client: dict[str, RecordCounts] = field(default_factory=dict)
    unmatched_count: int = 0
    multi_client_transactions: int = 0
    warnings: list[str] = field(default_factory=list)


def generate_report(result: dict[str, ClientDataset]) -> SplittingReport:
    """
    Generate a splitting report from the output of ClientSplitter.split_by_client().

    Parameters
    ----------
    result : dict[str, ClientDataset]
        Output of ClientSplitter.split_by_client().

    Returns
    -------
    SplittingReport
        Summary of the splitting operation.
    """
    report = SplittingReport()

    for name, dataset in result.items():
        if name == "__unmatched__":
            report.unmatched_count = len(dataset.unmatched_records)
            continue

        report.clients_found.append(name)
        report.records_per_client[name] = RecordCounts(
            accounts=len(dataset.accounts),
            transactions=len(dataset.transactions),
            customers=len(dataset.customers),
            invoices=len(dataset.invoices),
            vendors=len(dataset.vendors),
            employees=len(dataset.employees),
            payroll_records=len(dataset.payroll_records),
            journal_entries=len(dataset.journal_entries),
        )

    # Count multi-client transactions: transactions where the split field
    # contains "-Split-" indicating they span multiple accounts/clients
    # (flagged for CPA review).
    seen_txn_refs: dict[str, set[str]] = {}  # txn identifier -> set of client names
    for name, dataset in result.items():
        if name == "__unmatched__":
            continue
        for txn in dataset.transactions:
            # Use date+num+amount as a transaction identifier
            txn_key = f"{txn.date}|{txn.num}|{txn.amount}"
            seen_txn_refs.setdefault(txn_key, set()).add(name)

    multi_client_count = sum(
        1 for clients in seen_txn_refs.values() if len(clients) > 1
    )
    report.multi_client_transactions = multi_client_count

    # Generate warnings
    if report.unmatched_count > 0:
        report.warnings.append(
            f"{report.unmatched_count} record(s) could not be assigned to any client. "
            "CPA review required."
        )

    if multi_client_count > 0:
        report.warnings.append(
            f"{multi_client_count} transaction(s) appear in multiple client datasets. "
            "CPA review required to confirm correct assignment."
        )

    for name, counts in report.records_per_client.items():
        if counts.transactions == 0:
            report.warnings.append(
                f"Client '{name}' has 0 transactions. Verify this is expected."
            )

    return report
