"""
Federal income tax withholding, FICA, and FUTA calculator (module P4).

Calculates:
- Federal income tax withholding (percentage method, 2024/2025/2026 brackets)
- Social Security tax (employee + employer shares)
- Medicare tax (employee + employer shares, including Additional Medicare Tax)
- FUTA (employer-only)

Compliance (CLAUDE.md rule #3):
    Every rate constant must cite its IRS source document.
"""

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP


# ---------------------------------------------------------------------------
# Federal income tax brackets (percentage method, annual)
# ---------------------------------------------------------------------------

# SOURCE: IRS Publication 15-T, Tax Year 2024, Table 1
# REVIEW DATE: 2026-03-04
FEDERAL_BRACKETS_2024_SINGLE: list[tuple[Decimal, Decimal, Decimal]] = [
    (Decimal("0.00"), Decimal("11600.00"), Decimal("0.10")),
    (Decimal("11600.00"), Decimal("47150.00"), Decimal("0.12")),
    (Decimal("47150.00"), Decimal("100525.00"), Decimal("0.22")),
    (Decimal("100525.00"), Decimal("191950.00"), Decimal("0.24")),
    (Decimal("191950.00"), Decimal("243725.00"), Decimal("0.32")),
    (Decimal("243725.00"), Decimal("609350.00"), Decimal("0.35")),
    (Decimal("609350.00"), Decimal("999999999.99"), Decimal("0.37")),
]

FEDERAL_BRACKETS_2024_MARRIED: list[tuple[Decimal, Decimal, Decimal]] = [
    (Decimal("0.00"), Decimal("23200.00"), Decimal("0.10")),
    (Decimal("23200.00"), Decimal("94300.00"), Decimal("0.12")),
    (Decimal("94300.00"), Decimal("201050.00"), Decimal("0.22")),
    (Decimal("201050.00"), Decimal("383900.00"), Decimal("0.24")),
    (Decimal("383900.00"), Decimal("487450.00"), Decimal("0.32")),
    (Decimal("487450.00"), Decimal("731200.00"), Decimal("0.35")),
    (Decimal("731200.00"), Decimal("999999999.99"), Decimal("0.37")),
]

# SOURCE: IRS Publication 15-T, Tax Year 2025 (projected, inflation-adjusted)
# REVIEW DATE: 2026-03-04
# COMPLIANCE REVIEW NEEDED: Verify 2025 brackets with final IRS Pub 15-T
FEDERAL_BRACKETS_2025_SINGLE: list[tuple[Decimal, Decimal, Decimal]] = [
    (Decimal("0.00"), Decimal("11925.00"), Decimal("0.10")),
    (Decimal("11925.00"), Decimal("48475.00"), Decimal("0.12")),
    (Decimal("48475.00"), Decimal("103350.00"), Decimal("0.22")),
    (Decimal("103350.00"), Decimal("197300.00"), Decimal("0.24")),
    (Decimal("197300.00"), Decimal("250525.00"), Decimal("0.32")),
    (Decimal("250525.00"), Decimal("626350.00"), Decimal("0.35")),
    (Decimal("626350.00"), Decimal("999999999.99"), Decimal("0.37")),
]

FEDERAL_BRACKETS_2025_MARRIED: list[tuple[Decimal, Decimal, Decimal]] = [
    (Decimal("0.00"), Decimal("23850.00"), Decimal("0.10")),
    (Decimal("23850.00"), Decimal("96950.00"), Decimal("0.12")),
    (Decimal("96950.00"), Decimal("206700.00"), Decimal("0.22")),
    (Decimal("206700.00"), Decimal("394600.00"), Decimal("0.24")),
    (Decimal("394600.00"), Decimal("501050.00"), Decimal("0.32")),
    (Decimal("501050.00"), Decimal("751600.00"), Decimal("0.35")),
    (Decimal("751600.00"), Decimal("999999999.99"), Decimal("0.37")),
]

# SOURCE: IRS Revenue Procedure 2025-XX (projected)
# REVIEW DATE: 2026-03-04
# COMPLIANCE REVIEW NEEDED: Verify 2026 brackets with IRS publication
FEDERAL_BRACKETS_2026_SINGLE = FEDERAL_BRACKETS_2025_SINGLE
FEDERAL_BRACKETS_2026_MARRIED = FEDERAL_BRACKETS_2025_MARRIED

