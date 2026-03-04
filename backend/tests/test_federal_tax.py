"""
Tests for Federal Tax Calculator (module P4).

Tests federal income tax withholding, FICA (Social Security + Medicare),
and FUTA calculations.
"""

from decimal import Decimal

import pytest

from app.services.payroll.federal_tax import (
    ADDITIONAL_MEDICARE_THRESHOLD,
    FUTA_EFFECTIVE_RATE,
    FUTA_WAGE_BASE,
    MEDICARE_RATE,
    SS_RATE,
    FederalTaxCalculator,
    FederalWithholdingResult,
    FICAResult,
    FUTAResult,
)


# ---------------------------------------------------------------------------
# Federal income tax withholding
# ---------------------------------------------------------------------------


class TestFederalWithholding:

    def test_single_basic(self):
        """Single filer, basic withholding calculation."""
        result = FederalTaxCalculator.calculate_federal_withholding(
            gross_pay_per_period=Decimal("3000.00"),
            filing_status="SINGLE",
            pay_periods=26,
            tax_year=2024,
        )
        assert isinstance(result, FederalWithholdingResult)
        assert result.annual_gross == Decimal("78000.00")
        assert result.standard_deduction == Decimal("14600.00")
        assert result.taxable_income == Decimal("63400.00")
        assert result.per_period_tax > Decimal("0")

    def test_married_lower_tax(self):
        """Married filer pays less than single at same income."""
        single = FederalTaxCalculator.calculate_federal_withholding(
            gross_pay_per_period=Decimal("3000.00"),
            filing_status="SINGLE",
            pay_periods=26,
            tax_year=2024,
        )
        married = FederalTaxCalculator.calculate_federal_withholding(
            gross_pay_per_period=Decimal("3000.00"),
            filing_status="MARRIED",
            pay_periods=26,
            tax_year=2024,
        )
        assert married.per_period_tax < single.per_period_tax

    def test_head_of_household(self):
        result = FederalTaxCalculator.calculate_federal_withholding(
            gross_pay_per_period=Decimal("2500.00"),
            filing_status="HEAD_OF_HOUSEHOLD",
            pay_periods=26,
            tax_year=2024,
        )
        assert result.standard_deduction == Decimal("21900.00")
        assert result.per_period_tax > Decimal("0")

    def test_below_standard_deduction(self):
        """Income below standard deduction = zero tax."""
        result = FederalTaxCalculator.calculate_federal_withholding(
            gross_pay_per_period=Decimal("500.00"),
            filing_status="SINGLE",
            pay_periods=26,
            tax_year=2024,
        )
        # $500 * 26 = $13000, standard deduction $14600 => taxable = 0
        assert result.taxable_income == Decimal("0.00")
        assert result.per_period_tax == Decimal("0.00")

    def test_zero_pay(self):
        result = FederalTaxCalculator.calculate_federal_withholding(
            gross_pay_per_period=Decimal("0.00"),
            filing_status="SINGLE",
            pay_periods=26,
            tax_year=2024,
        )
        assert result.per_period_tax == Decimal("0.00")

    def test_different_tax_years(self):
        """Different tax years use different brackets."""
        r2024 = FederalTaxCalculator.calculate_federal_withholding(
            gross_pay_per_period=Decimal("5000.00"),
            filing_status="SINGLE",
            pay_periods=26,
            tax_year=2024,
        )
        r2025 = FederalTaxCalculator.calculate_federal_withholding(
            gross_pay_per_period=Decimal("5000.00"),
            filing_status="SINGLE",
            pay_periods=26,
            tax_year=2025,
        )
        # Different years have different brackets/deductions
        assert r2024.standard_deduction != r2025.standard_deduction

    def test_high_income_hits_higher_brackets(self):
        """High income should use higher tax brackets."""
        low = FederalTaxCalculator.calculate_federal_withholding(
            gross_pay_per_period=Decimal("1000.00"),
            filing_status="SINGLE",
            pay_periods=26,
            tax_year=2024,
        )
        high = FederalTaxCalculator.calculate_federal_withholding(
            gross_pay_per_period=Decimal("10000.00"),
            filing_status="SINGLE",
            pay_periods=26,
            tax_year=2024,
        )
        # Effective rate should be higher for high income
        if low.annual_gross > 0 and low.annual_tax > 0:
            low_effective = low.annual_tax / low.annual_gross
            high_effective = high.annual_tax / high.annual_gross
            assert high_effective > low_effective


# ---------------------------------------------------------------------------
# FICA (Social Security + Medicare)
# ---------------------------------------------------------------------------


