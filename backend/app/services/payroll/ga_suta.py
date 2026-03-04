"""
Georgia State Unemployment Tax (SUTA) calculator (module P3).

Calculates employer-side Georgia SUTA contributions based on
year-to-date wages and the wage base limit.

Compliance (CLAUDE.md rule #3):
    Every rate constant must cite its Georgia DOR source document.

Compliance (CLAUDE.md rule #4):
    Supports per-client custom SUTA rates for experienced employers.
"""

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP


# ---------------------------------------------------------------------------
# Constants — cited per CLAUDE.md rule #3
# ---------------------------------------------------------------------------

# SOURCE: Georgia DOL, Employer's Guide to Unemployment Insurance Tax, 2024
# REVIEW DATE: 2026-03-04
# New employer rate in Georgia is 2.7% (O.C.G.A. § 34-8-155)
GA_SUTA_NEW_EMPLOYER_RATE = Decimal("0.027")

# SOURCE: Georgia DOL, Employer's Guide to Unemployment Insurance Tax, 2024
# REVIEW DATE: 2026-03-04
# Taxable wage base for Georgia SUTA: first $9,500 of wages per employee per year
GA_SUTA_WAGE_BASE_2024 = Decimal("9500.00")

# SOURCE: Georgia DOL, Employer's Guide to Unemployment Insurance Tax, 2025
# REVIEW DATE: 2026-03-04
# COMPLIANCE REVIEW NEEDED: Verify 2025 wage base with GA DOL
GA_SUTA_WAGE_BASE_2025 = Decimal("9500.00")

# SOURCE: Georgia DOL, Employer's Guide to Unemployment Insurance Tax, 2026
# REVIEW DATE: 2026-03-04
# COMPLIANCE REVIEW NEEDED: Verify 2026 wage base with GA DOL
GA_SUTA_WAGE_BASE_2026 = Decimal("9500.00")

WAGE_BASES: dict[int, Decimal] = {
    2024: GA_SUTA_WAGE_BASE_2024,
    2025: GA_SUTA_WAGE_BASE_2025,
    2026: GA_SUTA_WAGE_BASE_2026,
}


@dataclass(frozen=True)
class SUTAResult:
    """Result of a Georgia SUTA calculation for one pay period."""

    gross_pay: Decimal
    ytd_wages_before: Decimal
    ytd_wages_after: Decimal
    taxable_wages: Decimal
    suta_amount: Decimal
    rate_used: Decimal
    wage_base: Decimal
    tax_year: int
    capped: bool  # True if employee has hit the wage base cap


class GeorgiaSUTACalculator:
    """
    Calculates Georgia SUTA (employer-paid) for a single pay period.

    Supports:
    - Default new employer rate (2.7%)
    - Per-client custom experienced employer rate
    - Wage base cap tracking via year-to-date wages

    The employer pays SUTA on the first $9,500 of each employee's
    annual wages. Once the cap is reached, no further SUTA is due.
    """

    @staticmethod
    def _get_wage_base(tax_year: int) -> Decimal:
        """Get the SUTA wage base for a given year."""
        if tax_year in WAGE_BASES:
            return WAGE_BASES[tax_year]
        return WAGE_BASES[max(WAGE_BASES.keys())]

    @classmethod
    def calculate(
        cls,
        gross_pay: Decimal,
        ytd_wages: Decimal,
        tax_year: int,
        custom_rate: Decimal | None = None,
    ) -> SUTAResult:
        """
        Calculate Georgia SUTA for one pay period.

        Parameters
        ----------
        gross_pay : Decimal
            Gross pay for this pay period.
        ytd_wages : Decimal
            Year-to-date wages for this employee BEFORE this pay period.
        tax_year : int
            Tax year for wage base lookup.
        custom_rate : Decimal or None
            Per-client experienced employer rate. If None, uses the
            default new employer rate of 2.7%.

        Returns
        -------
        SUTAResult
            Detailed breakdown of the SUTA calculation.
        """
        rate = custom_rate if custom_rate is not None else GA_SUTA_NEW_EMPLOYER_RATE
        wage_base = cls._get_wage_base(tax_year)

        ytd_after = ytd_wages + gross_pay

        # Determine taxable wages for this period
        if ytd_wages >= wage_base:
            # Already capped — no SUTA due
            taxable_wages = Decimal("0.00")
            capped = True
        elif ytd_after > wage_base:
            # Partially capped — only pay on wages up to the base
            taxable_wages = wage_base - ytd_wages
            capped = True
        else:
            # Full gross is taxable
            taxable_wages = gross_pay
            capped = False

        suta_amount = (taxable_wages * rate).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP,
        )

        return SUTAResult(
            gross_pay=gross_pay,
            ytd_wages_before=ytd_wages,
            ytd_wages_after=ytd_after,
            taxable_wages=taxable_wages,
            suta_amount=suta_amount,
            rate_used=rate,
            wage_base=wage_base,
            tax_year=tax_year,
            capped=capped,
        )