FEDERAL_BRACKETS: dict[int, dict[str, list[tuple[Decimal, Decimal, Decimal]]]] = {
    2024: {
        "SINGLE": FEDERAL_BRACKETS_2024_SINGLE,
        "HEAD_OF_HOUSEHOLD": FEDERAL_BRACKETS_2024_SINGLE,
        "MARRIED": FEDERAL_BRACKETS_2024_MARRIED,
    },
    2025: {
        "SINGLE": FEDERAL_BRACKETS_2025_SINGLE,
        "HEAD_OF_HOUSEHOLD": FEDERAL_BRACKETS_2025_SINGLE,
        "MARRIED": FEDERAL_BRACKETS_2025_MARRIED,
    },
    2026: {
        "SINGLE": FEDERAL_BRACKETS_2026_SINGLE,
        "HEAD_OF_HOUSEHOLD": FEDERAL_BRACKETS_2026_SINGLE,
        "MARRIED": FEDERAL_BRACKETS_2026_MARRIED,
    },
}

# Standard deduction for federal (used in percentage method)
# SOURCE: IRS Revenue Procedure 2023-34, Tax Year 2024
# REVIEW DATE: 2026-03-04
FEDERAL_STANDARD_DEDUCTIONS: dict[int, dict[str, Decimal]] = {
    2024: {
        "SINGLE": Decimal("14600.00"),
        "MARRIED": Decimal("29200.00"),
        "HEAD_OF_HOUSEHOLD": Decimal("21900.00"),
    },
    # SOURCE: IRS Revenue Procedure 2024-40, Tax Year 2025
    # REVIEW DATE: 2026-03-04
    2025: {
        "SINGLE": Decimal("15000.00"),
        "MARRIED": Decimal("30000.00"),
        "HEAD_OF_HOUSEHOLD": Decimal("22500.00"),
    },
    # COMPLIANCE REVIEW NEEDED: Verify 2026 standard deductions
    2026: {
        "SINGLE": Decimal("15000.00"),
        "MARRIED": Decimal("30000.00"),
        "HEAD_OF_HOUSEHOLD": Decimal("22500.00"),
    },
}


# ---------------------------------------------------------------------------
# FICA constants
# ---------------------------------------------------------------------------

# SOURCE: IRS Publication 15 (Circular E), Tax Year 2024
# REVIEW DATE: 2026-03-04
SS_RATE = Decimal("0.062")  # 6.2% employee AND 6.2% employer

# SOURCE: SSA Press Release, October 2023, Tax Year 2024
# REVIEW DATE: 2026-03-04
SS_WAGE_BASE_2024 = Decimal("168600.00")

# SOURCE: SSA Press Release, October 2024, Tax Year 2025
# REVIEW DATE: 2026-03-04
SS_WAGE_BASE_2025 = Decimal("176100.00")

# SOURCE: SSA (projected), Tax Year 2026
# REVIEW DATE: 2026-03-04
# COMPLIANCE REVIEW NEEDED: Verify 2026 SS wage base with SSA
SS_WAGE_BASE_2026 = Decimal("176100.00")

SS_WAGE_BASES: dict[int, Decimal] = {
    2024: SS_WAGE_BASE_2024,
    2025: SS_WAGE_BASE_2025,
    2026: SS_WAGE_BASE_2026,
}

# SOURCE: IRS Publication 15, Tax Year 2024
# REVIEW DATE: 2026-03-04
MEDICARE_RATE = Decimal("0.0145")  # 1.45% employee AND 1.45% employer

# SOURCE: IRS Publication 15, Additional Medicare Tax (ACA)
# REVIEW DATE: 2026-03-04
# Additional 0.9% on wages over $200,000 (employee-only, no employer match)
ADDITIONAL_MEDICARE_RATE = Decimal("0.009")
ADDITIONAL_MEDICARE_THRESHOLD = Decimal("200000.00")


# ---------------------------------------------------------------------------
# FUTA constants
# ---------------------------------------------------------------------------

