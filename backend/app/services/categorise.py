"""Rule-based transaction categorisation.

Deterministic keyword rules tuned to Nigerian bank / fintech narrations
(POS, NIP transfers, USSD, airtime, FIRS/state IRS). Rules are ordered;
first match wins. Deterministic rules are auditable — a lender can see
exactly why a line was called "sales" — which matters more here than the
marginal accuracy a black-box classifier might add.
"""

import re

from app.models import Category, Direction

_DEBIT_RULES: list[tuple[Category, tuple[str, ...]]] = [
    (Category.bank_charges, ("sms alert", "stamp duty", "vat on", "charge", "maintenance fee", "comm ")),
    (Category.loan_repayment, ("loan repay", "loan rpmt", "repayment", "credit direct", "fairmoney",
                               "carbon", "renmoney", "lapo", "palmcredit", "installment")),
    (Category.tax, ("firs", "lirs", "tax", "levy", "lasg", "irs ")),
    (Category.rent, ("rent", "shop lease", "landlord")),
    (Category.payroll, ("salary", "wages", "staff pay", "stipend")),
    (Category.utilities, ("airtime", "data bundle", "ikedc", "ekedc", "phcn", "nepa", "electricity",
                          "dstv", "gotv", "internet", "water bill", "diesel", "fuel", "petrol")),
    (Category.transport, ("bolt", "uber", "transport", "logistics", "gig ", "delivery", "dispatch")),
    (Category.inventory, ("supplier", "stock", "goods", "wholesale", "market purchase", "restock",
                          "inventory", "raw material", "invoice")),
    (Category.transfer, ("own account", "self transfer", "to self", "savings", "piggyvest", "cowrywise")),
]  # fmt: skip

_CREDIT_RULES: list[tuple[Category, tuple[str, ...]]] = [
    (Category.loan_in, ("loan disb", "loan credit", "disbursement")),
    (Category.transfer, ("own account", "self transfer", "from self", "reversal")),
    (Category.other_income, ("interest", "refund", "cashback", "grant")),
    (Category.sales, ("pos", "sale", "payment for", "customer", "order", "trf from", "transfer from",
                      "nip", "ussd", "web", "paystack", "flutterwave", "moniepoint", "opay", "palmpay")),
]  # fmt: skip

_SPACE = re.compile(r"\s+")


def categorise(narration: str, direction: Direction) -> Category:
    text = " " + _SPACE.sub(" ", narration.lower()) + " "
    rules = _CREDIT_RULES if direction == Direction.credit else _DEBIT_RULES
    for category, keywords in rules:
        if any(k in text for k in keywords):
            return category
    # Unmatched money-in for a trading MSME is most often a customer payment;
    # we still mark it so the owner can confirm (see "uncategorised" gap).
    return Category.uncategorised


INCOME_CATEGORIES = {Category.sales, Category.other_income}
EXCLUDED_FROM_CASHFLOW = {Category.transfer, Category.loan_in}
