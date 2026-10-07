"""Credit-readiness engine.

Pure functions: transactions + business profile in, indicators / score /
gaps out. No I/O, so it is fully unit-testable and its output is
reproducible — the same records always produce the same score.

The score is NOT a credit decision. It measures how complete, consistent
and lender-legible a business's records are, across four pillars that
mirror what Nigerian MFI and bank SME credit officers check (the "Cs" of
credit: capacity, character/records, conditions, capital/obligations).
Every point awarded is explained, so the owner can see exactly what to fix.
"""

from __future__ import annotations

import statistics
from collections import defaultdict
from dataclasses import dataclass
from datetime import date

from app.models import Category, Direction
from app.services.categorise import EXCLUDED_FROM_CASHFLOW

WINDOW_MONTHS = 12


@dataclass(frozen=True)
class Txn:
    txn_date: date
    amount_kobo: int
    direction: Direction
    category: Category
    counterparty: str | None = None


@dataclass(frozen=True)
class Profile:
    years_operating: int = 0
    has_cac_registration: bool = False
    has_tin: bool = False
    has_business_account: bool = False
    keeps_written_records: bool = False


def _month_key(d: date) -> tuple[int, int]:
    return (d.year, d.month)


def _months_between(a: tuple[int, int], b: tuple[int, int]) -> list[tuple[int, int]]:
    out, (y, m) = [], a
    while (y, m) <= b:
        out.append((y, m))
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)
    return out


def _scale(x: float, lo: float, hi: float) -> float:
    """Linear 0..1 between lo and hi (works for hi < lo, i.e. lower is better)."""
    if hi == lo:
        return 1.0
    t = (x - lo) / (hi - lo)
    return max(0.0, min(1.0, t))


def _component(label: str, earned: float, max_points: float, detail: str, code: str) -> dict:
    return {
        "code": code,
        "label": label,
        "points": round(earned * max_points, 1),
        "max": max_points,
        "detail": detail,
    }


def _naira(kobo: float) -> str:
    return f"₦{kobo / 100:,.0f}"