# SOURCE: IRS Publication 15, Tax Year 2024
# REVIEW DATE: 2026-03-04
# Gross FUTA rate is 6.0%, but with state credit the effective rate is 0.6%
FUTA_GROSS_RATE = Decimal("0.060")
FUTA_CREDIT_RATE = Decimal("0.054")  # Credit for state UI contributions
FUTA_EFFECTIVE_RATE = FUTA_GROSS_RATE - FUTA_CREDIT_RATE  # 0.6%

# SOURCE: IRS Publication 15, Tax Year 2024
# REVIEW DATE: 2026-03-04
FUTA_WAGE_BASE = Decimal("7000.00")


# ---------------------------------------------------------------------------
# Result dataclasses
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class FederalWithholdingResult:
    """Federal income tax withholding breakdown."""

    annual_gross: Decimal
    standard_deduction: Decimal
    taxable_income: Decimal
    annual_tax: Decimal
    per_period_tax: Decimal
    tax_year: int
    filing_status: str
    pay_periods: int


@dataclass(frozen=True)
class FICAResult:
    """FICA (Social Security + Medicare) calculation breakdown."""

    gross_pay: Decimal
    # Social Security
    ss_taxable_wages: Decimal
    ss_employee: Decimal
    ss_employer: Decimal
    ss_capped: bool
    # Medicare
    medicare_taxable_wages: Decimal
    medicare_employee: Decimal
    medicare_employer: Decimal
    additional_medicare: Decimal  # Employee-only additional 0.9%
    # Totals
    total_employee: Decimal
    total_employer: Decimal
    tax_year: int


@dataclass(frozen=True)
class FUTAResult:
    """FUTA calculation breakdown (employer-only)."""

    gross_pay: Decimal
    ytd_wages_before: Decimal
    taxable_wages: Decimal
    futa_amount: Decimal
    rate_used: Decimal
    wage_base: Decimal
    capped: bool


