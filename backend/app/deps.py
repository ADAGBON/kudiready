import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Business, User
from app.security import decode_access_token

bearer = HTTPBearer(auto_error=False)


def current_user(
    creds: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: Session = Depends(get_db),
) -> User:
    unauthorized = HTTPException(status.HTTP_401_UNAUTHORIZED, "Not authenticated", headers={"WWW-Authenticate": "Bearer"})
    if creds is None:
        raise unauthorized
    try:
        user_id = decode_access_token(creds.credentials)
    except (jwt.PyJWTError, ValueError, KeyError):
        raise unauthorized from None
    user = db.get(User, user_id)
    if user is None:
        raise unauthorized
    return user


def current_business(user: User = Depends(current_user), db: Session = Depends(get_db)) -> Business:
    """Every business-scoped endpoint resolves the business from the token,
    never from a client-supplied id — so one owner can't read another's data."""
    business = db.scalar(select(Business).where(Business.owner_id == user.id))
    if business is None:
        raise HTTPException(status.HTTP_409_CONFLICT, "Create your business profile first")
    return business
