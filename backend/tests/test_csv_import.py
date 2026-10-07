from datetime import date
from decimal import Decimal

import pytest

from app.models import Direction
from app.services.csv_import import ImportFormatError, parse_date, parse_money, parse_statement


@pytest.mark.parametrize(
    "raw,expected",
    [("2026-03-04", date(2026, 3, 4)), ("04/03/2026", date(2026, 3, 4)), ("04-Mar-2026", date(2026, 3, 4)),
     ("04 Mar 2026", date(2026, 3, 4)), ("2026-03-04 14:22:01", date(2026, 3, 4))],
)  # fmt: skip
def test_parse_date_formats(raw, expected):
    assert parse_date(raw) == expected


@pytest.mark.parametrize(
    "raw,expected",
    [("1,250.50", Decimal("1250.50")), ("₦5,000", Decimal("5000")), ("NGN 300", Decimal("300")),
     ("(2,000.00)", Decimal("-2000.00")), ("-45", Decimal("-45")), ("", None)],
)  # fmt: skip
def test_parse_money(raw, expected):
    assert parse_money(raw) == expected


def test_signed_amount_layout():
    csv = b"Date,Description,Amount\n2026-01-02,POS sale,5000\n2026-01-03,Rent,-2000\n"
    rows, errors, n = parse_statement(csv, 100)
    assert n == 2 and not errors
    assert rows[0].direction == Direction.credit and rows[0].amount_kobo == 500000
    assert rows[1].direction == Direction.debit and rows[1].amount_kobo == 200000


def test_debit_credit_layout_and_bad_rows_reported():
    csv = (b"Transaction Date,Narration,Debit,Credit\n"
           b"02-Jan-2026,POS SALE,,\"12,000.00\"\n"
           b"not-a-date,BAD,,100\n"
           b"03-Jan-2026,RENT,\"45,000.00\",\n")  # fmt: skip
    rows, errors, n = parse_statement(csv, 100)
    assert n == 3 and len(rows) == 2
    assert errors and "Row 3" in errors[0]


def test_identical_same_day_lines_both_kept():
    csv = b"Date,Description,Amount\n2026-01-02,POS sale,5000\n2026-01-02,POS sale,5000\n"
    rows, _, _ = parse_statement(csv, 100)
    assert len({r.fingerprint for r in rows}) == 2


def test_missing_required_columns():
    with pytest.raises(ImportFormatError):
        parse_statement(b"Foo,Bar\n1,2\n", 100)
    with pytest.raises(ImportFormatError):
        parse_statement(b"Date,Narration\n2026-01-01,x\n", 100)


def test_row_limit():
    body = "Date,Description,Amount\n" + "".join(f"2026-01-02,sale {i},10\n" for i in range(20))
    rows, errors, _ = parse_statement(body.encode(), 5)
    assert len(rows) == 5 and "limit" in errors[-1]