class FederalTaxCalculator:
    """
    Federal tax calculator covering income tax withholding, FICA, and FUTA.

    All methods are stateless class methods for easy testing.
    """

    # -------------------------------------------------------------------
    # Federal income tax withholding (percentage method)
    # -------------------------------------------------------------------

    @staticmethod
    def _apply_brackets(
        taxable_income: Decimal,
        brackets: list[tuple[Decimal, Decimal, Decimal]],
    ) -> Decimal:
        """Apply graduated tax brackets."""
        tax = Decimal("0.00")
        for bracket_min, bracket_max, rate in brackets:
            if taxable_income <= bracket_min:
                break
            taxable_in_bracket = min(taxable_income, bracket_max) - bracket_min
            tax += (taxable_in_bracket * rate).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP,
            )
        return tax

    @classmethod
    def calculate_federal_withholding(
        cls,
        gross_pay_per_period: Decimal,
        filing_status: str,
        pay_periods: int,
        tax_year: int,
    ) -> FederalWithholdingResult:
        """
        Calculate federal income tax withholding using the percentage method.

        Parameters
        ----------
        gross_pay_per_period : Decimal
            Gross pay for this pay period.
        filing_status : str
            SINGLE, MARRIED, or HEAD_OF_HOUSEHOLD.
        pay_periods : int
            Pay periods per year.
        tax_year : int
            Tax year for bracket lookup.
        """
        annual_gross = (gross_pay_per_period * pay_periods).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP,
        )

        # Standard deduction
        year_deductions = FEDERAL_STANDARD_DEDUCTIONS.get(tax_year)
        if year_deductions is None:
            year_deductions = FEDERAL_STANDARD_DEDUCTIONS[
                max(FEDERAL_STANDARD_DEDUCTIONS.keys())
            ]
        standard_deduction = year_deductions.get(
            filing_status, year_deductions["SINGLE"],
        )

        taxable_income = annual_gross - standard_deduction
        if taxable_income < Decimal("0"):
            taxable_income = Decimal("0.00")

        # Get brackets
        year_brackets = FEDERAL_BRACKETS.get(tax_year)
        if year_brackets is None:
            year_brackets = FEDERAL_BRACKETS[max(FEDERAL_BRACKETS.keys())]
        brackets = year_brackets.get(filing_status, year_brackets["SINGLE"])

        annual_tax = cls._apply_brackets(taxable_income, brackets)

        per_period_tax = Decimal("0.00")
        if pay_periods > 0:
            per_period_tax = (annual_tax / pay_periods).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP,
            )

        return FederalWithholdingResult(
            annual_gross=annual_gross,
            standard_deduction=standard_deduction,
            taxable_income=taxable_income,
            annual_tax=annual_tax,
            per_period_tax=per_period_tax,
            tax_year=tax_year,
            filing_status=filing_status,
            pay_periods=pay_periods,
        )

    # -------------------------------------------------------------------
    # FICA (Social Security + Medicare)
    # -------------------------------------------------------------------

    @classmethod
    def calculate_fica(
        cls,
        gross_pay: Decimal,
        ytd_wages: Decimal,
        tax_year: int,
    ) -> FICAResult:
        """
        Calculate FICA taxes (Social Security + Medicare) for one pay period.

        Parameters
        ----------
        gross_pay : Decimal
            Gross pay for this pay period.
        ytd_wages : Decimal
            Year-to-date wages BEFORE this pay period.
        tax_year : int
            Tax year for wage base lookup.
        """
        # Social Security wage base
        ss_base = SS_WAGE_BASES.get(tax_year)
        if ss_base is None:
            ss_base = SS_WAGE_BASES[max(SS_WAGE_BASES.keys())]

        ytd_after = ytd_wages + gross_pay

        # SS taxable wages (capped at wage base)
        if ytd_wages >= ss_base:
            ss_taxable = Decimal("0.00")
            ss_capped = True
        elif ytd_after > ss_base:
            ss_taxable = ss_base - ytd_wages
            ss_capped = True
        else:
            ss_taxable = gross_pay
            ss_capped = False

        ss_employee = (ss_taxable * SS_RATE).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP,
        )
        ss_employer = ss_employee  # Matched by employer

        # Medicare (no wage base cap)
        medicare_employee = (gross_pay * MEDICARE_RATE).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP,
        )
        medicare_employer = medicare_employee

        # Additional Medicare Tax (employee-only, on wages > $200k)
        additional_medicare = Decimal("0.00")
        if ytd_after > ADDITIONAL_MEDICARE_THRESHOLD:
            if ytd_wages >= ADDITIONAL_MEDICARE_THRESHOLD:
                additional_taxable = gross_pay
            else:
                additional_taxable = ytd_after - ADDITIONAL_MEDICARE_THRESHOLD
            additional_medicare = (additional_taxable * ADDITIONAL_MEDICARE_RATE).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP,
            )

        total_employee = ss_employee + medicare_employee + additional_medicare
        total_employer = ss_employer + medicare_employer

        return FICAResult(
            gross_pay=gross_pay,
            ss_taxable_wages=ss_taxable,
            ss_employee=ss_employee,
            ss_employer=ss_employer,
            ss_capped=ss_capped,
            medicare_taxable_wages=gross_pay,
            medicare_employee=medicare_employee,
            medicare_employer=medicare_employer,
            additional_medicare=additional_medicare,
            total_employee=total_employee,
            total_employer=total_employer,
            tax_year=tax_year,
        )

    # -------------------------------------------------------------------
    # FUTA (Federal Unemployment — employer only)
    # -------------------------------------------------------------------

    @classmethod
    def calculate_futa(
        cls,
        gross_pay: Decimal,
        ytd_wages: Decimal,
    ) -> FUTAResult:
        """
        Calculate FUTA for one pay period (employer-only).

        Parameters
        ----------
        gross_pay : Decimal
            Gross pay for this pay period.
        ytd_wages : Decimal
            Year-to-date wages BEFORE this pay period.
        """
        ytd_after = ytd_wages + gross_pay

        if ytd_wages >= FUTA_WAGE_BASE:
            taxable = Decimal("0.00")
            capped = True
        elif ytd_after > FUTA_WAGE_BASE:
            taxable = FUTA_WAGE_BASE - ytd_wages
            capped = True
        else:
            taxable = gross_pay
            capped = False

        futa_amount = (taxable * FUTA_EFFECTIVE_RATE).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP,
        )

        return FUTAResult(
            gross_pay=gross_pay,
            ytd_wages_before=ytd_wages,
            taxable_wages=taxable,
            futa_amount=futa_amount,
            rate_used=FUTA_EFFECTIVE_RATE,
            wage_base=FUTA_WAGE_BASE,
            capped=capped,
        )
