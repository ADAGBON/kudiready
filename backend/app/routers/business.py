from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import current_business, current_user
from app.models import Business, User
from app.schemas import NIGERIAN_STATES, SECTORS, BusinessIn, BusinessOut

router = APIRouter(prefix="/v1/business", tags=["business"])


def _validate(body: BusinessIn) -> None:
    try:
        body.validate_domain()
    except ValueError as e:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(e)) from None


@router.get("/options")
def options() -> dict:
    return {"sectors": sorted(SECTORS), "states": sorted(NIGERIAN_STATES)}


@router.post("", response_model=BusinessOut, status_code=status.HTTP_201_CREATED)
def create_business(body: BusinessIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    _validate(body)
    if db.scalar(select(Business.id).where(Business.owner_id == user.id)):
        raise HTTPException(status.HTTP_409_CONFLICT, "You already have a business profile")
    business = Business(owner_id=user.id, **body.model_dump())
    db.add(business)
    db.commit()
    return business


@router.get("", response_model=BusinessOut)
def get_business(business: Business = Depends(current_business)):
    return business


@router.put("", response_model=BusinessOut)
def update_business(body: BusinessIn, business: Business = Depends(current_business), db: Session = Depends(get_db)):
    _validate(body)
    for k, v in body.model_dump().items():
        setattr(business, k, v)
    db.commit()
    return business
