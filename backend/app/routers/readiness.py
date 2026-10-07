import uuid
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.db import get_db
from app.deps import current_business
from app.models import Business, ShareLink, Transaction
from app.schemas import ShareCreated, ShareIn, ShareOut
from app.security import hash_token, new_share_token
from app.services.readiness import Profile, Txn, assess

router = APIRouter(prefix="/v1", tags=["readiness"])


def build_assessment(db: Session, business: Business) -> dict:
    rows = db.execute(
        select(
            Transaction.txn_date,
            Transaction.amount_kobo,
            Transaction.direction,
            Transaction.category,
            Transaction.counterparty,
        ).where(Transaction.business_id == business.id)
    ).all()
    txns = [Txn(*r) for r in rows]
    profile = Profile(
        years_operating=business.years_operating,
        has_cac_registration=business.has_cac_registration,
        has_tin=business.has_tin,
        has_business_account=business.has_business_account,
        keeps_written_records=business.keeps_written_records,
    )
    result = assess(txns, profile)
    result["business"] = {
        "name": business.name,
        "sector": business.sector,
        "state": business.state,
        "years_operating": business.years_operating,
        "employees": business.employees,
        "has_cac_registration": business.has_cac_registration,
        "has_tin": business.has_tin,
        "has_business_account": business.has_business_account,
    }
    result["generated_at"] = datetime.now(UTC).isoformat()
    return result


@router.get("/readiness")
def readiness(business: Business = Depends(current_business), db: Session = Depends(get_db)) -> dict:
    return build_assessment(db, business)


# ---- lender share links ----
@router.post("/share-links", response_model=ShareCreated, status_code=status.HTTP_201_CREATED)
def create_share(
    body: ShareIn,
    business: Business = Depends(current_business),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> ShareCreated:
    raw, digest = new_share_token()
    link = ShareLink(
        business_id=business.id,
        token_hash=digest,
        label=body.label.strip(),
        expires_at=datetime.now(UTC) + timedelta(days=settings.share_link_days),
        # Frozen snapshot: the lender sees exactly what the owner shared,
        # even if records change later.
        snapshot=build_assessment(db, business),
    )
    db.add(link)
    db.commit()
    return ShareCreated(token=raw, **ShareOut.model_validate(link).model_dump())


@router.get("/share-links", response_model=list[ShareOut])
def list_shares(business: Business = Depends(current_business), db: Session = Depends(get_db)):
    return db.scalars(
        select(ShareLink).where(ShareLink.business_id == business.id).order_by(ShareLink.created_at.desc())
    ).all()


@router.delete("/share-links/{link_id}", status_code=status.HTTP_204_NO_CONTENT)
def revoke_share(link_id: uuid.UUID, business: Business = Depends(current_business), db: Session = Depends(get_db)) -> None:
    link = db.get(ShareLink, link_id)
    if link is None or link.business_id != business.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Share link not found")
    link.revoked = True
    db.commit()


@router.get("/public/profile/{token}", tags=["public"])
def public_profile(token: str, db: Session = Depends(get_db)) -> dict:
    """Unauthenticated, read-only view for lenders holding a valid link."""
    if len(token) > 64:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Link not found")
    link = db.scalar(select(ShareLink).where(ShareLink.token_hash == hash_token(token)))
    expires = link.expires_at if link else None
    if expires is not None and expires.tzinfo is None:  # SQLite drops tz info
        expires = expires.replace(tzinfo=UTC)
    if link is None or link.revoked or expires < datetime.now(UTC):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "This link is invalid, expired or revoked")
    link.view_count += 1
    db.commit()
    return {"label": link.label, "shared_at": link.created_at.isoformat(), **(link.snapshot or {})}
