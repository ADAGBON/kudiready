from pathlib import Path

from tests.conftest import BUSINESS, register

SAMPLE = (Path(__file__).parent / "sample-statement.csv").read_bytes()
SAMPLE_FEB = (Path(__file__).parent / "sample-statement-feb-2026.csv").read_bytes()


def upload(client, headers, content=SAMPLE, name="statement.csv"):
    return client.post("/v1/transactions/import", files={"file": (name, content, "text/csv")}, headers=headers)


def test_health(client):
    r = client.get("/healthz")
    assert r.status_code == 200 and r.json()["database"] is True
    assert r.headers["X-Content-Type-Options"] == "nosniff"


def test_register_login_me(client):
    h = register(client)
    assert client.get("/v1/auth/me", headers=h).json()["has_business"] is False
    r = client.post("/v1/auth/login", json={"email": "ADA@example.com", "password": "s3cure-pass"})
    assert r.status_code == 200
    assert client.post("/v1/auth/login", json={"email": "ada@example.com", "password": "wrong-pass"}).status_code == 401


def test_duplicate_email_rejected(client):
    register(client)
    r = client.post("/v1/auth/register", json={"email": "ada@example.com", "full_name": "X Y", "password": "another-pass"})
    assert r.status_code == 409


def test_weak_password_rejected(client):
    r = client.post("/v1/auth/register", json={"email": "b@example.com", "full_name": "B B", "password": "short"})
    assert r.status_code == 422


def test_auth_required(client):
    assert client.get("/v1/readiness").status_code == 401
    assert client.get("/v1/readiness", headers={"Authorization": "Bearer garbage"}).status_code == 401


def test_business_required_before_transactions(client):
    h = register(client)
    assert client.get("/v1/transactions", headers=h).status_code == 409


def test_business_validation(client):
    h = register(client)
    bad = {**BUSINESS, "state": "Atlantis"}
    assert client.post("/v1/business", json=bad, headers=h).status_code == 422


def test_full_flow_import_score_share(client, owner):
    r = upload(client, owner)
    assert r.status_code == 200, r.text
    res = r.json()
    assert res["imported"] > 1500 and res["rejected"] == 0

    # Re-uploading the same statement must not double count.
    again = upload(client, owner).json()
    assert again["imported"] == 0 and again["duplicates"] == res["imported"]

    page = client.get("/v1/transactions?page_size=10", headers=owner).json()
    assert page["total"] == res["imported"] and len(page["items"]) == 10

    a = client.get("/v1/readiness", headers=owner).json()
    assert a["indicators"]["months_with_data"] == 11
    assert a["indicators"]["missing_months"] == ["2026-02"]
    assert 40 <= a["score"]["total"] <= 100
    assert any(g["code"] == "tin" for g in a["gaps"])
    assert any(g["code"] == "uncategorised" for g in a["gaps"])

    # Uploading the missing month closes the gap and lifts the score.
    upload(client, owner, SAMPLE_FEB)
    b = client.get("/v1/readiness", headers=owner).json()
    assert b["indicators"]["missing_months"] == []
    assert b["score"]["total"] > a["score"]["total"]

    # Fix an uncategorised line and confirm it is now user-categorised.
    unc = client.get("/v1/transactions?category=uncategorised", headers=owner).json()["items"][0]
    p = client.patch(f"/v1/transactions/{unc['id']}", json={"category": "inventory"}, headers=owner)
    assert p.json()["category"] == "inventory" and p.json()["category_source"] == "user"

    s = client.post("/v1/share-links", json={"label": "LAPO MFB"}, headers=owner)
    assert s.status_code == 201
    token, link_id = s.json()["token"], s.json()["id"]
    pub = client.get(f"/v1/public/profile/{token}")
    assert pub.status_code == 200 and pub.json()["business"]["name"] == BUSINESS["name"]
    assert client.get("/v1/share-links", headers=owner).json()[0]["view_count"] == 1

    client.delete(f"/v1/share-links/{link_id}", headers=owner)
    assert client.get(f"/v1/public/profile/{token}").status_code == 404


def test_tenant_isolation(client, owner):
    upload(client, owner)
    txn_id = client.get("/v1/transactions", headers=owner).json()["items"][0]["id"]

    intruder = register(client, "eve@example.com")
    client.post("/v1/business", json={**BUSINESS, "name": "Eve Ventures"}, headers=intruder)
    assert client.get("/v1/transactions", headers=intruder).json()["total"] == 0
    assert client.patch(f"/v1/transactions/{txn_id}", json={"category": "rent"}, headers=intruder).status_code == 404
    assert client.delete(f"/v1/transactions/{txn_id}", headers=intruder).status_code == 404


def test_manual_transaction_and_delete(client, owner):
    body = {"txn_date": "2026-02-01", "narration": "Cash sale at market", "amount_naira": 15000,
            "direction": "credit", "category": "sales"}  # fmt: skip
    t = client.post("/v1/transactions", json=body, headers=owner).json()
    assert t["amount_kobo"] == 1_500_000 and t["source"] == "manual"
    assert client.delete(f"/v1/transactions/{t['id']}", headers=owner).status_code == 204


def test_upload_rejects_wrong_type_and_bad_csv(client, owner):
    assert upload(client, owner, b"x", "photo.png").status_code == 415
    assert upload(client, owner, b"a,b\n1,2\n").status_code == 422


def test_login_rate_limited(client):
    codes = [client.post("/v1/auth/login", json={"email": "x@example.com", "password": "nopenope"}).status_code
             for _ in range(12)]  # fmt: skip
    assert 429 in codes
