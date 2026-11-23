"""Reference monthly payment math. The browser widget (static/mortgage.js) uses the same formula."""

from __future__ import annotations


def monthly_payment(
    price: float,
    down_pct: float,
    rate_pct: float,
    years: int,
    tax_rate_pct: float = 0.0,
    insurance_per_year: float = 0.0,
    hoa_monthly: float = 0.0,
) -> dict[str, float]:
    loan = price * (1 - down_pct / 100)
    n = years * 12
    r = rate_pct / 100 / 12
    principal_interest = loan / n if r == 0 else loan * r / (1 - (1 + r) ** -n)
    tax = price * tax_rate_pct / 100 / 12
    insurance = insurance_per_year / 12
    return {
        "loan": loan,
        "principal_interest": principal_interest,
        "tax": tax,
        "insurance": insurance,
        "hoa": hoa_monthly,
        "total": principal_interest + tax + insurance + hoa_monthly,
    }
