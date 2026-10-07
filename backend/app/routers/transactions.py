import uuid
from decimal import Decimal

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy import delete, func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.db import get_db
from app.deps import current_business
from app.models import Business, Category, Direction, Source, Transaction
from app.schemas import CategoryUpdate, ImportResult, TransactionIn, TransactionOut, TransactionPage
from app.services.categorise import categorise
from app.services.csv_import import ImportFormatError, fingerprint, parse_statement, to_kobo

router = APIRouter(prefix="/v1/transactions", tags=["transactions"])


@router.post("/import", response_model=ImportResult)
async def import_csv(
    file: UploadFile = File(...),
    business: Business = Depends(current_business),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> ImportResult:
    if file.filename and not file.filename.lower().endswith((".csv", ".txt")):
        raise HTTPException(status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, "Upload a .csv file")
    content = await file.read(settings.max_upload_bytes + 1)
    if len(content) > settings.max_upload_bytes:
        raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, "File is larger than 2 MB")
    try:
        rows, errors, rows_read = parse_statement(content, settings.max_rows_per_upload)
    except ImportFormatError as e:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(e)) from None

    existing = set(
        db.scalars(
            select(Transaction.fingerprint).where(
                Transaction.business_id == business.id,
                Transaction.fingerprint.in_([r.fingerprint for r in rows]),
            )
        )
    )
    new = [r for r in rows if r.fingerprint not in existing]
    values = [
        {
            "id": uuid.uuid4(),
            "business_id": business.id,
            "txn_date": r.txn_date,
            "narration": r.narration,
            "counterparty": r.counterparty,
            "amount_kobo": r.amount_kobo,
            "direction": r.direction,
            "category": categorise(r.narration, r.direction),
            "category_source": "rule",
            "source": Source.csv,
            "fingerprint": r.fingerprint,
        }
        for r in new
    ]
    if values:
        if db.bind.dialect.name == "postgresql":
            # ON CONFLICT DO NOTHING makes concurrent duplicate uploads safe too.
            stmt = pg_insert(Transaction).values(values).on_conflict_do_nothing(constraint="uq_txn_business_fingerprint")
            db.execute(stmt)
        else:
            db.add_all(Transaction(**v) for v in values)
        db.commit()
    return ImportResult(
        rows_read=rows_read,
        imported=len(new),
        duplicates=len(rows) - len(new),
        rejected=rows_read - len(rows),
        errors=errors,
    )


@router.post("", response_model=TransactionOut, status_code=status.HTTP_201_CREATED)
def add_transaction(body: TransactionIn, business: Business = Depends(current_business), db: Session = Depends(get_db)):
    kobo = to_kobo(Decimal(str(body.amount_naira)))
    category = body.category or categorise(body.narration, body.direction)
    txn = Transaction(
        business_id=business.id,
        txn_date=body.txn_date,
        narration=body.narration.strip(),
        counterparty=(body.counterparty or "").strip() or None,
        amount_kobo=kobo,
        direction=body.direction,
        category=category,
        category_source="user" if body.category else "rule",
        source=Source.manual,
        fingerprint=fingerprint(body.txn_date, body.narration, kobo, body.direction, f"manual-{uuid.uuid4()}"),
    )
    db.add(txn)
    db.commit()
    return txn


@router.get("", response_model=TransactionPage)
def list_transactions(
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=200),
    direction: Direction | None = None,
    category: Category | None = None,
    q: str | None = Query(None, max_length=80),
    business: Business = Depends(current_business),
    db: Session = Depends(get_db),
) -> TransactionPage:
    filters = [Transaction.business_id == business.id]
    if direction:
        filters.append(Transaction.direction == direction)
    if category:
        filters.append(Transaction.category == category)
    if q:
        filters.append(Transaction.narration.ilike(f"%{q}%"))
    total = db.scalar(select(func.count()).select_from(Transaction).where(*filters)) or 0
    items = db.scalars(
        select(Transaction)
        .where(*filters)
        .order_by(Transaction.txn_date.desc(), Transaction.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return TransactionPage(
        items=[TransactionOut.model_validate(t) for t in items], total=total, page=page, page_size=page_size
    )


def _owned(db: Session, business: Business, txn_id: uuid.UUID) -> Transaction:
    txn = db.get(Transaction, txn_id)
    if txn is None or txn.business_id != business.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Transaction not found")
    return txn


@router.patch("/{txn_id}", response_model=TransactionOut)
def recategorise(
    txn_id: uuid.UUID,
    body: CategoryUpdate,
    business: Business = Depends(current_business),
    db: Session = Depends(get_db),
):
    txn = _owned(db, business, txn_id)
    txn.category = body.category
    txn.category_source = "user"
    db.commit()
    return txn


@router.delete("/{txn_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_transaction(
    txn_id: uuid.UUID, business: Business = Depends(current_business), db: Session = Depends(get_db)
) -> None:
    db.delete(_owned(db, business, txn_id))
    db.commit()


@router.delete("", status_code=status.HTTP_204_NO_CONTENT)
def delete_all(business: Business = Depends(current_business), db: Session = Depends(get_db)) -> None:
    db.execute(delete(Transaction).where(Transaction.business_id == business.id))
    db.commit()