def compute_indicators(txns: list[Txn]) -> dict:
    if not txns:
        return {"has_data": False}

    last = max(_month_key(t.txn_date) for t in txns)
    ly, lm = last
    start_m = lm - (WINDOW_MONTHS - 1)
    start = (ly + (start_m - 1) // 12, (start_m - 1) % 12 + 1)
    window = [t for t in txns if _month_key(t.txn_date) >= start]
    first = min(_month_key(t.txn_date) for t in window)
    months = _months_between(first, last)

    inflow = defaultdict(int)
    outflow = defaultdict(int)
    op_outflow = defaultdict(int)
    debt = defaultdict(int)
    counts = defaultdict(int)
    cp_sales: dict[str, int] = defaultdict(int)
    sales_with_cp = 0
    uncategorised = 0

    for t in window:
        mk = _month_key(t.txn_date)
        counts[mk] += 1
        if t.category == Category.uncategorised:
            uncategorised += 1
        if t.category in EXCLUDED_FROM_CASHFLOW:
            continue
        if t.direction == Direction.credit:
            inflow[mk] += t.amount_kobo
            if t.counterparty:
                cp_sales[t.counterparty.strip().lower()] += t.amount_kobo
                sales_with_cp += t.amount_kobo
        else:
            outflow[mk] += t.amount_kobo
            if t.category == Category.loan_repayment:
                debt[mk] += t.amount_kobo
            else:
                op_outflow[mk] += t.amount_kobo

    span = len(months)
    monthly_in = [inflow[m] for m in months]
    monthly_out = [outflow[m] for m in months]
    total_in, total_out = sum(monthly_in), sum(monthly_out)
    total_op_out, total_debt = sum(op_outflow.values()), sum(debt.values())
    months_with_data = sum(1 for m in months if counts[m] > 0)
    missing = [f"{y}-{m:02d}" for (y, m) in months if counts[(y, m)] == 0]

    mean_in = statistics.fmean(monthly_in) if span else 0
    cv = (statistics.pstdev(monthly_in) / mean_in) if span > 1 and mean_in > 0 else None
    growth = None
    if span >= 6:
        early, late = statistics.fmean(monthly_in[:3]), statistics.fmean(monthly_in[-3:])
        growth = (late - early) / early if early > 0 else None

    top_share = None
    if total_in > 0 and sales_with_cp / total_in >= 0.5 and cp_sales:
        top_share = max(cp_sales.values()) / sales_with_cp

    return {
        "has_data": True,
        "period_start": f"{first[0]}-{first[1]:02d}",
        "period_end": f"{last[0]}-{last[1]:02d}",
        "span_months": span,
        "months_with_data": months_with_data,
        "missing_months": missing,
        "continuity": months_with_data / span if span else 0,
        "transaction_count": len(window),
        "uncategorised_count": uncategorised,
        "categorised_share": 1 - uncategorised / len(window),
        "total_inflow_kobo": total_in,
        "total_outflow_kobo": total_out,
        "avg_monthly_inflow_kobo": round(mean_in),
        "avg_monthly_net_kobo": round((total_in - total_out) / span) if span else 0,
        "operating_margin": (total_in - total_op_out) / total_in if total_in else None,
        "positive_months_ratio": sum(1 for i, o in zip(monthly_in, monthly_out, strict=True) if i > o) / span,
        "inflow_volatility_cv": cv,
        "inflow_growth": growth,
        "debt_service_ratio": total_debt / total_in if total_in else None,
        "top_customer_share": top_share,
        "distinct_customers": len(cp_sales),
        "monthly": [
            {"month": f"{y}-{m:02d}", "inflow_kobo": inflow[(y, m)], "outflow_kobo": outflow[(y, m)]} for (y, m) in months
        ],
    }


def score(ind: dict, profile: Profile) -> dict:
    if not ind.get("has_data"):
        return {"total": 0, "band": "No data", "pillars": []}

    # Pillar 1 — Record quality (25)
    formal = sum([profile.has_cac_registration, profile.has_tin, profile.has_business_account])
    p1 = [
        _component("Months of records", _scale(ind["months_with_data"], 1, 12), 12,
                   f"{ind['months_with_data']} of 12 months covered", "months"),
        _component("Continuity", ind["continuity"], 6,
                   "No gaps" if not ind["missing_months"] else f"{len(ind['missing_months'])} missing month(s)",
                   "continuity"),
        _component("Categorised transactions", ind["categorised_share"], 4,
                   f"{ind['categorised_share']:.0%} categorised", "categorised"),
        _component("Formal registration", formal / 3, 3, f"{formal} of 3 (CAC, TIN, business account)", "formal"),
    ]  # fmt: skip

    # Pillar 2 — Cash-flow strength (25)
    margin = ind["operating_margin"]
    p2 = [
        _component("Operating margin", _scale(margin or 0, 0.0, 0.30), 13,
                   "n/a" if margin is None else f"{margin:.0%} of inflows retained", "margin"),
        _component("Cash-positive months", _scale(ind["positive_months_ratio"], 0.4, 1.0), 12,
                   f"{ind['positive_months_ratio']:.0%} of months inflow > outflow", "positive_months"),
    ]  # fmt: skip

    # Pillar 3 — Stability & trend (25)
    cv, growth = ind["inflow_volatility_cv"], ind["inflow_growth"]
    p3 = [
        _component("Revenue stability", 0.3 if cv is None else _scale(cv, 1.0, 0.2), 15,
                   "Need 2+ months" if cv is None else f"Monthly inflow varies ±{cv:.0%}", "stability"),
        _component("Revenue trend", 0.3 if growth is None else _scale(growth, -0.3, 0.2), 10,
                   "Need 6+ months" if growth is None else f"{growth:+.0%} last 3 vs first 3 months", "trend"),
    ]  # fmt: skip

    # Pillar 4 — Obligations & risk (25)
    dsr, conc = ind["debt_service_ratio"], ind["top_customer_share"]
    p4 = [
        _component("Existing debt burden", _scale(dsr or 0, 0.40, 0.10), 13,
                   "No loan repayments seen" if not dsr else f"{dsr:.0%} of inflows go to loans", "debt"),
        _component("Customer concentration", 0.5 if conc is None else _scale(conc, 0.7, 0.25), 8,
                   "Counterparties not recorded" if conc is None else f"Largest customer = {conc:.0%} of sales",
                   "concentration"),
        _component("Years operating", _scale(profile.years_operating, 0, 5), 4,
                   f"{profile.years_operating} year(s)", "tenure"),
    ]  # fmt: skip

    pillars = [
        {"code": "records", "name": "Record quality", "components": p1},
        {"code": "cashflow", "name": "Cash-flow strength", "components": p2},
        {"code": "stability", "name": "Stability & trend", "components": p3},
        {"code": "obligations", "name": "Obligations & risk", "components": p4},
    ]
    for p in pillars:
        p["points"] = round(sum(c["points"] for c in p["components"]), 1)
        p["max"] = sum(c["max"] for c in p["components"])
    raw_total = round(sum(p["points"] for p in pillars))

    # Evidence cap: strong ratios over a short history are not evidence of
    # repayment capacity. Lenders discount them; so do we, explicitly.
    m = ind["months_with_data"]
    cap, cap_reason = 100, None
    if m < 3:
        cap, cap_reason = 35, "Fewer than 3 months of records — score capped at 35"
    elif m < 6:
        cap, cap_reason = 55, "Fewer than 6 months of records — score capped at 55"
    total = min(raw_total, cap)

    if total >= 80:
        band = "Lender-ready"
    elif total >= 65:
        band = "Nearly ready"
    elif total >= 40:
        band = "Building"
    else:
        band = "Not ready"
    return {"total": total, "raw_total": raw_total, "cap_reason": cap_reason, "band": band, "pillars": pillars}


def gaps(ind: dict, profile: Profile, scored: dict) -> list[dict]:
    out: list[dict] = []

    def add(code, title, detail, severity, kind, points=0.0):
        out.append({"code": code, "title": title, "detail": detail, "severity": severity, "kind": kind,
                    "points_available": round(points, 1)})  # fmt: skip

    if not ind.get("has_data"):
        add("no_records", "Upload your first statement",
            "Export a CSV of your bank, OPay, Moniepoint or PalmPay statement and upload it.",
            "high", "data", 0)  # fmt: skip
        return out

    comp = {c["code"]: c for p in scored["pillars"] for c in p["components"]}

    def missing_pts(code: str) -> float:
        return comp[code]["max"] - comp[code]["points"]

    m = ind["months_with_data"]
    if m < 6:
        add("months_short", "Add at least 6 months of statements",
            f"You have {m} month(s). Most Nigerian MFIs ask for 6 months; banks usually ask for 12.",
            "high", "data", missing_pts("months"))  # fmt: skip
    elif m < 12:
        add("months_partial", "Extend your records to 12 months",
            f"You have {m} months. Twelve months shows lenders a full trading cycle, including seasonality.",
            "medium", "data", missing_pts("months"))  # fmt: skip
    if ind["missing_months"]:
        add("missing_months", "Fill the missing months",
            "No transactions found for: " + ", ".join(ind["missing_months"]) + ".",
            "medium", "data", missing_pts("continuity"))  # fmt: skip
    if ind["uncategorised_count"]:
        add("uncategorised", f"Categorise {ind['uncategorised_count']} transaction(s)",
            "Tell us what these were so they count correctly as sales, stock, rent, etc.",
            "medium" if ind["categorised_share"] < 0.9 else "low", "data",
            missing_pts("categorised"))  # fmt: skip
    if ind["top_customer_share"] is None:
        add("no_counterparties", "Record who pays you",
            "Include a sender/customer column in your CSV so lenders can see you aren't reliant on one buyer.",
            "low", "data", missing_pts("concentration"))  # fmt: skip
    if not profile.has_cac_registration:
        add("cac", "Register your business with CAC",
            "A CAC business-name registration (Business Name, ~₦10k–₦20k) is required by most bank SME loans.",
            "high", "formalisation", 1)  # fmt: skip
    if not profile.has_tin:
        add("tin", "Get a Tax Identification Number (TIN)",
            "Free from FIRS / JTB. Many lenders and government schemes require a TIN.",
            "medium", "formalisation", 1)  # fmt: skip
    if not profile.has_business_account:
        add("business_account", "Open a business (corporate) account",
            "Keeping business money separate from personal spending makes your cash flow far easier to read.",
            "medium", "formalisation", 1)  # fmt: skip
    if ind["operating_margin"] is not None and ind["operating_margin"] < 0.05:
        add("thin_margin", "Your margin is very thin",
            "Outflows nearly match inflows. Review pricing and costs before taking on repayments.",
            "high", "financial", missing_pts("margin"))  # fmt: skip
    if ind["debt_service_ratio"] and ind["debt_service_ratio"] > 0.25:
        add("high_debt", "Existing loan repayments are high",
            f"{ind['debt_service_ratio']:.0%} of inflows already go to loans. New lenders will see this.",
            "high", "financial", missing_pts("debt"))  # fmt: skip
    if ind["top_customer_share"] and ind["top_customer_share"] > 0.5:
        add("concentration", "One customer dominates your sales",
            "Over half your sales come from a single payer — a risk lenders will price in.",
            "medium", "financial", missing_pts("concentration"))  # fmt: skip

    order = {"high": 0, "medium": 1, "low": 2}
    out.sort(key=lambda g: (order[g["severity"]], -g["points_available"]))
    return out


def capacity(ind: dict) -> dict | None:
    """Indicative affordable monthly repayment — a planning aid, not an offer.
    Uses the common rule-of-thumb that new repayments should not exceed ~35%
    of free operating cash flow after existing debt service."""
    if not ind.get("has_data") or ind["span_months"] < 3:
        return None
    span = ind["span_months"]
    free = (ind["total_inflow_kobo"] - ind["total_outflow_kobo"]) / span
    if free <= 0:
        return {"monthly_free_cash_kobo": round(free), "indicative_repayment_kobo": 0}
    return {"monthly_free_cash_kobo": round(free), "indicative_repayment_kobo": round(free * 0.35)}


def assess(txns: list[Txn], profile: Profile) -> dict:
    ind = compute_indicators(txns)
    scored = score(ind, profile)
    return {
        "indicators": ind,
        "score": scored,
        "gaps": gaps(ind, profile, scored),
        "capacity": capacity(ind),
        "summary": _summary(ind, scored),
    }


_MONTHS = "Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec".split()


def _month_name(ym: str) -> str:
    y, m = ym.split("-")
    return f"{_MONTHS[int(m) - 1]} {y}"


def _summary(ind: dict, scored: dict) -> str:
    if not ind.get("has_data"):
        return "No records yet. Upload a statement to see your readiness."
    weakest = min(scored["pillars"], key=lambda p: p["points"] / p["max"])
    return (
        f"{ind['months_with_data']} months of records ({_month_name(ind['period_start'])} to "
        f"{_month_name(ind['period_end'])}), "
        f"average monthly inflow {_naira(ind['avg_monthly_inflow_kobo'])}. "
        f"Score {scored['total']}/100 ({scored['band']}); weakest area: {weakest['name'].lower()}."
    )
