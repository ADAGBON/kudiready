"""Test harness.

Runs against whatever DATABASE_URL points to: SQLite in-memory by default
(fast local loop), real Postgres in CI (same schema, same constraints).
"""

import os

os.environ.setdefault("DATABASE_URL", "sqlite://")
os.environ.setdefault("JWT_SECRET", "test-secret-test-secret-test-secret-123")

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app import main  # noqa: E402
from app.db import Base, engine  # noqa: E402


@pytest.fixture(autouse=True)
def _schema():
    Base.metadata.create_all(engine)
    main._auth_hits.clear()
    yield
    Base.metadata.drop_all(engine)


@pytest.fixture
def client() -> TestClient:
    return TestClient(main.app)


def register(client: TestClient, email: str = "ada@example.com") -> dict:
    r = client.post("/v1/auth/register", json={"email": email, "full_name": "Ada Obi", "password": "s3cure-pass"})
    assert r.status_code == 201, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


BUSINESS = {
    "name": "Mama Ada Provisions",
    "sector": "retail_trade",
    "state": "Lagos",
    "years_operating": 4,
    "employees": 2,
    "has_cac_registration": True,
    "has_tin": False,
    "has_business_account": True,
    "keeps_written_records": True,
}


@pytest.fixture
def owner(client) -> dict:
    h = register(client)
    r = client.post("/v1/business", json=BUSINESS, headers=h)
    assert r.status_code == 201, r.text
    return h
