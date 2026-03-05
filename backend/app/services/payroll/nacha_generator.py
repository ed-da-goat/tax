"""
NACHA/ACH file generator for payroll direct deposit (Phase 8A).

Generates NACHA-formatted files per the NACHA Operating Rules specification.
Each line is exactly 94 characters, fixed-width ASCII.

File structure:
    Record Type 1 - File Header (one per file)
      Record Type 5 - Batch Header (one per batch)
        Record Type 6 - Entry Detail (one per employee)
      Record Type 8 - Batch Control (one per batch)
    Record Type 9 - File Control (one per file)
    Padding lines of 9s (to make total lines divisible by 10)

SEC code: PPD (Prearranged Payment and Deposit) for payroll.
Transaction code: 22 (checking credit), 32 (savings credit).
Service class code: 220 (credits only).

Reference: NACHA Operating Rules, ACH Developer Guide (achdevguide.nacha.org)
"""

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal


@dataclass(frozen=True)
class NACHAEntry:
    """A single ACH entry detail record (one employee's direct deposit)."""
    transaction_code: str  # '22' = checking credit, '32' = savings credit
    routing_number: str    # 9-digit ABA routing number
    account_number: str    # Up to 17 chars
    amount: int            # In cents (no decimals)
    individual_id: str     # Employee ID (up to 15 chars)
    individual_name: str   # Employee name (up to 22 chars)
    trace_number: str      # Unique trace (ODFI routing 8 digits + sequence)


