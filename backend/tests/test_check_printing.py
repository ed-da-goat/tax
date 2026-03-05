"""
Tests for check printing (amount_to_words, HTML rendering, schemas).
"""

from datetime import date
from decimal import Decimal

import pytest

from app.services.check_printing import (
    CheckData,
    CheckPrintingService,
    _build_check_html,
    _format_currency,
    _format_date,
    amount_to_words,
)


class TestAmountToWords:

    def test_zero(self):
        assert amount_to_words(Decimal("0.00")) == "Zero and 00/100"

    def test_one(self):
        assert amount_to_words(Decimal("1.00")) == "One and 00/100"

    def test_teens(self):
        assert amount_to_words(Decimal("11.00")) == "Eleven and 00/100"
        assert amount_to_words(Decimal("19.00")) == "Nineteen and 00/100"

    def test_tens(self):
        assert amount_to_words(Decimal("20.00")) == "Twenty and 00/100"
        assert amount_to_words(Decimal("50.00")) == "Fifty and 00/100"

    def test_tens_and_ones(self):
        assert amount_to_words(Decimal("42.00")) == "Forty-Two and 00/100"
        assert amount_to_words(Decimal("99.00")) == "Ninety-Nine and 00/100"

    def test_hundreds(self):
        assert amount_to_words(Decimal("100.00")) == "One Hundred and 00/100"
        assert amount_to_words(Decimal("500.00")) == "Five Hundred and 00/100"

    def test_hundreds_with_remainder(self):
        assert amount_to_words(Decimal("123.00")) == "One Hundred Twenty-Three and 00/100"
        assert amount_to_words(Decimal("210.00")) == "Two Hundred Ten and 00/100"

    def test_thousands(self):
        assert amount_to_words(Decimal("1000.00")) == "One Thousand and 00/100"
        assert amount_to_words(Decimal("5000.00")) == "Five Thousand and 00/100"

    def test_typical_check_amount(self):
        assert amount_to_words(Decimal("1234.56")) == "One Thousand Two Hundred Thirty-Four and 56/100"

    def test_large_amount(self):
        result = amount_to_words(Decimal("99999.99"))
        assert result == "Ninety-Nine Thousand Nine Hundred Ninety-Nine and 99/100"

    def test_cents_only(self):
        assert amount_to_words(Decimal("0.50")) == "Zero and 50/100"
        assert amount_to_words(Decimal("0.01")) == "Zero and 01/100"

    def test_million(self):
        result = amount_to_words(Decimal("1000000.00"))
        assert result == "One Million and 00/100"

    def test_common_bill_amount(self):
        result = amount_to_words(Decimal("2500.00"))
        assert result == "Two Thousand Five Hundred and 00/100"


class TestCheckFormatting:

    def test_format_currency(self):
        assert _format_currency(Decimal("1234.56")) == "$1,234.56"
        assert _format_currency(Decimal("0.00")) == "$0.00"

    def test_format_date(self):
        assert _format_date(date(2026, 3, 4)) == "03/04/2026"


class TestCheckHTML:

    def _sample_check(self) -> CheckData:
        return CheckData(
            payer_name="Test CPA Client",
            payer_address="123 Main St, Atlanta, GA 30301",
            payee_name="Acme Supplies LLC",
            check_number=1001,
            check_date=date(2026, 3, 4),
            amount=Decimal("2500.00"),
            memo="Bill #INV-001",
        )

    def test_html_contains_payer(self):
        html = _build_check_html(self._sample_check())
        assert "Test CPA Client" in html

    def test_html_contains_payee(self):
        html = _build_check_html(self._sample_check())
        assert "Acme Supplies LLC" in html

    def test_html_contains_check_number(self):
        html = _build_check_html(self._sample_check())
        assert "1001" in html

    def test_html_contains_amount(self):
        html = _build_check_html(self._sample_check())
        assert "$2,500.00" in html

    def test_html_contains_amount_in_words(self):
        html = _build_check_html(self._sample_check())
        assert "Two Thousand Five Hundred and 00/100" in html

    def test_html_contains_memo(self):
        html = _build_check_html(self._sample_check())
        assert "Bill #INV-001" in html

    def test_html_contains_date(self):
        html = _build_check_html(self._sample_check())
        assert "03/04/2026" in html

    def test_html_contains_stub(self):
        html = _build_check_html(self._sample_check())
        assert "CHECK STUB" in html

    def test_html_valid_structure(self):
        html = _build_check_html(self._sample_check())
        assert html.startswith("<!DOCTYPE html>")
        assert "</html>" in html

    def test_html_no_memo(self):
        check = CheckData(
            payer_name="Test",
            payer_address=None,
            payee_name="Vendor",
            check_number=1002,
            check_date=date(2026, 3, 4),
            amount=Decimal("100.00"),
        )
        html = _build_check_html(check)
        assert "Test" in html
        assert "Vendor" in html

    def test_html_no_payer_address(self):
        check = CheckData(
            payer_name="Test",
            payer_address=None,
            payee_name="Vendor",
            check_number=1003,
            check_date=date(2026, 3, 4),
            amount=Decimal("50.00"),
        )
        html = _build_check_html(check)
        assert "Test" in html


class TestCheckData:

    def test_frozen_dataclass(self):
        check = CheckData(
            payer_name="Test",
            payer_address=None,
            payee_name="Vendor",
            check_number=1001,
            check_date=date(2026, 3, 4),
            amount=Decimal("100.00"),
        )
        with pytest.raises(AttributeError):
            check.check_number = 9999
