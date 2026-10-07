from datetime import date

from app.models import Category, Direction
from app.services.categorise import categorise
from app.services.readiness import Profile, Txn, assess, compute_indicators

C, D = Direction.credit, Direction.debit


def month_of(year, month, sales=500_000_00, costs=350_000_00, loan=0):
    t = [Txn(date(year, month, 3), sales, C, Category.sales, "Buyer A"),
         Txn(date(year, month, 9), costs, D, Category.inventory)]  # fmt: skip
    if loan:
        t.append(Txn(date(year, month, 1), loan, D, Category.loan_repayment))
    return t


def year_of(**kw):
    out = []
    for i in range(12):
        y, m = (2025 + (9 + i) // 12, (9 + i) % 12 + 1)
        out += month_of(y, m, **kw)
    return out


def test_no_data_returns_upload_gap():
    r = assess([], Profile())
    assert r["score"]["total"] == 0
    assert r["gaps"][0]["code"] == "no_records"
    assert r["capacity"] is None


def test_indicators_basic_cashflow():
    ind = compute_indicators(year_of())
    assert ind["span_months"] == 12 and ind["months_with_data"] == 12
    assert ind["missing_months"] == []
    assert ind["total_inflow_kobo"] == 12 * 500_000_00
    assert abs(ind["operating_margin"] - 0.30) < 1e-9
    assert ind["positive_months_ratio"] == 1.0
    assert ind["inflow_volatility_cv"] == 0


def test_window_is_last_12_months_only():
    old = month_of(2023, 1, sales=99_999_999_00)
    ind = compute_indicators(old + year_of())
    assert ind["total_inflow_kobo"] == 12 * 500_000_00
    assert ind["period_start"] == "2025-10"


def test_missing_month_detected_and_penalised():
    txns = [t for t in year_of() if not (t.txn_date.year == 2026 and t.txn_date.month == 3)]
    r = assess(txns, Profile())
    assert r["indicators"]["missing_months"] == ["2026-03"]
    assert any(g["code"] == "missing_months" for g in r["gaps"])


def test_transfers_and_loan_disbursements_excluded_from_inflow():
    txns = year_of() + [Txn(date(2026, 5, 2), 2_000_000_00, C, Category.loan_in),
                        Txn(date(2026, 5, 3), 300_000_00, C, Category.transfer)]  # fmt: skip
    assert compute_indicators(txns)["total_inflow_kobo"] == 12 * 500_000_00


def test_strong_business_is_lender_ready():
    r = assess(year_of(), Profile(years_operating=6, has_cac_registration=True, has_tin=True,
                                  has_business_account=True))  # fmt: skip
    assert r["score"]["total"] >= 80
    assert r["score"]["band"] == "Lender-ready"
    assert sum(p["max"] for p in r["score"]["pillars"]) == 100


def test_heavy_debt_lowers_score_and_flags_gap():
    healthy = assess(year_of(), Profile())["score"]["total"]
    indebted = assess(year_of(loan=200_000_00), Profile())
    assert indebted["score"]["total"] < healthy
    assert any(g["code"] == "high_debt" for g in indebted["gaps"])


def test_short_history_flags_months_gap_and_scores_lower():
    r = assess(month_of(2026, 1) + month_of(2026, 2), Profile())
    assert r["gaps"][0]["code"] in {"months_short", "cac"}
    assert any(g["code"] == "months_short" for g in r["gaps"])
    assert r["score"]["total"] <= 35 and r["score"]["cap_reason"]


def test_capacity_is_35pct_of_free_cash():
    r = assess(year_of(), Profile())
    assert r["capacity"]["monthly_free_cash_kobo"] == 150_000_00
    assert r["capacity"]["indicative_repayment_kobo"] == 52_500_00


def test_score_is_deterministic():
    assert assess(year_of(), Profile()) == assess(year_of(), Profile())


def test_categorisation_rules():
    assert categorise("POS PURCHASE SETTLEMENT MONIEPOINT", C) == Category.sales
    assert categorise("NIP TRF FROM JOHN - PAYMENT FOR GOODS", C) == Category.sales
    assert categorise("LAPO MFB LOAN REPAYMENT", D) == Category.loan_repayment
    assert categorise("IKEDC PREPAID ELECTRICITY", D) == Category.utilities
    assert categorise("SMS ALERT CHARGES", D) == Category.bank_charges
    assert categorise("SHOP RENT - LANDLORD", D) == Category.rent
    assert categorise("LASG LEVY", D) == Category.tax
    assert categorise("XYZ 123", D) == Category.uncategorised
