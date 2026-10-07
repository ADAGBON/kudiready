"""Relational data model.

Money is stored as integer kobo (1 NGN = 100 kobo) in BIGINT columns — never
floats — so sums are exact and reproducible. Types are kept portable
(Uuid, JSON) so the same models run on Postgres in production and SQLite in
fast unit tests.
"""

import enum
import uuid
from datetime import UTC, date, datetime

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


def utcnow() -> datetime:
    return datetime.now(UTC)


class Direction(enum.StrEnum):
    credit = "credit"  # money in
    debit = "debit"  # money out


class Source(enum.StrEnum):
    csv = "csv"
    manual = "manual"


class Category(enum.StrEnum):
    sales = "sales"
    other_income = "other_income"
    loan_in = "loan_in"
    inventory = "inventory"
    rent = "rent"
    payroll = "payroll"
    utilities = "utilities"
    transport = "transport"
    tax = "tax"
    loan_repayment = "loan_repayment"
    bank_charges = "bank_charges"
    transfer = "transfer"
    other_expense = "other_expense"
    uncategorised = "uncategorised"


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(254), unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(120))
    password_hash: Mapped[str] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    business: Mapped["Business | None"] = relationship(back_populates="owner", uselist=False)


class Business(Base):
    __tablename__ = "businesses"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    owner_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True)
    name: Mapped[str] = mapped_column(String(160))
    sector: Mapped[str] = mapped_column(String(60))
    state: Mapped[str] = mapped_column(String(40))
    years_operating: Mapped[int] = mapped_column(Integer, default=0)
    employees: Mapped[int] = mapped_column(Integer, default=0)
    # Formalisation signals (declared, booleans only — we never store the
    # identifiers themselves; see report §6 on data minimisation).
    has_cac_registration: Mapped[bool] = mapped_column(Boolean, default=False)
    has_tin: Mapped[bool] = mapped_column(Boolean, default=False)
    has_business_account: Mapped[bool] = mapped_column(Boolean, default=False)
    keeps_written_records: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    owner: Mapped[User] = relationship(back_populates="business")
    transactions: Mapped[list["Transaction"]] = relationship(
        back_populates="business", cascade="all, delete-orphan", passive_deletes=True
    )


class Transaction(Base):
    __tablename__ = "transactions"
    __table_args__ = (
        # Re-uploading an overlapping statement must not double-count money.
        UniqueConstraint("business_id", "fingerprint", name="uq_txn_business_fingerprint"),
        Index("ix_txn_business_date", "business_id", "txn_date"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    business_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("businesses.id", ondelete="CASCADE"))
    txn_date: Mapped[date] = mapped_column(Date)
    narration: Mapped[str] = mapped_column(String(300))
    counterparty: Mapped[str | None] = mapped_column(String(160), nullable=True)
    amount_kobo: Mapped[int] = mapped_column(BigInteger)  # always positive
    direction: Mapped[Direction] = mapped_column(Enum(Direction, name="direction"))
    category: Mapped[Category] = mapped_column(Enum(Category, name="category"))
    category_source: Mapped[str] = mapped_column(String(10), default="rule")  # rule | user
    source: Mapped[Source] = mapped_column(Enum(Source, name="source"))
    fingerprint: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    business: Mapped[Business] = relationship(back_populates="transactions")


class ShareLink(Base):
    """Read-only, expiring link a business owner gives a lender. Only the
    SHA-256 of the token is stored, so a DB leak does not leak live links."""

    __tablename__ = "share_links"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    business_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("businesses.id", ondelete="CASCADE"), index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    label: Mapped[str] = mapped_column(String(80))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    revoked: Mapped[bool] = mapped_column(Boolean, default=False)
    view_count: Mapped[int] = mapped_column(Integer, default=0)
    snapshot: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