class NACHAFileGenerator:
    """
    Generates a NACHA-formatted ACH file for payroll direct deposit.

    Usage:
        gen = NACHAFileGenerator(
            immediate_destination="091000019",
            immediate_origin="1234567890",
            destination_name="FIRST NATIONAL BANK",
            origin_name="ACME CORP",
            file_creation_date=date.today(),
            file_id_modifier="A",
        )
        gen.add_batch(
            company_name="ACME CORP",
            company_id="1234567890",
            effective_entry_date=date(2026, 3, 10),
            entries=[
                NACHAEntry(
                    transaction_code="22",
                    routing_number="091000019",
                    account_number="123456789",
                    amount=125000,  # $1,250.00
                    individual_id="EMP001",
                    individual_name="DOE JANE",
                    trace_number="09100001000001",
                ),
            ],
        )
        file_content = gen.generate()
    """

    RECORD_LENGTH = 94
    # Transaction codes for credits
    CHECKING_CREDIT = "22"
    SAVINGS_CREDIT = "32"
    # Prenote (zero-dollar test) codes
    CHECKING_PRENOTE = "23"
    SAVINGS_PRENOTE = "33"

    def __init__(
        self,
        immediate_destination: str,
        immediate_origin: str,
        destination_name: str,
        origin_name: str,
        file_creation_date: date | None = None,
        file_id_modifier: str = "A",
        reference_code: str = "",
    ):
        # Immediate Destination: space + 9-digit routing = 10 chars total
        self._immediate_destination = (" " + immediate_destination).ljust(10)[:10]
        self._immediate_origin = immediate_origin.ljust(10)[:10]
        self._destination_name = destination_name.ljust(23)[:23]
        self._origin_name = origin_name.ljust(23)[:23]
        self._file_creation_date = file_creation_date or date.today()
        self._file_id_modifier = file_id_modifier[0] if file_id_modifier else "A"
        self._reference_code = reference_code.ljust(8)[:8]
        self._batches: list[dict] = []

    def add_batch(
        self,
        company_name: str,
        company_id: str,
        effective_entry_date: date,
        entries: list[NACHAEntry],
        entry_description: str = "PAYROLL",
        company_discretionary_data: str = "",
    ) -> None:
        """Add a batch of ACH entries (typically one per client/payroll run)."""
        self._batches.append({
            "company_name": company_name,
            "company_id": company_id,
            "effective_entry_date": effective_entry_date,
            "entries": entries,
            "entry_description": entry_description,
            "company_discretionary_data": company_discretionary_data,
        })

    def generate(self) -> str:
        """Generate the complete NACHA file as a string."""
        lines: list[str] = []

        # Record Type 1: File Header
        lines.append(self._file_header())

        total_entry_count = 0
        total_debit = 0
        total_credit = 0
        total_entry_addenda_count = 0
        batch_count = 0

        for batch_num, batch in enumerate(self._batches, start=1):
            batch_count += 1
            entries = batch["entries"]

            # Record Type 5: Batch Header
            lines.append(self._batch_header(batch, batch_num))

            # Record Type 6: Entry Detail records
            batch_credit = 0
            batch_debit = 0
            batch_entry_hash = 0

            for seq, entry in enumerate(entries, start=1):
                lines.append(self._entry_detail(entry, seq))
                total_entry_count += 1
                total_entry_addenda_count += 1
                batch_credit += entry.amount
                # Entry hash: sum of first 8 digits of each RDFI routing number
                batch_entry_hash += int(entry.routing_number[:8])

            total_credit += batch_credit
            total_debit += batch_debit

            # Record Type 8: Batch Control
            lines.append(self._batch_control(
                batch_num=batch_num,
                entry_addenda_count=len(entries),
                entry_hash=batch_entry_hash,
                total_debit=batch_debit,
                total_credit=batch_credit,
                company_id=batch["company_id"],
            ))

        # Record Type 9: File Control
        total_entry_hash = sum(
            int(entry.routing_number[:8])
            for batch in self._batches
            for entry in batch["entries"]
        )
        lines.append(self._file_control(
            batch_count=batch_count,
            block_count=0,  # Calculated below
            entry_addenda_count=total_entry_addenda_count,
            entry_hash=total_entry_hash,
            total_debit=total_debit,
            total_credit=total_credit,
        ))

        # Pad to make line count divisible by 10 (blocking factor)
        while len(lines) % 10 != 0:
            lines.append("9" * self.RECORD_LENGTH)

        # Update block count in file control record
        block_count = len(lines) // 10
        file_control = self._file_control(
            batch_count=batch_count,
            block_count=block_count,
            entry_addenda_count=total_entry_addenda_count,
            entry_hash=total_entry_hash,
            total_debit=total_debit,
            total_credit=total_credit,
        )
        # Replace the file control line (it's right before the padding lines)
        for i in range(len(lines) - 1, -1, -1):
            if lines[i].startswith("9") and not all(c == "9" for c in lines[i]):
                lines[i] = file_control
                break

        return "\n".join(lines) + "\n"

    # -------------------------------------------------------------------
    # Record builders (private)
    # -------------------------------------------------------------------

    def _file_header(self) -> str:
        """Record Type 1: File Header Record."""
        now = datetime.now()
        return self._pad(
            "1"                                          # Record Type Code
            + "01"                                       # Priority Code
            + self._immediate_destination                # Immediate Destination (b + 9 digits, 10 chars)
            + self._immediate_origin                     # Immediate Origin (10 chars)
            + self._file_creation_date.strftime("%y%m%d")  # File Creation Date
            + now.strftime("%H%M")                       # File Creation Time
            + self._file_id_modifier                     # File ID Modifier
            + "094"                                      # Record Size
            + "10"                                       # Blocking Factor
            + "1"                                        # Format Code
            + self._destination_name                     # Immediate Destination Name
            + self._origin_name                          # Immediate Origin Name
            + self._reference_code                       # Reference Code
        )

    def _batch_header(self, batch: dict, batch_num: int) -> str:
        """Record Type 5: Batch Header Record."""
        return self._pad(
            "5"                                          # Record Type Code
            + "220"                                      # Service Class Code (credits only)
            + batch["company_name"].ljust(16)[:16]       # Company Name
            + batch["company_discretionary_data"].ljust(20)[:20]  # Company Discretionary Data
            + batch["company_id"].ljust(10)[:10]         # Company Identification
            + "PPD"                                      # Standard Entry Class Code
            + batch["entry_description"].ljust(10)[:10]  # Company Entry Description
            + self._file_creation_date.strftime("%y%m%d")  # Company Descriptive Date
            + batch["effective_entry_date"].strftime("%y%m%d")  # Effective Entry Date
            + "   "                                      # Settlement Date (reserved)
            + "1"                                        # Originator Status Code
            + self._immediate_destination.strip()[:8].ljust(8)  # Originating DFI ID
            + str(batch_num).rjust(7, "0")               # Batch Number
        )

    def _entry_detail(self, entry: NACHAEntry, sequence: int) -> str:
        """Record Type 6: Entry Detail Record."""
        rdfi_id = entry.routing_number[:8]
        check_digit = entry.routing_number[8]

        return self._pad(
            "6"                                          # Record Type Code
            + entry.transaction_code                     # Transaction Code
            + rdfi_id                                    # Receiving DFI Identification
            + check_digit                                # Check Digit
            + entry.account_number.ljust(17)[:17]        # DFI Account Number
            + str(entry.amount).rjust(10, "0")           # Amount (in cents)
            + entry.individual_id.ljust(15)[:15]         # Individual Identification Number
            + entry.individual_name.ljust(22)[:22]       # Individual Name
            + "  "                                       # Discretionary Data
            + "0"                                        # Addenda Record Indicator
            + entry.trace_number.ljust(15)[:15]          # Trace Number
        )

    def _batch_control(
        self,
        batch_num: int,
        entry_addenda_count: int,
        entry_hash: int,
        total_debit: int,
        total_credit: int,
        company_id: str,
    ) -> str:
        """Record Type 8: Batch Control Record."""
        # Entry hash: last 10 digits only
        hash_str = str(entry_hash)[-10:].rjust(10, "0")

        return self._pad(
            "8"                                          # Record Type Code
            + "220"                                      # Service Class Code
            + str(entry_addenda_count).rjust(6, "0")     # Entry/Addenda Count
            + hash_str                                   # Entry Hash
            + str(total_debit).rjust(12, "0")            # Total Debit Entry Dollar Amount
            + str(total_credit).rjust(12, "0")           # Total Credit Entry Dollar Amount
            + company_id.ljust(10)[:10]                  # Company Identification
            + " " * 19                                   # Message Authentication Code
            + " " * 6                                    # Reserved
            + self._immediate_destination.strip()[:8].ljust(8)  # Originating DFI ID
            + str(batch_num).rjust(7, "0")               # Batch Number
        )

    def _file_control(
        self,
        batch_count: int,
        block_count: int,
        entry_addenda_count: int,
        entry_hash: int,
        total_debit: int,
        total_credit: int,
    ) -> str:
        """Record Type 9: File Control Record."""
        hash_str = str(entry_hash)[-10:].rjust(10, "0")

        return self._pad(
            "9"                                          # Record Type Code
            + str(batch_count).rjust(6, "0")             # Batch Count
            + str(block_count).rjust(6, "0")             # Block Count
            + str(entry_addenda_count).rjust(8, "0")     # Entry/Addenda Count
            + hash_str                                   # Entry Hash
            + str(total_debit).rjust(12, "0")            # Total Debit Entry Dollar Amount
            + str(total_credit).rjust(12, "0")           # Total Credit Entry Dollar Amount
            + " " * 39                                   # Reserved
        )

    def _pad(self, record: str) -> str:
        """Pad or truncate a record to exactly 94 characters."""
        if len(record) > self.RECORD_LENGTH:
            return record[:self.RECORD_LENGTH]
        return record.ljust(self.RECORD_LENGTH)

    # -------------------------------------------------------------------
    # Utility class methods
    # -------------------------------------------------------------------

    @staticmethod
    def transaction_code_for(account_type: str, is_prenote: bool = False) -> str:
        """Return the NACHA transaction code for a given account type."""
        if is_prenote:
            return (
                NACHAFileGenerator.CHECKING_PRENOTE
                if account_type == "CHECKING"
                else NACHAFileGenerator.SAVINGS_PRENOTE
            )
        return (
            NACHAFileGenerator.CHECKING_CREDIT
            if account_type == "CHECKING"
            else NACHAFileGenerator.SAVINGS_CREDIT
        )

    @staticmethod
    def amount_to_cents(amount: Decimal) -> int:
        """Convert a Decimal dollar amount to integer cents for NACHA."""
        return int((amount * 100).to_integral_value())
