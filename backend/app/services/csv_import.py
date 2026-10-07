"""Bank / mobile-money statement CSV import.

Nigerian statements come in many shapes. We accept either
  * a signed `amount` column (negative = money out), or
  * separate `debit` / `credit` (a.k.a. withdrawal / deposit / money out / money in) columns,
plus a date column and a narration column, matched case-insensitively from
a list of common header aliases. Every row is validated independently: bad
rows are reported back, good rows are kept.
"""

import csv
import hashlib
import io
import re
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

from app.models import Direction

DATE_ALIASES = ("date", "txn date", "transaction date", "trans date", "value date", "posting date")
NARRATION_ALIASES = ("narration", "description", "details", "remarks", "transaction details", "particulars")
AMOUNT_ALIASES = ("amount", "amount (ngn)", "amount(ngn)", "value")
DEBIT_ALIASES = ("debit", "debits", "withdrawal", "withdrawals", "money out", "dr")
CREDIT_ALIASES = ("credit", "credits", "deposit", "deposits", "money in", "cr", "lodgement")
COUNTERPARTY_ALIASES = ("counterparty", "beneficiary", "sender", "from/to", "payee", "customer")
REFERENCE_ALIASES = ("reference", "ref", "transaction ref", "session id", "txn ref")

DATE_FORMATS = ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%d-%b-%Y", "%d %b %Y", "%d-%b-%y", "%d/%m/%y",
                "%Y/%m/%d", "%d %B %Y")  # fmt: skip

_MONEY_JUNK = re.compile(r"[₦,\s]|NGN|N(?=\d)", re.IGNORECASE)


class ImportFormatError(ValueError):
    pass


@dataclass(frozen=True)
class ParsedRow:
    txn_date: date
    narration: str
    counterparty: str | None
    amount_kobo: int
    direction: Direction
    fingerprint: str


def _find(headers: dict[str, str], aliases: tuple[str, ...]) -> str | None:
    for a in aliases:
        if a in headers:
            return headers[a]
    return None


def parse_date(raw: str) -> date:
    raw = raw.strip()
    # Some exports append a time: "2026-03-04 14:22:01"
    candidates = [raw, raw.split(" ")[0]] if " " in raw and ":" in raw else [raw]
    for c in candidates:
        for fmt in DATE_FORMATS:
            try:
                return datetime.strptime(c, fmt).date()
            except ValueError:
                continue
    raise ValueError(f"unrecognised date '{raw}'")


def parse_money(raw: str | None) -> Decimal | None:
    if raw is None:
        return None
    s = raw.strip()
    if not s or s in {"-", "--"}:
        return None
    negative = s.startswith("(") and s.endswith(")")
    s = _MONEY_JUNK.sub("", s.strip("()"))
    try:
        value = Decimal(s)
    except InvalidOperation:
        raise ValueError(f"unrecognised amount '{raw}'") from None
    return -value if negative else value


def to_kobo(value: Decimal) -> int:
    return int((value * 100).quantize(Decimal("1")))


def fingerprint(
    d: date, narration: str, amount_kobo: int, direction: Direction, ref: str | None, occurrence: int = 0
) -> str:
    """Stable identity for a statement line. `occurrence` distinguishes genuinely
    identical lines on the same day (two ₦5,000 POS sales at 10am and 4pm with no
    reference) while still deduplicating when the same statement is re-uploaded."""
    norm = " ".join(narration.lower().split())
    basis = f"{d.isoformat()}|{norm}|{amount_kobo}|{direction}|{ref or ''}|{occurrence}"
    return hashlib.sha256(basis.encode()).hexdigest()


def parse_statement(content: bytes, max_rows: int) -> tuple[list[ParsedRow], list[str], int]:
    """Returns (rows, errors, rows_read). Raises ImportFormatError if the file
    as a whole is unusable (wrong encoding, missing required columns)."""
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError:
        try:
            text = content.decode("latin-1")
        except UnicodeDecodeError:
            raise ImportFormatError("File is not a readable text CSV") from None

    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames:
        raise ImportFormatError("CSV has no header row")
    headers = {h.strip().lower(): h for h in reader.fieldnames if h}

    date_col = _find(headers, DATE_ALIASES)
    narr_col = _find(headers, NARRATION_ALIASES)
    amount_col = _find(headers, AMOUNT_ALIASES)
    debit_col = _find(headers, DEBIT_ALIASES)
    credit_col = _find(headers, CREDIT_ALIASES)
    cp_col = _find(headers, COUNTERPARTY_ALIASES)
    ref_col = _find(headers, REFERENCE_ALIASES)

    if not date_col or not narr_col:
        raise ImportFormatError("CSV needs a date column and a narration/description column")
    if not amount_col and not (debit_col or credit_col):
        raise ImportFormatError("CSV needs an 'amount' column or 'debit'/'credit' columns")

    rows: list[ParsedRow] = []
    errors: list[str] = []
    rows_read = 0
    seen: dict[tuple, int] = {}
    for line_no, raw in enumerate(reader, start=2):
        if rows_read >= max_rows:
            errors.append(f"Stopped after {max_rows} rows (upload limit)")
            break
        if not any((v or "").strip() for v in raw.values()):
            continue
        rows_read += 1
        try:
            d = parse_date(raw.get(date_col) or "")
            narration = (raw.get(narr_col) or "").strip()[:300]
            if not narration:
                raise ValueError("empty narration")
            if amount_col:
                amt = parse_money(raw.get(amount_col))
                if amt is None or amt == 0:
                    raise ValueError("missing amount")
                direction = Direction.credit if amt > 0 else Direction.debit
                amt = abs(amt)
            else:
                dr = parse_money(raw.get(debit_col)) if debit_col else None
                cr = parse_money(raw.get(credit_col)) if credit_col else None
                if cr and cr > 0:
                    direction, amt = Direction.credit, cr
                elif dr and dr > 0:
                    direction, amt = Direction.debit, dr
                else:
                    raise ValueError("no debit or credit amount")
            kobo = to_kobo(amt)
            if kobo > 10_000_000_000_00:
                raise ValueError("amount implausibly large")
            cp = (raw.get(cp_col) or "").strip()[:160] or None if cp_col else None
            ref = (raw.get(ref_col) or "").strip() or None if ref_col else None
            key = (d, " ".join(narration.lower().split()), kobo, direction, ref)
            occurrence = seen.get(key, 0)
            seen[key] = occurrence + 1
            fp = fingerprint(d, narration, kobo, direction, ref, occurrence)
            rows.append(ParsedRow(d, narration, cp, kobo, direction, fp))
        except ValueError as e:
            if len(errors) < 50:
                errors.append(f"Row {line_no}: {e}")
    return rows, errors, rows_read
