"""
Tests for 1099-NEC generation (data schemas and HTML rendering).
"""

from decimal import Decimal

import pytest

from app.schemas.form_1099 import Form1099NECData, Form1099NECSummaryResponse
from app.services.tax_exports_1099 import (
    FILING_THRESHOLD,
    _build_1099_html,
    _format_currency,
)


class TestFilingThreshold:

    def test_threshold_is_600(self):
        assert FILING_THRESHOLD == Decimal("600.00")


class Test1099Formatting:

    def test_format_currency(self):
        assert _format_currency(Decimal("1500.00")) == "$1,500.00"
        assert _format_currency(Decimal("600.00")) == "$600.00"


class Test1099HTML:

    def _sample_1099(self) -> Form1099NECData:
        return Form1099NECData(
            vendor_id="00000000-0000-0000-0000-000000000001",
            vendor_name="Acme Consulting",
            vendor_address="456 Oak Ave",
            vendor_city="Savannah",
            vendor_state="GA",
            vendor_zip="31401",
            tax_year=2026,
            box1_nonemployee_compensation=Decimal("15000.00"),
        )

    def test_html_contains_vendor_name(self):
        html = _build_1099_html(self._sample_1099(), "Test Client", "100 Main St")
        assert "Acme Consulting" in html

    def test_html_contains_payer_name(self):
        html = _build_1099_html(self._sample_1099(), "Test Client", "100 Main St")
        assert "Test Client" in html

    def test_html_contains_tax_year(self):
        html = _build_1099_html(self._sample_1099(), "Test Client", None)
        assert "2026" in html

    def test_html_contains_compensation_amount(self):
        html = _build_1099_html(self._sample_1099(), "Test Client", None)
        assert "$15,000.00" in html

    def test_html_contains_substitute_label(self):
        html = _build_1099_html(self._sample_1099(), "Test Client", None)
        assert "Substitute Form 1099-NEC" in html
        assert "For recipient information only" in html

    def test_html_valid_structure(self):
        html = _build_1099_html(self._sample_1099(), "Test Client", None)
        assert html.startswith("<!DOCTYPE html>")
        assert "</html>" in html

    def test_html_vendor_address(self):
        html = _build_1099_html(self._sample_1099(), "Test Client", None)
        assert "456 Oak Ave" in html
        assert "Savannah" in html

    def test_html_no_vendor_address(self):
        form = Form1099NECData(
            vendor_id="00000000-0000-0000-0000-000000000001",
            vendor_name="No Address Vendor",
            tax_year=2026,
            box1_nonemployee_compensation=Decimal("1000.00"),
        )
        html = _build_1099_html(form, "Test Client", None)
        assert "No Address Vendor" in html
        assert "N/A" in html


class Test1099Summary:

    def test_summary_with_multiple_vendors(self):
        summary = Form1099NECSummaryResponse(
            client_id="00000000-0000-0000-0000-000000000001",
            tax_year=2026,
            payer_name="Test Client",
            forms=[
                Form1099NECData(
                    vendor_id="00000000-0000-0000-0000-000000000002",
                    vendor_name="Vendor A",
                    tax_year=2026,
                    box1_nonemployee_compensation=Decimal("5000.00"),
                ),
                Form1099NECData(
                    vendor_id="00000000-0000-0000-0000-000000000003",
                    vendor_name="Vendor B",
                    tax_year=2026,
                    box1_nonemployee_compensation=Decimal("10000.00"),
                ),
            ],
            total_nonemployee_compensation=Decimal("15000.00"),
        )
        assert len(summary.forms) == 2
        assert summary.total_nonemployee_compensation == Decimal("15000.00")

    def test_empty_summary(self):
        summary = Form1099NECSummaryResponse(
            client_id="00000000-0000-0000-0000-000000000001",
            tax_year=2026,
            payer_name="Test Client",
        )
        assert summary.forms == []
        assert summary.total_nonemployee_compensation == Decimal("0.00")
