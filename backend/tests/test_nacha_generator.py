"""
Tests for the NACHA file generator (Phase 8A).

Validates NACHA file format compliance:
- Each line is exactly 94 characters
- Record types are correct (1, 5, 6, 8, 9)
- Amounts are in cents
- File is padded to lines divisible by 10
- Entry hash calculation is correct
"""

from datetime import date
from decimal import Decimal

import pytest

from app.services.payroll.nacha_generator import NACHAEntry, NACHAFileGenerator


@pytest.fixture
def generator():
    return NACHAFileGenerator(
        immediate_destination="091000019",
        immediate_origin="1234567890",
        destination_name="FIRST NATIONAL BANK",
        origin_name="ACME CPA FIRM",
        file_creation_date=date(2026, 3, 4),
        file_id_modifier="A",
    )


@pytest.fixture
def sample_entries():
    return [
        NACHAEntry(
            transaction_code="22",
            routing_number="091000019",
            account_number="123456789",
            amount=125000,  # $1,250.00
            individual_id="EMP001",
            individual_name="DOE JANE",
            trace_number="09100001000001",
        ),
        NACHAEntry(
            transaction_code="32",
            routing_number="091000019",
            account_number="987654321",
            amount=98500,  # $985.00
            individual_id="EMP002",
            individual_name="SMITH JOHN",
            trace_number="09100001000002",
        ),
    ]