class TestFICA:

    def test_basic_fica(self):
        """Basic FICA with no caps hit."""
        result = FederalTaxCalculator.calculate_fica(
            gross_pay=Decimal("3000.00"),
            ytd_wages=Decimal("0.00"),
            tax_year=2024,
        )
        assert isinstance(result, FICAResult)
        # SS: 3000 * 6.2% = 186
        assert result.ss_employee == Decimal("186.00")
        assert result.ss_employer == Decimal("186.00")
        # Medicare: 3000 * 1.45% = 43.50
        assert result.medicare_employee == Decimal("43.50")
        assert result.medicare_employer == Decimal("43.50")
        assert result.additional_medicare == Decimal("0.00")
        assert result.ss_capped is False

    def test_ss_wage_base_cap(self):
        """Social Security stops at wage base."""
        result = FederalTaxCalculator.calculate_fica(
            gross_pay=Decimal("5000.00"),
            ytd_wages=Decimal("165000.00"),  # Close to $168,600 cap
            tax_year=2024,
        )
        # Only $3600 taxable for SS (168600 - 165000)
        assert result.ss_taxable_wages == Decimal("3600.00")
        assert result.ss_capped is True
        # Medicare is still on full amount
        assert result.medicare_taxable_wages == Decimal("5000.00")

    def test_ss_already_capped(self):
        """No SS when already over wage base."""
        result = FederalTaxCalculator.calculate_fica(
            gross_pay=Decimal("5000.00"),
            ytd_wages=Decimal("170000.00"),
            tax_year=2024,
        )
        assert result.ss_taxable_wages == Decimal("0.00")
        assert result.ss_employee == Decimal("0.00")
        assert result.ss_capped is True
        # Medicare still applies
        assert result.medicare_employee > Decimal("0")

    def test_additional_medicare_tax(self):
        """Additional 0.9% Medicare on wages over $200k."""
        result = FederalTaxCalculator.calculate_fica(
            gross_pay=Decimal("10000.00"),
            ytd_wages=Decimal("195000.00"),
            tax_year=2024,
        )
        # YTD after: $205,000. Additional Medicare on $5000 over threshold
        assert result.additional_medicare == Decimal("45.00")  # 5000 * 0.9%

    def test_additional_medicare_already_over_threshold(self):
        """When already over $200k, full pay gets additional Medicare."""
        result = FederalTaxCalculator.calculate_fica(
            gross_pay=Decimal("10000.00"),
            ytd_wages=Decimal("250000.00"),
            tax_year=2024,
        )
        assert result.additional_medicare == Decimal("90.00")  # 10000 * 0.9%

    def test_additional_medicare_below_threshold(self):
        """No additional Medicare when below $200k."""
        result = FederalTaxCalculator.calculate_fica(
            gross_pay=Decimal("5000.00"),
            ytd_wages=Decimal("100000.00"),
            tax_year=2024,
        )
        assert result.additional_medicare == Decimal("0.00")

    def test_total_employee_fica(self):
        """Total employee FICA = SS + Medicare + Additional Medicare."""
        result = FederalTaxCalculator.calculate_fica(
            gross_pay=Decimal("2000.00"),
            ytd_wages=Decimal("0.00"),
            tax_year=2024,
        )
        expected = result.ss_employee + result.medicare_employee + result.additional_medicare
        assert result.total_employee == expected

    def test_zero_pay(self):
        result = FederalTaxCalculator.calculate_fica(
            gross_pay=Decimal("0.00"),
            ytd_wages=Decimal("50000.00"),
            tax_year=2024,
        )
        assert result.total_employee == Decimal("0.00")
        assert result.total_employer == Decimal("0.00")


# ---------------------------------------------------------------------------
# FUTA
# ---------------------------------------------------------------------------


class TestFUTA:

    def test_basic_futa(self):
        """Basic FUTA at effective 0.6% rate."""
        result = FederalTaxCalculator.calculate_futa(
            gross_pay=Decimal("2000.00"),
            ytd_wages=Decimal("0.00"),
        )
        assert isinstance(result, FUTAResult)
        assert result.taxable_wages == Decimal("2000.00")
        assert result.futa_amount == Decimal("12.00")  # 2000 * 0.006
        assert result.rate_used == FUTA_EFFECTIVE_RATE
        assert result.capped is False

    def test_futa_wage_base_cap(self):
        """FUTA stops at $7000 wage base."""
        result = FederalTaxCalculator.calculate_futa(
            gross_pay=Decimal("2000.00"),
            ytd_wages=Decimal("6000.00"),
        )
        # Only $1000 taxable (7000 - 6000)
        assert result.taxable_wages == Decimal("1000.00")
        assert result.futa_amount == Decimal("6.00")  # 1000 * 0.006
        assert result.capped is True

    def test_futa_already_capped(self):
        """No FUTA when already over $7000."""
        result = FederalTaxCalculator.calculate_futa(
            gross_pay=Decimal("2000.00"),
            ytd_wages=Decimal("8000.00"),
        )
        assert result.taxable_wages == Decimal("0.00")
        assert result.futa_amount == Decimal("0.00")
        assert result.capped is True

    def test_futa_zero_pay(self):
        result = FederalTaxCalculator.calculate_futa(
            gross_pay=Decimal("0.00"),
            ytd_wages=Decimal("3000.00"),
        )
        assert result.futa_amount == Decimal("0.00")

    def test_futa_first_pay_period(self):
        """First pay period of the year, full amount taxable."""
        result = FederalTaxCalculator.calculate_futa(
            gross_pay=Decimal("5000.00"),
            ytd_wages=Decimal("0.00"),
        )
        assert result.taxable_wages == Decimal("5000.00")
        assert result.futa_amount == Decimal("30.00")
