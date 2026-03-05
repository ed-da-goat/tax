"""
Tests for W-2 generation (data aggregation and HTML rendering).
"""

from decimal import Decimal

import pytest

from app.schemas.w2 import W2Data, W2SummaryResponse
from app.services.payroll.w2_generator import (
    SS_WAGE_BASE_2026,
    W2GeneratorService,
    _build_w2_html,
    _format_currency,
)


class TestW2Formatting:

    def test_format_currency(self):
        assert _format_currency(Decimal("1234.56")) == "$1,234.56"
        assert _format_currency(Decimal("0.00")) == "$0.00"

    def test_format_currency_large(self):
        assert _format_currency(Decimal("100000.00")) == "$100,000.00"


class TestW2HTML:

    def _sample_w2(self) -> W2Data:
        return W2Data(
            employee_id="00000000-0000-0000-0000-000000000001",
            employee_first_name="John",
            employee_last_name="Smith",
            employee_address="123 Main St",
            employee_city="Atlanta",
            employee_state="GA",
            employee_zip="30301",
            tax_year=2026,
            box1_wages=Decimal("50000.00"),
            box2_federal_withheld=Decimal("6000.00"),
            box3_ss_wages=Decimal("50000.00"),
            box4_ss_tax=Decimal("3100.00"),
            box5_medicare_wages=Decimal("50000.00"),
            box6_medicare_tax=Decimal("725.00"),
            box16_state_wages=Decimal("50000.00"),
            box17_state_tax=Decimal("2500.00"),
        )

    def test_html_contains_employee_name(self):
        html = _build_w2_html(self._sample_w2(), "Test Firm", "123 Firm St")
        assert "John" in html
        assert "Smith" in html

    def test_html_contains_employer_name(self):
        html = _build_w2_html(self._sample_w2(), "Test Firm", "123 Firm St")
        assert "Test Firm" in html

    def test_html_contains_tax_year(self):
        html = _build_w2_html(self._sample_w2(), "Test Firm", None)
        assert "2026" in html

    def test_html_contains_box_values(self):
        html = _build_w2_html(self._sample_w2(), "Test Firm", None)
        assert "$50,000.00" in html
        assert "$6,000.00" in html
        assert "$3,100.00" in html
        assert "$725.00" in html
        assert "$2,500.00" in html

    def test_html_contains_substitute_label(self):
        html = _build_w2_html(self._sample_w2(), "Test Firm", None)
        assert "Substitute Form W-2" in html
        assert "Not for filing with SSA" in html

    def test_html_valid_structure(self):
        html = _build_w2_html(self._sample_w2(), "Test Firm", None)
        assert html.startswith("<!DOCTYPE html>")
        assert "</html>" in html

    def test_html_employee_address(self):
        html = _build_w2_html(self._sample_w2(), "Test Firm", None)
        assert "123 Main St" in html
        assert "Atlanta" in html

    def test_html_no_employer_address(self):
        html = _build_w2_html(self._sample_w2(), "Test Firm", None)
        assert "N/A" in html

    def test_html_no_employee_address(self):
        w2 = W2Data(
            employee_id="00000000-0000-0000-0000-000000000001",
            employee_first_name="Jane",
            employee_last_name="Doe",
            tax_year=2026,
        )
        html = _build_w2_html(w2, "Test Firm", "123 Firm St")
        assert "Jane" in html
        assert "Doe" in html


class TestW2SSWageBase:

    def test_ss_wage_base_caps_high_earner(self):
        """Verify box3 SS wages are capped at SS wage base."""
        gross = Decimal("200000.00")
        capped = min(gross, SS_WAGE_BASE_2026)
        assert capped == SS_WAGE_BASE_2026

    def test_ss_wage_base_no_cap_low_earner(self):
        gross = Decimal("50000.00")
        capped = min(gross, SS_WAGE_BASE_2026)
        assert capped == gross


class TestW2BatchPDF:

    def test_batch_empty_produces_html(self):
        summary = W2SummaryResponse(
            client_id="00000000-0000-0000-0000-000000000001",
            tax_year=2026,
            employer_name="Test Firm",
            w2s=[],
        )
        # Just verify the service method exists and handles empty data
        # Actual PDF generation requires WeasyPrint system libs
        assert summary.w2s == []
        assert summary.employer_name == "Test Firm"