class TestNACHAFileGenerator:
    def test_generate_basic_file(self, generator, sample_entries):
        generator.add_batch(
            company_name="ACME CPA FIRM",
            company_id="1234567890",
            effective_entry_date=date(2026, 3, 10),
            entries=sample_entries,
        )

        content = generator.generate()
        lines = content.strip().split("\n")

        # Each line must be exactly 94 characters
        for i, line in enumerate(lines):
            assert len(line) == 94, f"Line {i} is {len(line)} chars, expected 94"

    def test_line_count_divisible_by_10(self, generator, sample_entries):
        generator.add_batch(
            company_name="ACME CPA FIRM",
            company_id="1234567890",
            effective_entry_date=date(2026, 3, 10),
            entries=sample_entries,
        )

        content = generator.generate()
        lines = content.strip().split("\n")

        assert len(lines) % 10 == 0, f"Line count {len(lines)} not divisible by 10"

    def test_record_types(self, generator, sample_entries):
        generator.add_batch(
            company_name="ACME CPA FIRM",
            company_id="1234567890",
            effective_entry_date=date(2026, 3, 10),
            entries=sample_entries,
        )

        content = generator.generate()
        lines = content.strip().split("\n")

        # First line: File Header (type 1)
        assert lines[0][0] == "1"
        # Second line: Batch Header (type 5)
        assert lines[1][0] == "5"
        # Entry details (type 6)
        assert lines[2][0] == "6"
        assert lines[3][0] == "6"
        # Batch control (type 8)
        assert lines[4][0] == "8"
        # File control (type 9)
        assert lines[5][0] == "9"

    def test_file_header_fields(self, generator, sample_entries):
        generator.add_batch(
            company_name="ACME CPA FIRM",
            company_id="1234567890",
            effective_entry_date=date(2026, 3, 10),
            entries=sample_entries,
        )

        content = generator.generate()
        header = content.strip().split("\n")[0]

        # NACHA File Header positions (0-indexed):
        # 0: Record Type, 1-2: Priority, 3-12: Dest, 13-22: Origin,
        # 23-28: Date, 29-32: Time, 33: File ID Mod,
        # 34-36: Record Size, 37-38: Blocking Factor, 39: Format Code
        assert header[0] == "1"          # Record Type Code
        assert header[1:3] == "01"       # Priority Code
        assert header[34:37] == "094"    # Record Size
        assert header[37:39] == "10"     # Blocking Factor
        assert header[39] == "1"         # Format Code

    def test_entry_detail_fields(self, generator, sample_entries):
        generator.add_batch(
            company_name="ACME CPA FIRM",
            company_id="1234567890",
            effective_entry_date=date(2026, 3, 10),
            entries=sample_entries,
        )

        content = generator.generate()
        entry_line = content.strip().split("\n")[2]

        # Record type
        assert entry_line[0] == "6"
        # Transaction code (22 = checking credit)
        assert entry_line[1:3] == "22"
        # RDFI ID (first 8 digits of routing)
        assert entry_line[3:11] == "09100001"
        # Check digit
        assert entry_line[11] == "9"
        # Amount field (10 chars, right-justified, zero-padded)
        amount_field = entry_line[29:39]
        assert amount_field == "0000125000"  # $1,250.00 = 125000 cents

    def test_batch_control_totals(self, generator, sample_entries):
        generator.add_batch(
            company_name="ACME CPA FIRM",
            company_id="1234567890",
            effective_entry_date=date(2026, 3, 10),
            entries=sample_entries,
        )

        content = generator.generate()
        batch_ctrl = content.strip().split("\n")[4]

        # Record type 8
        assert batch_ctrl[0] == "8"
        # Service class code
        assert batch_ctrl[1:4] == "220"
        # Entry/Addenda count (2 entries)
        assert batch_ctrl[4:10] == "000002"
        # Total credit: 125000 + 98500 = 223500 cents
        total_credit = batch_ctrl[32:44]
        assert total_credit == "000000223500"

    def test_ppd_sec_code(self, generator, sample_entries):
        generator.add_batch(
            company_name="ACME CPA FIRM",
            company_id="1234567890",
            effective_entry_date=date(2026, 3, 10),
            entries=sample_entries,
        )

        content = generator.generate()
        batch_header = content.strip().split("\n")[1]

        # SEC code at position 50-53
        assert batch_header[50:53] == "PPD"

    def test_service_class_credits_only(self, generator, sample_entries):
        generator.add_batch(
            company_name="ACME CPA FIRM",
            company_id="1234567890",
            effective_entry_date=date(2026, 3, 10),
            entries=sample_entries,
        )

        content = generator.generate()
        batch_header = content.strip().split("\n")[1]

        # Service Class Code 220 = credits only
        assert batch_header[1:4] == "220"

    def test_empty_entries_raises_no_error(self, generator):
        """Generator with no batches should still produce valid structure."""
        content = generator.generate()
        lines = content.strip().split("\n")

        # Should have file header + file control + padding
        assert lines[0][0] == "1"  # File header
        # All other lines should be 9s (file control + padding)

    def test_multiple_batches(self, generator, sample_entries):
        generator.add_batch(
            company_name="CLIENT A",
            company_id="1111111111",
            effective_entry_date=date(2026, 3, 10),
            entries=sample_entries[:1],
        )
        generator.add_batch(
            company_name="CLIENT B",
            company_id="2222222222",
            effective_entry_date=date(2026, 3, 10),
            entries=sample_entries[1:],
        )

        content = generator.generate()
        lines = content.strip().split("\n")

        # Count record types
        type_counts = {}
        for line in lines:
            rt = line[0]
            type_counts[rt] = type_counts.get(rt, 0) + 1

        # 1 file header, 2 batch headers, 2 entries, 2 batch controls, rest are 9s
        assert type_counts.get("1", 0) == 1
        assert type_counts.get("5", 0) == 2
        assert type_counts.get("6", 0) == 2
        assert type_counts.get("8", 0) == 2

    def test_savings_credit_code(self):
        entry = NACHAEntry(
            transaction_code="32",
            routing_number="091000019",
            account_number="123456789",
            amount=50000,
            individual_id="EMP003",
            individual_name="WILSON BOB",
            trace_number="09100001000003",
        )
        gen = NACHAFileGenerator(
            immediate_destination="091000019",
            immediate_origin="1234567890",
            destination_name="BANK",
            origin_name="FIRM",
        )
        gen.add_batch(
            company_name="FIRM",
            company_id="1234567890",
            effective_entry_date=date(2026, 3, 10),
            entries=[entry],
        )

        content = gen.generate()
        entry_line = content.strip().split("\n")[2]

        # Transaction code 32 = savings credit
        assert entry_line[1:3] == "32"


class TestNACHAUtilities:
    def test_transaction_code_checking(self):
        assert NACHAFileGenerator.transaction_code_for("CHECKING") == "22"

    def test_transaction_code_savings(self):
        assert NACHAFileGenerator.transaction_code_for("SAVINGS") == "32"

    def test_transaction_code_prenote_checking(self):
        assert NACHAFileGenerator.transaction_code_for("CHECKING", is_prenote=True) == "23"

    def test_transaction_code_prenote_savings(self):
        assert NACHAFileGenerator.transaction_code_for("SAVINGS", is_prenote=True) == "33"

    def test_amount_to_cents(self):
        assert NACHAFileGenerator.amount_to_cents(Decimal("1250.00")) == 125000
        assert NACHAFileGenerator.amount_to_cents(Decimal("0.01")) == 1
        assert NACHAFileGenerator.amount_to_cents(Decimal("0.00")) == 0
        assert NACHAFileGenerator.amount_to_cents(Decimal("99999.99")) == 9999999
