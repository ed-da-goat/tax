"""
Tests for Direct Deposit Pydantic schemas (Phase 8A).

Validates routing number checksum, account number format, and schema constraints.
"""

import pytest
from pydantic import ValidationError

from app.schemas.direct_deposit import (
    EmployeeBankAccountCreate,
    NACHAGenerateRequest,
)
from datetime import date


class TestEmployeeBankAccountCreate:
    def test_valid_account(self):
        """Valid bank account should pass validation."""
        acct = EmployeeBankAccountCreate(
            account_holder_name="Jane Doe",
            account_number="123456789",
            routing_number="021000021",  # JPMorgan Chase
            account_type="CHECKING",
            authorization_on_file=True,
        )
        assert acct.routing_number == "021000021"
        assert acct.account_number == "123456789"

    def test_invalid_routing_number_checksum(self):
        """Routing number with bad checksum should fail."""
        with pytest.raises(ValidationError, match="checksum"):
            EmployeeBankAccountCreate(
                account_holder_name="Jane Doe",
                account_number="123456789",
                routing_number="123456789",  # Invalid checksum
                authorization_on_file=True,
            )

    def test_routing_number_non_digits(self):
        with pytest.raises(ValidationError, match="9 digits"):
            EmployeeBankAccountCreate(
                account_holder_name="Jane Doe",
                account_number="123456789",
                routing_number="02100002A",
                authorization_on_file=True,
            )

    def test_routing_number_wrong_length(self):
        with pytest.raises(ValidationError):
            EmployeeBankAccountCreate(
                account_holder_name="Jane Doe",
                account_number="123456789",
                routing_number="0210000",
                authorization_on_file=True,
            )

    def test_account_number_non_digits(self):
        with pytest.raises(ValidationError, match="digits"):
            EmployeeBankAccountCreate(
                account_holder_name="Jane Doe",
                account_number="12345ABC9",
                routing_number="021000021",
                authorization_on_file=True,
            )

    def test_account_number_too_short(self):
        with pytest.raises(ValidationError):
            EmployeeBankAccountCreate(
                account_holder_name="Jane Doe",
                account_number="123",  # min_length=4
                routing_number="021000021",
                authorization_on_file=True,
            )

    def test_default_account_type(self):
        acct = EmployeeBankAccountCreate(
            account_holder_name="Jane Doe",
            account_number="123456789",
            routing_number="021000021",
            authorization_on_file=True,
        )
        assert acct.account_type.value == "CHECKING"

    def test_savings_account_type(self):
        acct = EmployeeBankAccountCreate(
            account_holder_name="Jane Doe",
            account_number="123456789",
            routing_number="021000021",
            account_type="SAVINGS",
            authorization_on_file=True,
        )
        assert acct.account_type.value == "SAVINGS"

    def test_well_known_routing_numbers(self):
        """Test against real routing numbers with known-good checksums."""
        valid_routings = [
            "021000021",  # JPMorgan Chase
            "011401533",  # Bank of America
            "021200339",  # Citibank
            "071000013",  # BMO Harris
        ]
        for routing in valid_routings:
            acct = EmployeeBankAccountCreate(
                account_holder_name="Test",
                account_number="1234567890",
                routing_number=routing,
                authorization_on_file=True,
            )
            assert acct.routing_number == routing


class TestNACHAGenerateRequest:
    def test_valid_config(self):
        config = NACHAGenerateRequest(
            company_name="ACME CPA FIRM",
            company_id="1234567890",
            odfi_routing_number="021000021",
            odfi_name="JPMORGAN CHASE",
            effective_entry_date=date(2026, 3, 10),
        )
        assert config.file_id_modifier == "A"

    def test_company_name_max_length(self):
        config = NACHAGenerateRequest(
            company_name="A" * 16,
            company_id="1234567890",
            odfi_routing_number="021000021",
            odfi_name="BANK",
            effective_entry_date=date(2026, 3, 10),
        )
        assert len(config.company_name) == 16

    def test_company_name_too_long(self):
        with pytest.raises(ValidationError):
            NACHAGenerateRequest(
                company_name="A" * 17,
                company_id="1234567890",
                odfi_routing_number="021000021",
                odfi_name="BANK",
                effective_entry_date=date(2026, 3, 10),
            )
