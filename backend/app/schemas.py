import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models import Category, Direction, Source

NIGERIAN_STATES = {
    "Abia", "Adamawa", "Akwa Ibom", "Anambra", "Bauchi", "Bayelsa", "Benue", "Borno", "Cross River",
    "Delta", "Ebonyi", "Edo", "Ekiti", "Enugu", "FCT", "Gombe", "Imo", "Jigawa", "Kaduna", "Kano",
    "Katsina", "Kebbi", "Kogi", "Kwara", "Lagos", "Nasarawa", "Niger", "Ogun", "Ondo", "Osun", "Oyo",
    "Plateau", "Rivers", "Sokoto", "Taraba", "Yobe", "Zamfara",
}  # fmt: skip

SECTORS = {
    "retail_trade", "food_services", "agriculture", "manufacturing", "fashion_tailoring",
    "transport_logistics", "beauty_personal_care", "ict_services", "construction", "other",
}  # fmt: skip


class ORM(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# ---- auth ----
class RegisterIn(BaseModel):
    email: EmailStr
    full_name: str = Field(min_length=2, max_length=120)
    password: str = Field(min_length=8, max_length=72)


class LoginIn(BaseModel):
    email: EmailStr
    password: str = Field(max_length=72)


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"  # noqa: S105


class UserOut(ORM):
    id: uuid.UUID
    email: str
    full_name: str
    has_business: bool = False


# ---- business ----
class BusinessIn(BaseModel):
    name: str = Field(min_length=2, max_length=160)
    sector: str
    state: str
    years_operating: int = Field(ge=0, le=100)
    employees: int = Field(ge=0, le=10_000)
    has_cac_registration: bool = False
    has_tin: bool = False
    has_business_account: bool = False
    keeps_written_records: bool = False

    def validate_domain(self) -> None:
        if self.sector not in SECTORS:
            raise ValueError(f"sector must be one of {sorted(SECTORS)}")
        if self.state not in NIGERIAN_STATES:
            raise ValueError("state must be a Nigerian state or FCT")


class BusinessOut(ORM, BusinessIn):
    id: uuid.UUID
    created_at: datetime


# ---- transactions ----
class TransactionIn(BaseModel):
    txn_date: date
    narration: str = Field(min_length=1, max_length=300)
    counterparty: str | None = Field(default=None, max_length=160)
    amount_naira: float = Field(gt=0, le=10_000_000_000)
    direction: Direction
    category: Category | None = None


class TransactionOut(ORM):
    id: uuid.UUID
    txn_date: date
    narration: str
    counterparty: str | None
    amount_kobo: int
    direction: Direction
    category: Category
    category_source: str
    source: Source


class TransactionPage(BaseModel):
    items: list[TransactionOut]
    total: int
    page: int
    page_size: int


class CategoryUpdate(BaseModel):
    category: Category


class ImportResult(BaseModel):
    rows_read: int
    imported: int
    duplicates: int
    rejected: int
    errors: list[str]


# ---- share links ----
class ShareIn(BaseModel):
    label: str = Field(min_length=1, max_length=80)


class ShareOut(ORM):
    id: uuid.UUID
    label: str
    expires_at: datetime
    revoked: bool
    view_count: int
    created_at: datetime


class ShareCreated(ShareOut):
    token: str
