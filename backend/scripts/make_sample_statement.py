"""Generate a realistic synthetic 12-month statement for a Lagos provisions
shop, in the debit/credit layout most Nigerian banks export. Synthetic data
only — no real customer records are used anywhere in this project.

    python scripts/make_sample_statement.py ../frontend/public
"""

import csv
import random
import sys
from datetime import date, timedelta

random.seed(7)

CUSTOMERS = ["Chinedu Okafor", "Bisi Adeyemi", "Musa Bello", "Ngozi Eze", "Tunde Bakare", "Halima Sani",
             "Emeka Nwosu", "Funke Alabi", "Kunle Ajayi", "Grace Udo", "Obinna Ike", "Zainab Yusuf"]  # fmt: skip
SEASONAL = {1: 0.85, 2: 0.9, 3: 1.0, 4: 1.05, 5: 0.95, 6: 0.9, 7: 0.95, 8: 1.0, 9: 1.05, 10: 1.1, 11: 1.2, 12: 1.45}


def rows(start: date, months: int):
    balance = 185_000.0
    d = start
    end_month = (start.month - 1 + months) % 12 + 1
    end_year = start.year + (start.month - 1 + months) // 12
    end = date(end_year, end_month, 1)
    ref = 100_000
    growth = 1.0
    while d < end:
        season = SEASONAL[d.month] * growth
        events = []
        for _ in range(random.randint(3, 6)):  # daily sales
            amt = round(random.uniform(2_500, 18_000) * season, -1)
            if random.random() < 0.55:
                events.append(("POS PURCHASE SETTLEMENT MONIEPOINT", "", amt, ""))
            else:
                c = random.choice(CUSTOMERS)
                events.append((f"NIP TRF FROM {c.upper()} - PAYMENT FOR GOODS", "", amt, c))
        if d.weekday() == 1:
            events.append(
                ("TRF TO ALABA WHOLESALE SUPPLIER - RESTOCK", round(random.uniform(150_000, 230_000) * season, -2), "", "")
            )  # noqa: E501
        if d.weekday() == 4 and random.random() < 0.6:
            events.append(
                ("TRF TO DANGOTE DISTRIBUTOR GOODS INVOICE", round(random.uniform(70_000, 120_000) * season, -2), "", "")
            )  # noqa: E501
        if d.day == 1:
            events.append(("SHOP RENT - LANDLORD", 45_000, "", ""))
            events.append(("LAPO MFB LOAN REPAYMENT", 38_500, "", ""))
        if d.day == 28:
            events.append(("STAFF SALARY - SHOP ATTENDANT", 55_000, "", ""))
            events.append(("IKEDC PREPAID ELECTRICITY", round(random.uniform(9_000, 15_000), -2), "", ""))
        if d.day in (5, 20):
            events.append(("MTN AIRTIME/DATA BUNDLE", 3_000, "", ""))
            events.append(("BOLT LOGISTICS DELIVERY", round(random.uniform(4_000, 9_000), -2), "", ""))
        if d.day == 15:
            events.append(("LASG LEVY - MARKET ASSOCIATION", 2_500, "", ""))
            events.append(("SMS ALERT CHARGES", 120, "", ""))
        if d.weekday() == 5 and random.random() < 0.5:
            events.append(
                (f"OPAY TRF TO 803{random.randint(1000000, 9999999)}", round(random.uniform(8_000, 40_000), -2), "", "")
            )
        for narration, dr, cr, sender in events:
            balance += (cr or 0) - (dr or 0)
            ref += 1
            yield {
                "Transaction Date": d.strftime("%d-%b-%Y"),
                "Narration": narration,
                "Sender": sender,
                "Debit": f"{dr:,.2f}" if dr else "",
                "Credit": f"{cr:,.2f}" if cr else "",
                "Balance": f"{balance:,.2f}",
                "Reference": f"KR{ref}",
            }
        d += timedelta(days=1)
        if d.day == 1:
            growth *= 1.012


FIELDS = ["Transaction Date", "Narration", "Sender", "Debit", "Credit", "Balance", "Reference"]
MISSING = "Feb-2026"  # demo story: the owner "lost" February's statement


def main(out_dir: str) -> None:
    all_rows = list(rows(date(2025, 10, 1), 12))
    main_rows = [r for r in all_rows if MISSING not in r["Transaction Date"]]
    feb_rows = [r for r in all_rows if MISSING in r["Transaction Date"]]
    for name, data in (("sample-statement.csv", main_rows), ("sample-statement-feb-2026.csv", feb_rows)):
        with open(f"{out_dir}/{name}", "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=FIELDS)
            w.writeheader()
            w.writerows(data)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else ".")
